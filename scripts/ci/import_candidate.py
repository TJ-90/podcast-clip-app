#!/usr/bin/env python3
"""Trusted candidate importer.

Upstream bytes are parsed as data. This process never imports Python modules from,
sources, hooks, builds, or otherwise executes candidate content.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


MAX_ENTRIES = 200_000
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_FILE = 512 * 1024 * 1024
MAX_ARCHIVE = 1024 * 1024 * 1024

CANDIDATES = {
    "podaura": {
        "owner": "SkyD666",
        "repo": "PodAura",
        "commit": "9c154cbba2936725e1aef4a09a8f82be49ccb9a0",
        "tree": "59b4ac49f35e2314ddcb40ca8f6a0358e4924024",
        "license_blob": "f288702d2fa16d3cdf0035b15a9fcbc552cd88e7",
    },
    "antennapod": {
        "owner": "AntennaPod",
        "repo": "AntennaPod",
        "commit": "1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7",
        "tree": "ebfc8990216aded7ad4ab6d393fa6e0131a69fee",
        "license_blob": "0c780f71ed85dbd7605d1946312e2dc3fb36cf90",
        "quarantined_symlinks": {
            "app/src/free/play": {"sha": "e9d641154ce0b37b27ed83f4761cfb4b71665fff", "target": "../main/play"},
            "app/src/play/play": {"sha": "e9d641154ce0b37b27ed83f4761cfb4b71665fff", "target": "../main/play"},
            "ui/preferences/src/main/assets/LICENSE.txt": {"sha": "2a64f9d0fc673aa4f81ebacaac15f13df255688a", "target": "../../../../../LICENSE"},
        },
        "quarantined_gitlinks": {
            "app/src/main/play": "122c14a36d50f2fd804ea2d9ed780efd2dba9b06",
        },
    },
}

RESERVED_PREFIXES = (
    ".github/",
    "scripts/ci/",
    "provenance/",
)
RESERVED_ROOTS = {
    "DESIGN.md",
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "UPSTREAM.md",
    "docs/modification-ledger.md",
}


class Reject(RuntimeError):
    pass


@dataclass(frozen=True)
class Entry:
    archive_name: str
    path: str
    size: int
    mode: int
    member: tarfile.TarInfo


def request_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "podcast-clips-trusted-importer/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download_bounded(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "podcast-clips-trusted-importer/1"})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("xb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARCHIVE:
                raise Reject("compressed archive exceeds 1 GiB")
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def normalized_relative(raw_name: str, root: str | None) -> tuple[str, str]:
    if not raw_name or raw_name.startswith(("/", "\\")):
        raise Reject(f"absolute/empty archive path: {raw_name!r}")
    if "\x00" in raw_name or "\\" in raw_name:
        raise Reject(f"ambiguous archive path: {raw_name!r}")
    posix = PurePosixPath(raw_name)
    parts = posix.parts
    if not parts:
        raise Reject("empty archive path")
    discovered_root = parts[0]
    if root is not None and discovered_root != root:
        raise Reject("archive contains multiple roots")
    rel_parts = parts[1:]
    if not rel_parts:
        return discovered_root, ""
    clean: list[str] = []
    for component in rel_parts:
        if component in ("", ".", ".."):
            raise Reject(f"escaping/dot archive path: {raw_name!r}")
        if unicodedata.normalize("NFC", component) != component:
            raise Reject(f"non-NFC archive path: {raw_name!r}")
        if component.endswith((".", " ")):
            raise Reject(f"trailing-dot/space archive path: {raw_name!r}")
        folded = component.casefold()
        alias = folded.rstrip(". ")
        if alias == ".git" or re.fullmatch(r"\.?git~\d+", alias):
            raise Reject(f"git control alias: {raw_name!r}")
        if folded in {"con", "prn", "aux", "nul"} or re.fullmatch(r"(?:com|lpt)[1-9]", folded):
            raise Reject(f"reserved device path: {raw_name!r}")
        clean.append(component)
    rel = "/".join(clean)
    if str(PurePosixPath(rel)) != rel or rel.startswith("../"):
        raise Reject(f"non-canonical archive path: {raw_name!r}")
    return discovered_root, rel


def preflight(
    archive: tarfile.TarFile,
    allowed_symlinks: dict[str, dict] | None = None,
) -> tuple[list[Entry], list[dict]]:
    allowed_symlinks = allowed_symlinks or {}
    members = archive.getmembers()
    if len(members) > MAX_ENTRIES:
        raise Reject("archive entry count exceeds limit")
    entries: list[Entry] = []
    quarantined_symlinks: list[dict] = []
    seen: dict[str, str] = {}
    root: str | None = None
    total = 0
    for member in members:
        root, rel = normalized_relative(member.name, root)
        if member.issym():
            expected = allowed_symlinks.get(rel)
            target = member.linkname
            if (
                expected is None
                or target != expected["target"]
                or github_blob_sha(target.encode("utf-8")) != expected["sha"]
            ):
                raise Reject(f"unapproved or changed symlink rejected: {member.name!r}")
            quarantined_symlinks.append(
                {"path": rel, "git_blob_sha1": expected["sha"], "target": target, "reason": "symlink quarantined; never materialized"}
            )
            continue
        if member.islnk() or member.isdev() or member.isfifo():
            raise Reject(f"link/special entry rejected: {member.name!r}")
        if not (member.isdir() or member.isfile()):
            raise Reject(f"unsupported tar entry rejected: {member.name!r}")
        if not rel:
            if not member.isdir():
                raise Reject("archive root is not a directory")
            continue
        collision_key = unicodedata.normalize("NFC", rel).casefold()
        previous = seen.get(collision_key)
        if previous is not None:
            raise Reject(f"case/Unicode collision: {previous!r} vs {rel!r}")
        seen[collision_key] = rel
        if member.isfile():
            if member.size < 0 or member.size > MAX_FILE:
                raise Reject(f"file size outside bounds: {rel!r}")
            total += member.size
            if total > MAX_TOTAL:
                raise Reject("expanded archive exceeds 4 GiB")
            entries.append(Entry(member.name, rel, member.size, member.mode & 0o777, member))
    if set(allowed_symlinks) != {item["path"] for item in quarantined_symlinks}:
        raise Reject("approved symlink inventory does not match the archive")
    return entries, quarantined_symlinks


def github_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()  # nosec: Git object identity, not security


def validate_and_extract(
    archive_path: Path,
    github_files: dict[str, dict],
    destination: Path,
    allowed_symlinks: dict[str, dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    with tarfile.open(archive_path, mode="r:*") as archive:
        entries, quarantined_symlinks = preflight(archive, allowed_symlinks)
        archive_paths = {entry.path for entry in entries}
        github_paths = set(github_files)
        if archive_paths != github_paths:
            missing = sorted(github_paths - archive_paths)[:10]
            extra = sorted(archive_paths - github_paths)[:10]
            raise Reject(f"archive/tree path mismatch; missing={missing}, extra={extra}")

        manifest: list[dict] = []
        for entry in entries:
            source = archive.extractfile(entry.member)
            if source is None:
                raise Reject(f"regular file not readable: {entry.path}")
            data = source.read(MAX_FILE + 1)
            if len(data) != entry.size:
                raise Reject(f"file length mismatch: {entry.path}")
            observed_blob = github_blob_sha(data)
            expected = github_files[entry.path]
            if observed_blob != expected["sha"] or entry.size != expected.get("size", entry.size):
                raise Reject(f"GitHub tree/blob mismatch: {entry.path}")
            expected_executable = expected["mode"] == "100755"
            if bool(entry.mode & stat.S_IXUSR) != expected_executable:
                raise Reject(f"executable-mode mismatch: {entry.path}")
            output = destination.joinpath(*PurePosixPath(entry.path).parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise Reject(f"extraction collision: {entry.path}")
            with output.open("xb") as handle:
                handle.write(data)
            output.chmod(0o755 if expected_executable else 0o644)
            manifest.append(
                {
                    "path": entry.path,
                    "git_blob_sha1": observed_blob,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": entry.size,
                    "mode": expected["mode"],
                }
            )
    return manifest, quarantined_symlinks


def is_quarantined(path: str, executable: bool) -> tuple[bool, str]:
    folded = path.casefold()
    if folded.startswith((".github/", ".gitlab/", ".circleci/", ".githooks/", ".hooks/", ".idea/", ".vscode/", "fastlane/")):
        return True, "upstream repository control surface"
    if folded in {".gitmodules", "jenkinsfile", "gradlew", "gradlew.bat", ".vscode/tasks.json", ".vscode/launch.json"}:
        return True, "active bootstrap/IDE control"
    if re.search(r"(^|/)(ci|release|scripts/(ci|release))(/|$)", folded):
        return True, "CI/release script"
    if executable and ("/scripts/" in f"/{folded}" or "/tools/" in f"/{folded}"):
        return True, "executable tool/script"
    return False, ""


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(*args: str, cwd: Path, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=None,
    )
    return result.stdout.strip() if capture else ""


def rebrand(candidate: str, root: Path) -> list[dict]:
    changes: list[dict] = []
    if candidate == "podaura":
        path = root / "shared/src/commonMain/composeResources/values/strings.xml"
        text = path.read_text(encoding="utf-8")
        replacements = {
            '<string name="app_name">PodAura</string>': '<string name="app_name">Podcast Clips</string>',
            '<string name="play_activity_label">PodAura Player</string>': '<string name="play_activity_label">Podcast Clips Player</string>',
        }
        for old, new in replacements.items():
            if old not in text:
                raise Reject(f"rebrand anchor missing: {old}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        changes.append(
            {
                "path": str(path.relative_to(root)),
                "reason": "Visible brand follows DESIGN.md Product character and Visual language; upstream credit remains in legal records",
            }
        )
    elif candidate == "antennapod":
        path = root / "common.gradle"
        text = path.read_text(encoding="utf-8")
        replacements = {
            'resValue "string", "app_name", "AntennaPod"': 'resValue "string", "app_name", "Podcast Clips"',
            'resValue "string", "app_name", "AntennaPod Debug"': 'resValue "string", "app_name", "Podcast Clips Debug"',
        }
        for old, new in replacements.items():
            if old not in text:
                raise Reject(f"rebrand anchor missing: {old}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        changes.append(
            {
                "path": str(path.relative_to(root)),
                "reason": "Visible brand follows DESIGN.md Product character and Visual language; upstream credit remains in legal records",
            }
        )
    return changes


def run_self_test() -> None:
    def archive_with(items: list[tuple[str, bytes, str]]) -> tarfile.TarFile:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as output:
            root = tarfile.TarInfo("root")
            root.type = tarfile.DIRTYPE
            output.addfile(root)
            for name, data, kind in items:
                info = tarfile.TarInfo(f"root/{name}")
                info.size = len(data)
                if kind == "file":
                    output.addfile(info, io.BytesIO(data))
                elif kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../../escape"
                    output.addfile(info)
                elif kind == "fifo":
                    info.type = tarfile.FIFOTYPE
                    output.addfile(info)
                else:
                    raise AssertionError(kind)
        stream.seek(0)
        return tarfile.open(fileobj=stream, mode="r:")

    with archive_with([("ok.txt", b"ok", "file")]) as valid:
        entries, symlinks = preflight(valid)
        assert [entry.path for entry in entries] == ["ok.txt"] and not symlinks
    hostile = [
        [("../escape", b"x", "file")],
        [(".git/config", b"x", "file")],
        [("link", b"", "symlink")],
        [("pipe", b"", "fifo")],
        [("Readme", b"a", "file"), ("README", b"b", "file")],
        [("trailing. ", b"x", "file")],
        [("back\\slash", b"x", "file")],
    ]
    for corpus in hostile:
        try:
            with archive_with(corpus) as candidate:
                preflight(candidate)
        except Reject:
            continue
        raise AssertionError(f"hostile corpus accepted: {corpus!r}")
    print("ARCHIVE-01..03 hostile corpus: PASS")


def import_candidate(args: argparse.Namespace) -> None:
    config = CANDIDATES[args.candidate]
    owner, repo, commit = config["owner"], config["repo"], config["commit"]
    commit_meta = request_json(f"https://api.github.com/repos/{owner}/{repo}/commits/{commit}")
    observed_commit = commit_meta["sha"]
    observed_tree = commit_meta["commit"]["tree"]["sha"]
    if observed_commit != commit or (config["tree"] and observed_tree != config["tree"]):
        raise Reject("pinned commit/tree identity mismatch")
    tree_meta = request_json(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{observed_tree}?recursive=1"
    )
    if tree_meta.get("truncated"):
        raise Reject("GitHub recursive tree is truncated")
    approved_gitlinks = config.get("quarantined_gitlinks", {})
    non_blobs = [item for item in tree_meta["tree"] if item["type"] not in {"blob", "tree"}]
    observed_gitlinks = {item["path"]: item["sha"] for item in non_blobs if item["type"] == "commit"}
    if observed_gitlinks != approved_gitlinks or len(non_blobs) != len(observed_gitlinks):
        raise Reject(f"unapproved submodule/unknown tree entries: {non_blobs[:3]}")
    approved_symlinks = config.get("quarantined_symlinks", {})
    github_files = {
        item["path"]: {"sha": item["sha"], "size": item.get("size", 0), "mode": item["mode"]}
        for item in tree_meta["tree"]
        if item["type"] == "blob" and item["mode"] in {"100644", "100755"}
    }
    observed_symlinks = {
        item["path"]: item["sha"] for item in tree_meta["tree"] if item["type"] == "blob" and item["mode"] == "120000"
    }
    if observed_symlinks != {path: value["sha"] for path, value in approved_symlinks.items()}:
        raise Reject("approved symlink inventory does not match GitHub tree metadata")
    license_entry = github_files.get("LICENSE")
    if not license_entry or (config["license_blob"] and license_entry["sha"] != config["license_blob"]):
        raise Reject("pinned GPL license blob is absent or changed")

    repo_root = Path(args.repository).resolve()
    if not (repo_root / ".git").is_dir():
        raise Reject("trusted bootstrap checkout is not a Git repository")
    with tempfile.TemporaryDirectory(prefix="trusted-import-") as temp_name:
        temp = Path(temp_name)
        archive_path = temp / "candidate.tar.gz"
        extracted = temp / "extracted"
        extracted.mkdir()
        archive_sha256 = download_bounded(
            f"https://codeload.github.com/{owner}/{repo}/tar.gz/{commit}", archive_path
        )
        manifest, quarantined_symlinks = validate_and_extract(
            archive_path, github_files, extracted, approved_symlinks
        )

        quarantine: list[dict] = list(quarantined_symlinks)
        quarantine.extend(
            {"path": path, "gitlink_commit": sha, "reason": "submodule gitlink quarantined; content never fetched or materialized"}
            for path, sha in sorted(approved_gitlinks.items())
        )
        reserved: list[dict] = []
        manifest_by_path = {item["path"]: item for item in manifest}
        for item in manifest:
            rel = item["path"]
            source = extracted.joinpath(*PurePosixPath(rel).parts)
            executable = item["mode"] == "100755"
            quarantine_it, reason = is_quarantined(rel, executable)
            reserved_it = rel in RESERVED_ROOTS or rel.startswith(RESERVED_PREFIXES)
            if quarantine_it or reserved_it:
                quarantine.append({**item, "reason": reason or "trusted bootstrap path reserved"})
                if reserved_it:
                    reserved.append({"path": rel, "upstream_blob": item["git_blob_sha1"]})
                continue
            destination = repo_root.joinpath(*PurePosixPath(rel).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise Reject(f"candidate would overwrite trusted path: {rel}")
            shutil.copyfile(source, destination, follow_symlinks=False)
            destination.chmod(0o644)

        upstream_license = extracted / "LICENSE"
        bootstrap_license = repo_root / "LICENSE"
        project_license = bootstrap_license.read_text(encoding="utf-8", errors="replace")
        if "GNU GENERAL PUBLIC LICENSE" not in project_license or "Version 3" not in project_license:
            raise Reject("bootstrap LICENSE is not a complete GPL v3 text")
        upstream_license_copy = repo_root / "licenses" / f"{repo}-LICENSE.txt"
        upstream_license_copy.parent.mkdir(parents=True, exist_ok=True)
        upstream_license_copy.write_bytes(upstream_license.read_bytes())

        changes = rebrand(args.candidate, repo_root)
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        lock = {
            "schema": 1,
            "candidate": args.candidate,
            "upstream_repository": f"https://github.com/{owner}/{repo}",
            "upstream_commit": observed_commit,
            "upstream_tree": observed_tree,
            "github_commit_verified": bool(commit_meta["commit"].get("verification", {}).get("verified")),
            "observed_archive_sha256": archive_sha256,
            "archive_entry_count": len(manifest),
            "expanded_regular_bytes": sum(item["size"] for item in manifest),
            "license_blob": license_entry["sha"],
            "bootstrap_overlay_commit": args.control_sha,
            "import_run_id": run_id,
            "quarantined_count": len(quarantine),
            "reserved_upstream_paths": reserved,
            "visible_brand_changes": changes,
        }
        write_json(repo_root / "provenance/import-lock.json", lock)
        write_json(repo_root / "provenance/extracted-manifest.json", manifest)
        write_json(repo_root / "provenance/quarantine-manifest.json", quarantine)
        with (repo_root / "docs/modification-ledger.md").open("a", encoding="utf-8") as ledger:
            ledger.write(
                f"| 2026-07-17 | trusted importer | Snapshot `{owner}/{repo}@{commit}`; "
                f"archive `{archive_sha256}`; {len(quarantine)} controls quarantined; visible brand overlay | "
                "Candidate admission without executing upstream under a write token |\n"
            )

    branch = f"candidate/{args.candidate}-{commit[:12]}-r{os.environ.get('GITHUB_RUN_ID', 'manual')}"
    run("git", "config", "core.hooksPath", "/dev/null", cwd=repo_root)
    run("git", "config", "user.name", "podcast-clips-bot", cwd=repo_root)
    run("git", "config", "user.email", "actions@users.noreply.github.com", cwd=repo_root)
    run("git", "switch", "-c", branch, cwd=repo_root)
    run("git", "add", "-A", cwd=repo_root)
    title = "Prove the pinned podcast foundation before product investment"
    body = (
        f"Import the verified {owner}/{repo} source snapshot as inert data, retain the trusted "
        "bootstrap controls, quarantine upstream automation, and apply only the DESIGN.md-governed visible brand.\n\n"
        "Constraint: Candidate content may not execute while a write-capable token is present\n"
        "Constraint: Snapshot provenance must remain honest and GPL-3.0 compliant\n"
        "Rejected: Preserve upstream workflows in place | unreviewed control surfaces would become active\n"
        "Confidence: high\n"
        "Scope-risk: broad\n"
        "Directive: Do not merge until two exact-identity clean validations and capability audit pass\n"
        "Tested: GitHub commit/tree mapping, full archive preflight/hash manifest, quarantine policy, visible brand anchor\n"
        "Not-tested: Android code; it runs only in the separate candidate workflow"
    )
    run("git", "commit", "-m", title, "-m", body, cwd=repo_root)
    candidate_sha = run("git", "rev-parse", "HEAD", cwd=repo_root, capture=True)
    run("git", "push", "origin", f"HEAD:refs/heads/{branch}", cwd=repo_root)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"branch={branch}\n")
            handle.write(f"candidate_sha={candidate_sha}\n")
            handle.write(f"upstream_tree={observed_tree}\n")
            handle.write(f"archive_sha256={archive_sha256}\n")
    print(json.dumps({"branch": branch, "candidate_sha": candidate_sha, "upstream_tree": observed_tree}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--candidate", choices=sorted(CANDIDATES))
    parser.add_argument("--repository", default=".")
    parser.add_argument("--control-sha")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        return
    if not args.candidate or not args.control_sha or not re.fullmatch(r"[0-9a-f]{40}", args.control_sha):
        parser.error("--candidate and exact --control-sha are required")
    import_candidate(args)


if __name__ == "__main__":
    main()
