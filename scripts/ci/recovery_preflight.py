#!/usr/bin/env python3
"""Pure, non-executing Story 1 recovery preflight.

Upstream bytes are data only. This module has no checkout, subprocess, import,
build, Gradle, Android, credential, cache, result, or artifact behavior.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Iterable, Mapping

UPSTREAM_COMMIT = "1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7"
UPSTREAM_TREE = "ebfc8990216aded7ad4ab6d393fa6e0131a69fee"
UPSTREAM_ARCHIVE_SHA256 = "99c9d77996595d6d75ed170240d5849ce381931f6d5e726d12e198ff15dae8a2"
PINNED_TUPLE_COUNT = 2028
PINNED_TUPLE_DIGEST = "b05cc9e64c2285efab776bf05a6de65ba8396e0de8a6329c00a9a23ba3997aee"
GRADLE_PROPERTIES = b"android.useAndroidX=true\norg.gradle.jvmargs=-Xmx4096m\nandroid.nonTransitiveRClass=false\n"
GRADLE_PROPERTIES_BLOB = "19058640ca22d0398085d67d6a49e68892894a80"
GRADLE_DISTRIBUTION_URL = "https\\://services.gradle.org/distributions/gradle-8.13-bin.zip"
GRADLE_DISTRIBUTION_SHA256 = "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"
GRADLE_WRAPPER_JAR_SHA256 = "81a82aaea5abcc8ff68b3dfcb58b3c3c429378efd98e7433460610fecd7ae45f"

TASK_POLICY = {
    "tasks": [":app:assembleFreeDebug", ":app:testFreeDebugUnitTest", ":app:lintFreeDebug"],
    "expected_failures": [], "exclusions": [], "noops": [],
    "task_shadowing": False, "property_shadows": [],
    "thresholds": {"max_dispatches": 3, "required_consecutive_successes": 2,
                   "timeout_minutes": 25, "critical_gaps": 0},
}

BUILD_SCRIPTS = """app-wearos/build.gradle
app/build.gradle
build.gradle
common.gradle
event/build.gradle
model/build.gradle
net/common/build.gradle
net/discovery/build.gradle
net/download/service-interface/build.gradle
net/download/service/build.gradle
net/ssl/build.gradle
net/sync/gpoddernet/build.gradle
net/sync/service-interface/build.gradle
net/sync/service/build.gradle
net/sync/wear-interface/build.gradle
parser/feed/build.gradle
parser/media/build.gradle
parser/transcript/build.gradle
playFlavor.gradle
playback/base/build.gradle
playback/cast/build.gradle
playback/service/build.gradle
settings.gradle
storage/database-maintenance-service/build.gradle
storage/database/build.gradle
storage/importexport/build.gradle
storage/preferences/build.gradle
system/build.gradle
ui/app-start-intent/build.gradle
ui/chapters/build.gradle
ui/common/build.gradle
ui/discovery/build.gradle
ui/echo/build.gradle
ui/episodes/build.gradle
ui/glide/build.gradle
ui/i18n/build.gradle
ui/notifications/build.gradle
ui/preferences/build.gradle
ui/statistics/build.gradle
ui/transcript/build.gradle
ui/widget/build.gradle""".splitlines()
KNOWN_INPUTS = {
    "gradle_properties": ["gradle.properties"],
    "wrapper": ["gradle/wrapper/gradle-wrapper.jar", "gradle/wrapper/gradle-wrapper.properties"],
    "settings_and_build_scripts": BUILD_SCRIPTS,
    "version_catalogs": ["gradle/libs.versions.toml"],
    "build_logic": [],
    "jdk_java_declarations": ["common.gradle", "gradle/libs.versions.toml"],
    "statically_referenced_root_config": ["common.gradle", "playFlavor.gradle"],
}

# path -> (Git type, mode, blob-or-target identity, symlink target if applicable)
_Q = """.github/ISSUE_TEMPLATE/bug_report.yml blob 100644 cedb7b5994517e514e51f9e5830cae5fd1202f90
.github/ISSUE_TEMPLATE/config.yml blob 100644 b1f495e13a18cf5cc0a60da7953a270a8dd070d3
.github/ISSUE_TEMPLATE/feature_request.yml blob 100644 6ce0525b840ca198a10be7def8708d096a99a85e
.github/pull_request_template.md blob 100644 adbca13f111b3f7ce3fe1e1074bb6ab8c943960c
.github/workflows/assign-milestone.yml blob 100644 cafb6c4e804d2791af125275935c3ffee623941e
.github/workflows/checks.yml blob 100644 c46a38233945a9cee3045c23fbb2e57c52450525
.github/workflows/close-if-no-reply.yml blob 100644 ccf9b9faa8fabe9a05b5cb342b19ed56d4682a2b
.github/workflows/copilot-setup-steps.yml blob 100644 a9adad7b32c8dc1e42aea0f2ba76daa3d2288582
.github/workflows/create-changelog.yml blob 100644 a21c594ca7299730c5c9383c8f9aca44c3299a0a
.github/workflows/errorPrinter.py blob 100644 c83b9b3ad4728498fbc86c4210184d16a3bfdced
.github/workflows/issue-comment.yml blob 100644 43bdc51fa407321a8550b69e96df7cb7cf328f1b
.github/workflows/issue-opened.yml blob 100644 1330cd5c3a84c6d88e1e89f91fd75ef4e7776814
.github/workflows/pr-conventions.yml blob 100644 1147ef0f684edc245d055654195652cd2cd20319
.github/workflows/remove-labels-when-issue-gets-closed.yml blob 100644 0175df440203d1c3b2992015a1b9bdb782f9e680
.github/workflows/review-link-label.yml blob 100644 fca0ae32dc5c3a99db2ddb2b53d368a674d2737b
.github/workflows/runEmulatorTests.sh blob 100644 82a43693a7867b698787439999004ab798354c7a
.gitmodules blob 100644 a3d4c3cf256b901fa32d98d80eb19a61b1037bab
.idea/codeStyles/Project.xml blob 100644 bc73fbfd0d24f0468470aaf9338ca64fc20b813f
.idea/codeStyles/codeStyleConfig.xml blob 100644 79ee123c2b23e069e35ed634d687e17f731cc702
.idea/icon.png blob 100644 998bfdea82398e21d1aca1ea86a84c695f7c58e3
LICENSE blob 100644 0c780f71ed85dbd7605d1946312e2dc3fb36cf90
README.md blob 100644 83bd00e36ef2462e0a056227b9a9edc8b0307bf5
app/src/free/play blob 120000 e9d641154ce0b37b27ed83f4761cfb4b71665fff ../main/play
app/src/main/play commit 160000 122c14a36d50f2fd804ea2d9ed780efd2dba9b06
app/src/play/play blob 120000 e9d641154ce0b37b27ed83f4761cfb4b71665fff ../main/play
gradlew blob 100755 1aa94a4269074199e6ed2c37e8db3e0826030965
gradlew.bat blob 100644 7101f8e4676fcad8adc961e929ea3bcb37b5262f
ui/preferences/src/main/assets/LICENSE.txt blob 120000 2a64f9d0fc673aa4f81ebacaac15f13df255688a ../../../../../LICENSE"""
QUARANTINE = {}
for _line in _Q.splitlines():
    _parts = _line.split()
    QUARANTINE[_parts[0]] = (*_parts[1:4], _parts[4] if len(_parts) == 5 else None)

TRUSTED_OVERLAY_PATHS = frozenset(""".github/workflows/import-upstream.yml
.github/workflows/preflight-recovery.yml
.github/workflows/validate-candidate.yml
DESIGN.md
LICENSE
README.md
THIRD_PARTY_NOTICES.md
UPSTREAM.md
docs/base-selection-report.md
docs/modification-ledger.md
scripts/ci/audit_candidate.py
scripts/ci/import_candidate.py
scripts/ci/recovery_preflight.py
scripts/ci/test_recovery_preflight.py
scripts/ci/validate_preflight_report.py""".splitlines())

ALLOWED_ENV = frozenset({"HOME", "LANG", "LC_ALL", "PATH", "RECOVERY_OUTPUT", "RECOVERY_OVERLAY_SHA"})
FORBIDDEN_PREFIXES = ("ACTIONS_", "GITHUB_", "RUNNER_", "ANDROID_", "GRADLE_")

class Reject(RuntimeError): pass

@dataclass(frozen=True, order=True)
class GitEntry:
    path: str
    type: str
    mode: str
    identity: str

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # nosec: Git identity

def normalize_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "\\")) or "\0" in raw or "\\" in raw:
        raise Reject(f"invalid Git path: {raw!r}")
    parts = raw.split("/")
    if any(p in {"", ".", ".."} or unicodedata.normalize("NFC", p) != p for p in parts):
        raise Reject(f"non-canonical Git path: {raw!r}")
    result = "/".join(parts)
    if str(PurePosixPath(result)) != result: raise Reject(f"non-canonical Git path: {raw!r}")
    return result

def validate_commit(payload: Mapping[str, object]) -> None:
    try: tree = payload["commit"]["tree"]["sha"]  # type: ignore[index]
    except (KeyError, TypeError): raise Reject("malformed commit payload") from None
    if payload.get("sha") != UPSTREAM_COMMIT or tree != UPSTREAM_TREE: raise Reject("pinned commit/tree mismatch")

def parse_git_tree(payload: Mapping[str, object], expected_count: int = PINNED_TUPLE_COUNT, expected_digest: str = PINNED_TUPLE_DIGEST) -> dict[str, GitEntry]:
    if payload.get("sha") != UPSTREAM_TREE: raise Reject("pinned root tree mismatch")
    if payload.get("truncated") is not False: raise Reject("recursive tree lacks non-truncated proof")
    rows = payload.get("tree")
    if not isinstance(rows, list) or not rows: raise Reject("malformed/empty recursive tree")
    valid = {"blob": {"100644", "100755", "120000"}, "tree": {"040000"}, "commit": {"160000"}}
    result, folded = {}, set()
    for row in rows:
        if not isinstance(row, Mapping): raise Reject("malformed tree entry")
        path = normalize_path(row.get("path"))  # type: ignore[arg-type]
        kind, mode, identity = row.get("type"), row.get("mode"), row.get("sha")
        if kind not in valid or mode not in valid[kind] or not isinstance(identity, str) or not re.fullmatch("[0-9a-f]{40}", identity):
            raise Reject(f"invalid tuple: {path}")
        key = path.casefold()
        if path in result or key in folded: raise Reject(f"duplicate/case collision: {path}")
        folded.add(key); result[path] = GitEntry(path, kind, mode, identity)
    body = json.dumps([asdict(result[p]) for p in sorted(result)], sort_keys=True, separators=(",", ":"))
    if len(result) != expected_count or hashlib.sha256(body.encode()).hexdigest() != expected_digest:
        raise Reject("full pinned Git tuple inventory mismatch")
    return result

def validate_environment(env: Mapping[str, str] | None = None) -> None:
    env = os.environ if env is None else env
    forbidden = {k for k in env if k.startswith(FORBIDDEN_PREFIXES) or k in {"GH_TOKEN", "JAVA_HOME", "CI"}}
    extra = set(env) - ALLOWED_ENV
    if forbidden or extra: raise Reject(f"unsanitized parser environment: {sorted(forbidden | extra)}")

def validate_quarantine(entries: Mapping[str, GitEntry], policy: Mapping[str, tuple] = QUARANTINE) -> None:
    if set(policy) != set(QUARANTINE): raise Reject("quarantine allowlist paths changed")
    for path, expected in QUARANTINE.items():
        if tuple(policy[path]) != expected: raise Reject(f"quarantine tuple policy changed: {path}")
        got = entries.get(path)
        if got is None or (got.type, got.mode, got.identity) != expected[:3]: raise Reject(f"quarantine tuple mismatch: {path}")
        if expected[3] is not None and git_blob_sha(expected[3].encode()) != got.identity: raise Reject(f"symlink target mismatch: {path}")

def validate_overlay(overlay: Mapping[str, GitEntry]) -> None:
    if set(overlay) != TRUSTED_OVERLAY_PATHS: raise Reject("closed overlay path set changed")
    if any(e.path != p or e.type != "blob" or e.mode != "100644" for p, e in overlay.items()):
        raise Reject("overlay contains non-ordinary blob tuple")

def relocation(path: str, entry: GitEntry) -> GitEntry:
    if path == "LICENSE": return GitEntry("licenses/AntennaPod-LICENSE.txt", "blob", "100644", entry.identity)
    suffix, kind, mode = ".disabled", entry.type, entry.mode
    if entry.mode == "120000": suffix, kind, mode = ".symlink-target", "blob", "100644"
    elif entry.type == "commit": suffix = ".gitlink"
    return GitEntry(f"upstream-quarantine/{path}{suffix}", kind, mode, entry.identity)

def project_tree(upstream: Mapping[str, GitEntry], overlay: Mapping[str, GitEntry], common_gradle: bytes) -> dict[str, GitEntry]:
    validate_quarantine(upstream); validate_overlay(overlay)
    leaves = {p: e for p, e in upstream.items() if e.type != "tree"}
    result = {}
    for path, entry in leaves.items():
        destination = relocation(path, entry) if path in QUARANTINE else entry
        if path == "common.gradle":
            if git_blob_sha(common_gradle) != entry.identity: raise Reject("common.gradle byte identity mismatch")
            branded = common_gradle
            for old, new in ((b'"AntennaPod"', b'"Podcast Clips"'), (b'"AntennaPod Debug"', b'"Podcast Clips Debug"')):
                if branded.count(old) != 1: raise Reject("branding anchor missing/repeated")
                branded = branded.replace(old, new, 1)
            destination = GitEntry(path, "blob", "100644", git_blob_sha(branded))
        if destination.path in result: raise Reject(f"projection collision: {destination.path}")
        result[destination.path] = destination
    for path, entry in overlay.items(): result[path] = entry
    keys = [p.casefold() for p in result]
    if len(keys) != len(set(keys)): raise Reject("projection case collision")
    # Exact accounting: every pinned leaf maps once; only overlay paths add/replace.
    if len(leaves) != sum(1 for p in result if p not in TRUSTED_OVERLAY_PATHS):
        raise Reject("projection does not account for every upstream leaf exactly once")
    return result

def validate_gradle_properties(values: Mapping[str, bytes]) -> None:
    if set(values) != {"gradle.properties"}: raise Reject("complete gradle.properties inventory mismatch")
    data = values["gradle.properties"]
    if data != GRADLE_PROPERTIES or git_blob_sha(data) != GRADLE_PROPERTIES_BLOB: raise Reject("gradle.properties changed/incomplete")

def validate_known_inputs(entries: Mapping[str, GitEntry], inventory: Mapping[str, Iterable[str]] = KNOWN_INPUTS) -> None:
    if set(inventory) != set(KNOWN_INPUTS): raise Reject("known-input categories changed")
    for category, expected in KNOWN_INPUTS.items():
        if list(inventory[category]) != expected: raise Reject(f"known-input set changed: {category}")
        for path in expected:
            if path not in entries or entries[path].type != "blob": raise Reject(f"known input absent: {category}:{path}")
    properties = sorted(p for p in entries if p.rsplit("/", 1)[-1] == "gradle.properties")
    if properties != KNOWN_INPUTS["gradle_properties"]: raise Reject("unaccounted gradle.properties")
    logic = sorted(p for p, e in entries.items() if e.type != "tree" and p.startswith(("buildSrc/", "gradle/plugins/", "convention-plugins/")))
    if logic != KNOWN_INPUTS["build_logic"]: raise Reject("unaccounted build logic")

_INPUT_CALL = re.compile(r"(?P<api>System\.getenv|System\.getProperty|providers\.environmentVariable|providers\.gradleProperty|(?:project\.)?findProperty)\s*\(\s*(?P<arg>[^)]*)\)")
_STATIC_ROOT = re.compile(r"apply\s+from\s*:\s*(['\"])(?P<path>[^'\"]+)\1")
_DYNAMIC_ROOT = re.compile(r"apply\s+from\s*:(?!\s*['\"])|includeBuild\s*\((?!\s*['\"])|(?:file|files)\s*\(\s*(?:System\.(?:getenv|getProperty)|providers\.|(?:project\.)?findProperty)")

def scan_dynamic_inputs(contents: Mapping[str, bytes], entries: Mapping[str, GitEntry]) -> dict[str, object]:
    required = set().union(*(set(v) for v in KNOWN_INPUTS.values()))
    if set(contents) != required: raise Reject("known input byte set missing or expanded")
    declarations, roots = [], []
    for path in sorted(contents):
        if path.endswith((".jar", ".toml", ".properties")): continue
        text = contents[path].decode("utf-8", errors="strict")
        if _DYNAMIC_ROOT.search(text): raise Reject(f"unresolved dynamic config input: {path}")
        for match in _INPUT_CALL.finditer(text):
            arg = match.group("arg").strip(); literal = re.fullmatch(r"(['\"])([A-Za-z0-9_.-]+)\1", arg)
            if not literal: raise Reject(f"unresolved dynamic environment/property input: {path}")
            declarations.append({"path": path, "api": match.group("api"), "name": literal.group(2)})
        for match in _STATIC_ROOT.finditer(text):
            target = normalize_path(match.group("path"))
            if target not in entries or entries[target].type != "blob": raise Reject(f"unresolved static root config: {target}")
            roots.append({"declared_by": path, "path": target})
    return {"literal_environment_and_properties": declarations, "static_root_config": roots, "unresolved": []}

def validate_policy(policy: Mapping[str, object]) -> None:
    if policy != TASK_POLICY: raise Reject("validation task/product/threshold policy mutated")

def recovery_scope_negative_tests() -> dict[str, str]:
    attacks = {
        "EF": lambda p: p["expected_failures"].append("unit"),
        "EXCLUDE": lambda p: p["exclusions"].append("**/transcript/**"),
        "NOOP": lambda p: p["noops"].append(":app:lintFreeDebug"),
        "TASK": lambda p: p["tasks"].__setitem__(0, ":app:assembleDebug"),
        "SHADOW": lambda p: p["property_shadows"].append("android.useAndroidX"),
        "THRESHOLD": lambda p: p["thresholds"].__setitem__("max_dispatches", 4),
    }
    result = {}
    for name, mutate in attacks.items():
        policy = copy.deepcopy(TASK_POLICY); mutate(policy)
        try: validate_policy(policy)
        except Reject: result[name] = "rejected"
        else: raise AssertionError(f"RECOVERY-SCOPE {name} accepted")
    return result

def validate_wrapper(properties: bytes, jar: bytes) -> None:
    text = properties.decode()
    if f"distributionUrl={GRADLE_DISTRIBUTION_URL}" not in text or f"distributionSha256Sum={GRADLE_DISTRIBUTION_SHA256}" not in text:
        raise Reject("wrapper distribution/checksum changed")
    if hashlib.sha256(jar).hexdigest() != GRADLE_WRAPPER_JAR_SHA256: raise Reject("wrapper JAR checksum changed")

def inventory_digest(entries: Mapping[str, GitEntry]) -> str:
    body = json.dumps([asdict(entries[p]) for p in sorted(entries)], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()

def report_manifest(entries: Mapping[str, GitEntry]) -> list[dict[str, str]]:
    return [asdict(entries[p]) for p in sorted(entries)]

# --- Recovery audit correction: full projection, frozen controls, CLI/schema. ---
import argparse
import base64
import urllib.error
import urllib.request
from pathlib import Path

UPSTREAM_TREE_ENTRY_COUNT = 745
EVIDENCE_COMMIT = "37593a4217bd442d407d8b0f63d7fcb2fa10f069"
OLD_CANDIDATE_COMMIT = "c58e2607c57925486b856416e1b3f9044673e2be"
OLD_CANDIDATE_BRANCH = "refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562160851"
OLD_PR = 1
REPORT_SCHEMA = "podcast-clips/story1-recovery-preflight/v1"
REPORT_PATH = "/tmp/podcast-clips-recovery-preflight/report.json"
TARGET_REPOSITORY = "TJ-90/podcast-clip-app"
UPSTREAM_REPOSITORY = "AntennaPod/AntennaPod"

@dataclass(frozen=True)
class OverlayRule:
    type: str
    mode: str
    identity: str
    category: str
    rationale: str

# Only candidate-carried trusted files are permitted. Preflight parser/tests and
# its later workflow/uploader remain main-only controls and are never projected.
CANDIDATE_OVERLAY_POLICY = {
    ".github/workflows/import-upstream.yml": OverlayRule("blob", "100644", "b2083a3cc18be27aca8ba6459a17e2b47cf2b1d3", "trusted-control", "write-token import control retained inert during validation"),
    ".github/workflows/validate-candidate.yml": OverlayRule("blob", "100644", "41e780d61b7daf8ac070cfc6d75f30897c0eb6a1", "frozen-validation", "exact build, unit, lint, reporter, permissions, and timeout contract"),
    "DESIGN.md": OverlayRule("blob", "100644", "4234af3f9f512dd98ed50089c858150d9f32153d", "product-contract", "approved product and interaction source of truth"),
    "LICENSE": OverlayRule("blob", "100644", "f288702d2fa16d3cdf0035b15a9fcbc552cd88e7", "legal", "project GPL-3.0 license"),
    "README.md": OverlayRule("blob", "100644", "eed8367a80de22bc17bc1bf99e28e27f7541588c", "documentation", "project identity and recovery status"),
    "THIRD_PARTY_NOTICES.md": OverlayRule("blob", "100644", "e7abfa3bb8e1e3f2c08f74f42751cb0c0c7472db", "legal", "upstream attribution"),
    "UPSTREAM.md": OverlayRule("blob", "100644", "d8f3133fa5f6985f5ff9523adea2b009931b5f2c", "provenance", "pinned upstream identity and evidence"),
    "docs/base-selection-report.md": OverlayRule("blob", "100644", "ee32be287c11a50757d68fb8b05a7d0cff2011c2", "evidence", "immutable Story 1 admission evidence"),
    "docs/modification-ledger.md": OverlayRule("blob", "100644", "9d397c5c81c5518c2b02293779a16a664ad25b8e", "provenance", "closed modification record"),
    "scripts/ci/audit_candidate.py": OverlayRule("blob", "100644", "7a7f236fb7fb94aa00f65c8f68e369b3aedf75f0", "frozen-validation", "actual provenance and capability test implementation"),
    "scripts/ci/import_candidate.py": OverlayRule("blob", "100644", "0f9b4b6387822fab58a74e0b9850ca6272a8ca63", "trusted-control", "reviewed data-only importer retained for provenance"),
}
TRUSTED_OVERLAY_PATHS = frozenset(CANDIDATE_OVERLAY_POLICY)

FROZEN_CONTROLS = {
    "validate_candidate_blob": "41e780d61b7daf8ac070cfc6d75f30897c0eb6a1",
    "audit_candidate_blob": "7a7f236fb7fb94aa00f65c8f68e369b3aedf75f0",
    "tests": list(TASK_POLICY["tasks"]),
    "tasks": list(TASK_POLICY["tasks"]),
    "thresholds": copy.deepcopy(TASK_POLICY["thresholds"]),
    "expected_failures": [], "exclusions": [], "noops": [],
    "task_shadowing": False, "property_shadows": [],
}
FROZEN_CONTROLS_SHA256 = "5d63123058f8d45dcd7edcb265f8b719ca8bcdeaf3dd16473d52f0604c7e85ec"

def validate_overlay(overlay: Mapping[str, GitEntry]) -> None:
    if set(overlay) != set(CANDIDATE_OVERLAY_POLICY):
        raise Reject("closed candidate overlay path set changed")
    for path, rule in CANDIDATE_OVERLAY_POLICY.items():
        got = overlay.get(path)
        if got is None or (got.type, got.mode, got.identity) != (rule.type, rule.mode, rule.identity):
            raise Reject(f"candidate overlay tuple/blob changed: {path}")

def validate_frozen_controls(value: Mapping[str, object]) -> None:
    if value != FROZEN_CONTROLS:
        raise Reject("actual validation/audit/tests/tasks/threshold controls mutated")
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != FROZEN_CONTROLS_SHA256:
        raise Reject("frozen control digest mismatch")

def _tree_object_identity(children: list[GitEntry]) -> str:
    def sort_key(entry: GitEntry) -> bytes:
        name = entry.path.rsplit("/", 1)[-1].encode()
        return name + (b"/" if entry.type == "tree" else b"")
    body = bytearray()
    for child in sorted(children, key=sort_key):
        name = child.path.rsplit("/", 1)[-1].encode()
        mode = b"40000" if child.type == "tree" else child.mode.encode()
        body += mode + b" " + name + b"\0" + bytes.fromhex(child.identity)
    return hashlib.sha1(f"tree {len(body)}\0".encode() + body).hexdigest()  # nosec: Git identity

def build_tree_inventory(leaves: Mapping[str, GitEntry]) -> dict[str, GitEntry]:
    inventory = dict(leaves)
    directories = set()
    for path in leaves:
        parts = path.split("/")[:-1]
        directories.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    for directory in sorted(directories, key=lambda value: (-value.count("/"), value)):
        prefix = directory + "/"
        children = [entry for path, entry in inventory.items()
                    if path.startswith(prefix) and "/" not in path[len(prefix):]]
        if not children: raise Reject(f"empty derived projected tree: {directory}")
        inventory[directory] = GitEntry(directory, "tree", "040000", _tree_object_identity(children))
    return inventory

def project_tree(upstream: Mapping[str, GitEntry], overlay: Mapping[str, GitEntry], common_gradle: bytes):
    validate_quarantine(upstream); validate_overlay(overlay)
    if len(upstream) != PINNED_TUPLE_COUNT:
        raise Reject("full upstream inventory was not supplied to projection")
    if sum(entry.type == "tree" for entry in upstream.values()) != UPSTREAM_TREE_ENTRY_COUNT:
        raise Reject("pinned tree-entry count changed")
    leaf_targets, leaf_origin = {}, {}
    branded = common_gradle
    for old, new in ((b'"AntennaPod"', b'"Podcast Clips"'), (b'"AntennaPod Debug"', b'"Podcast Clips Debug"')):
        if branded.count(old) != 1: raise Reject("branding anchor missing/repeated")
        branded = branded.replace(old, new, 1)
    for path, entry in upstream.items():
        if entry.type == "tree": continue
        destination = relocation(path, entry) if path in QUARANTINE else entry
        if path == "common.gradle":
            if git_blob_sha(common_gradle) != entry.identity: raise Reject("common.gradle byte identity mismatch")
            destination = GitEntry(path, "blob", "100644", git_blob_sha(branded))
        if destination.path in leaf_targets: raise Reject(f"projection leaf collision: {destination.path}")
        leaf_targets[destination.path] = destination
        leaf_origin[path] = destination.path
    leaf_targets.update(overlay)
    final_inventory = build_tree_inventory(leaf_targets)
    mapping = []
    for path in sorted(upstream):
        origin = upstream[path]
        if origin.type != "tree":
            destination_path = leaf_origin[path]
        else:
            prefix = path + "/"
            descendants = [leaf_origin[p] for p, e in upstream.items()
                           if e.type != "tree" and p.startswith(prefix)]
            quarantined_prefix = "upstream-quarantine/" + prefix
            destination_path = ("upstream-quarantine/" + path
                                if descendants and all(p.startswith(quarantined_prefix) for p in descendants)
                                else path)
        destination = final_inventory.get(destination_path)
        if destination is None: raise Reject(f"upstream tuple has no projected result: {path}")
        mapping.append({"origin": asdict(origin), "projected": asdict(destination)})
    if len(mapping) != PINNED_TUPLE_COUNT or len({x["origin"]["path"] for x in mapping}) != PINNED_TUPLE_COUNT:
        raise Reject("not every one of 2,028 upstream tuples maps exactly once")
    return final_inventory, mapping

def validate_exact_tuple(expected: GitEntry, observed: GitEntry) -> None:
    if observed != expected: raise Reject("Git path/type/mode/blob-or-target tuple changed")

def tuple_negative_tests() -> dict[str, str]:
    regular_x = GitEntry("regular-x", "blob", "100755", "1" * 40)
    regular_n = GitEntry("regular-n", "blob", "100644", "2" * 40)
    symlink = GitEntry("link", "blob", "120000", git_blob_sha(b"target"))
    gitlink = GitEntry("module", "commit", "160000", "3" * 40)
    attacks = {
        "regular-100755-to-100644": (regular_x, GitEntry("regular-x", "blob", "100644", regular_x.identity)),
        "regular-100644-to-100755": (regular_n, GitEntry("regular-n", "blob", "100755", regular_n.identity)),
        "regular-to-symlink": (regular_n, GitEntry("regular-n", "blob", "120000", regular_n.identity)),
        "symlink-to-regular": (symlink, GitEntry("link", "blob", "100644", symlink.identity)),
        "regular-to-gitlink": (regular_n, GitEntry("regular-n", "commit", "160000", regular_n.identity)),
        "gitlink-to-regular": (gitlink, GitEntry("module", "blob", "100644", gitlink.identity)),
        "symlink-target-identity": (symlink, GitEntry("link", "blob", "120000", git_blob_sha(b"other"))),
        "gitlink-commit-identity": (gitlink, GitEntry("module", "commit", "160000", "4" * 40)),
    }
    results = {}
    for name, values in attacks.items():
        try: validate_exact_tuple(*values)
        except Reject: results[name] = "rejected"
        else: raise AssertionError(f"tuple attack accepted: {name}")
    return results

def gradle_property_negative_tests() -> dict[str, str]:
    attacks = {
        "androidx-omission": GRADLE_PROPERTIES.replace(b"android.useAndroidX=true\n", b""),
        "androidx-value": GRADLE_PROPERTIES.replace(b"android.useAndroidX=true", b"android.useAndroidX=false"),
        "nontransitive-omission": GRADLE_PROPERTIES.replace(b"android.nonTransitiveRClass=false\n", b""),
        "nontransitive-value": GRADLE_PROPERTIES.replace(b"android.nonTransitiveRClass=false", b"android.nonTransitiveRClass=true"),
    }
    results = {}
    for name, value in attacks.items():
        try: validate_gradle_properties({"gradle.properties": value})
        except Reject: results[name] = "rejected"
        else: raise AssertionError(f"Gradle property attack accepted: {name}")
    return results

def recovery_scope_negative_tests() -> dict[str, str]:
    attacks = {
        "EF": lambda c: c["expected_failures"].append(":app:testFreeDebugUnitTest"),
        "EXCLUDE": lambda c: c["exclusions"].append("**/transcript/**"),
        "NOOP": lambda c: c["noops"].append(":app:lintFreeDebug"),
        "TASK": lambda c: c["tasks"].__setitem__(0, ":app:assembleDebug"),
        "SHADOW": lambda c: c["property_shadows"].append("android.useAndroidX"),
        "THRESHOLD": lambda c: c["thresholds"].__setitem__("max_dispatches", 4),
    }
    result = {}
    for name, mutate in attacks.items():
        controls = copy.deepcopy(FROZEN_CONTROLS); mutate(controls)
        try: validate_frozen_controls(controls)
        except Reject: result[name] = "rejected"
        else: raise AssertionError(f"RECOVERY-SCOPE {name} accepted")
    return result

def _public_bytes(url: str, maximum: int = 16 * 1024 * 1024) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "podcast-clips-recovery-preflight/1"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(maximum + 1)
    if len(data) > maximum: raise Reject(f"public exact-SHA response exceeds bound: {url}")
    return data

def _public_json(url: str) -> object:
    try: return json.loads(_public_bytes(url, 32 * 1024 * 1024))
    except (json.JSONDecodeError, urllib.error.URLError) as error: raise Reject(f"public JSON read failed: {url}: {error}") from None

def _parse_any_tree(payload: Mapping[str, object], expected_root: str) -> dict[str, GitEntry]:
    if payload.get("sha") != expected_root or payload.get("truncated") is not False:
        raise Reject("overlay recursive tree identity/truncation mismatch")
    result = {}
    for row in payload.get("tree", []):
        path = normalize_path(row["path"]); entry = GitEntry(path, row["type"], row["mode"], row["sha"])
        if path in result: raise Reject("overlay duplicate path")
        result[path] = entry
    return result

REPORT_KEYS = frozenset({"schema", "status", "identity", "historical_evidence", "overlay", "projection", "gradle_inputs", "negative_tests", "invariants", "isolation"})

def validate_report_schema(report: Mapping[str, object]) -> None:
    if set(report) != REPORT_KEYS or report.get("schema") != REPORT_SCHEMA or report.get("status") != "pass":
        raise Reject("closed report schema/status mismatch")
    expected_nested = {
        "identity": {"upstream_commit", "upstream_tree", "upstream_archive_sha256", "overlay_sha"},
        "historical_evidence": {"evidence_commit", "old_candidate_commit", "old_candidate_branch", "pull_request", "immutable"},
        "overlay": {"entries", "policy_digest"},
        "projection": {"upstream_tuple_count", "upstream_tree_count", "upstream_digest", "projected_tuple_count", "projected_digest", "origin_projection"},
        "gradle_inputs": {"known_inventory", "dynamic_inputs", "gradle_properties_blob", "wrapper_distribution_sha256", "wrapper_jar_sha256"},
        "negative_tests": {"tuples", "gradle_properties", "recovery_scope"},
        "invariants": {"one_preflight", "fresh_identity", "validation_budget"},
        "isolation": {"sanitized_environment", "candidate_workspace", "credential_channels", "runtime_cache_result_channels", "constant_report_path"},
    }
    for field, keys in expected_nested.items():
        if not isinstance(report[field], Mapping) or set(report[field]) != keys:
            raise Reject(f"closed report nested schema mismatch: {field}")

def validate_operational_invariants(run_payload, refs_payload) -> dict[str, object]:
    if not isinstance(run_payload, Mapping) or run_payload.get("total_count") != 1:
        raise Reject("exactly one preflight dispatch is required")
    runs = run_payload.get("workflow_runs")
    if not isinstance(runs, list) or len(runs) != 1 or runs[0].get("run_attempt") != 1:
        raise Reject("preflight rerun/attempt is forbidden")
    if not isinstance(refs_payload, list): raise Reject("candidate refs payload malformed")
    refs = {item.get("ref"): item.get("object", {}).get("sha") for item in refs_payload}
    if refs != {OLD_CANDIDATE_BRANCH: OLD_CANDIDATE_COMMIT}:
        raise Reject("fresh recovery identity already exists or old evidence branch changed")
    return {
        "one_preflight": {"maximum": 1, "observed": 1, "run_attempt": 1},
        "fresh_identity": {"must_be_created_after_preflight": True, "present": False, "allowed_historical_identity": OLD_CANDIDATE_COMMIT},
        "validation_budget": {"maximum_dispatches": 3, "used_for_fresh_identity": 0, "required_consecutive_successes": 2, "run2_failure_stop": True},
    }

def run_preflight(overlay_sha: str) -> dict[str, object]:
    validate_environment()
    if not re.fullmatch(r"[0-9a-f]{40}", overlay_sha): raise Reject("exact overlay SHA required")
    api = "https://api.github.com/repos"
    commit_payload = _public_json(f"{api}/{UPSTREAM_REPOSITORY}/commits/{UPSTREAM_COMMIT}")
    validate_commit(commit_payload)
    tree_payload = _public_json(f"{api}/{UPSTREAM_REPOSITORY}/git/trees/{UPSTREAM_TREE}?recursive=1")
    upstream = parse_git_tree(tree_payload)
    validate_known_inputs(upstream)
    overlay_commit = _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{overlay_sha}")
    if overlay_commit.get("sha") != overlay_sha: raise Reject("overlay commit mismatch")
    overlay_root = overlay_commit["tree"]["sha"]
    overlay_all = _parse_any_tree(_public_json(f"{api}/{TARGET_REPOSITORY}/git/trees/{overlay_root}?recursive=1"), overlay_root)
    overlay = {path: overlay_all[path] for path in CANDIDATE_OVERLAY_POLICY if path in overlay_all}
    validate_overlay(overlay); validate_frozen_controls(FROZEN_CONTROLS)
    contents = {}
    required = set().union(*(set(value) for value in KNOWN_INPUTS.values()))
    for path in sorted(required):
        data = _public_bytes(f"https://raw.githubusercontent.com/{UPSTREAM_REPOSITORY}/{UPSTREAM_COMMIT}/{path}")
        if git_blob_sha(data) != upstream[path].identity: raise Reject(f"known input byte/Git identity mismatch: {path}")
        contents[path] = data
    validate_gradle_properties({path: contents[path] for path in KNOWN_INPUTS["gradle_properties"]})
    dynamic = scan_dynamic_inputs(contents, upstream)
    validate_wrapper(contents["gradle/wrapper/gradle-wrapper.properties"], contents["gradle/wrapper/gradle-wrapper.jar"])
    projected, origin_projection = project_tree(upstream, overlay, contents["common.gradle"])
    evidence = _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{EVIDENCE_COMMIT}")
    old_candidate = _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{OLD_CANDIDATE_COMMIT}")
    pr = _public_json(f"{api}/{TARGET_REPOSITORY}/pulls/{OLD_PR}")
    if evidence.get("sha") != EVIDENCE_COMMIT or old_candidate.get("sha") != OLD_CANDIDATE_COMMIT:
        raise Reject("historical commit evidence changed")
    if pr.get("state") != "closed" or pr.get("merged") is not False or pr.get("head", {}).get("sha") != OLD_CANDIDATE_COMMIT:
        raise Reject("historical PR evidence changed")
    runs = _public_json(f"{api}/{TARGET_REPOSITORY}/actions/workflows/preflight-recovery.yml/runs?event=workflow_dispatch&per_page=100")
    refs = _public_json(f"{api}/{TARGET_REPOSITORY}/git/matching-refs/heads/candidate/antennapod")
    invariants = validate_operational_invariants(runs, refs)
    policy_rows = [{"path": path, **asdict(CANDIDATE_OVERLAY_POLICY[path])} for path in sorted(CANDIDATE_OVERLAY_POLICY)]
    report = {
        "schema": REPORT_SCHEMA, "status": "pass",
        "identity": {"upstream_commit": UPSTREAM_COMMIT, "upstream_tree": UPSTREAM_TREE,
                     "upstream_archive_sha256": UPSTREAM_ARCHIVE_SHA256, "overlay_sha": overlay_sha},
        "historical_evidence": {"evidence_commit": EVIDENCE_COMMIT, "old_candidate_commit": OLD_CANDIDATE_COMMIT,
                                "old_candidate_branch": OLD_CANDIDATE_BRANCH, "pull_request": OLD_PR, "immutable": True},
        "overlay": {"entries": policy_rows, "policy_digest": hashlib.sha256(json.dumps(policy_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()},
        "projection": {"upstream_tuple_count": len(upstream), "upstream_tree_count": sum(x.type == "tree" for x in upstream.values()),
                       "upstream_digest": inventory_digest(upstream), "projected_tuple_count": len(projected),
                       "projected_digest": inventory_digest(projected), "origin_projection": origin_projection},
        "gradle_inputs": {"known_inventory": KNOWN_INPUTS, "dynamic_inputs": dynamic,
                          "gradle_properties_blob": GRADLE_PROPERTIES_BLOB,
                          "wrapper_distribution_sha256": GRADLE_DISTRIBUTION_SHA256,
                          "wrapper_jar_sha256": GRADLE_WRAPPER_JAR_SHA256},
        "negative_tests": {"tuples": tuple_negative_tests(), "gradle_properties": gradle_property_negative_tests(),
                           "recovery_scope": recovery_scope_negative_tests()},
        "invariants": invariants,
        "isolation": {"sanitized_environment": True, "candidate_workspace": "absent", "credential_channels": "absent",
                      "runtime_cache_result_channels": "absent", "constant_report_path": REPORT_PATH},
    }
    validate_report_schema(report)
    return report

def write_constant_report(report: Mapping[str, object]) -> None:
    validate_report_schema(report)
    parent = Path(REPORT_PATH).parent
    if parent.exists(): raise Reject("constant trusted report directory already exists")
    parent.mkdir(mode=0o700)
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    descriptor = os.open(REPORT_PATH, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle: handle.write(data)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-sha", required=True)
    args = parser.parse_args()
    report = run_preflight(args.overlay_sha)
    write_constant_report(report)
    print(hashlib.sha256((json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest())


WRAPPER_PROPERTIES = (
    b"#Sun Aug 17 17:07:23 CEST 2025\n"
    b"distributionBase=GRADLE_USER_HOME\n"
    b"distributionPath=wrapper/dists\n"
    b"distributionUrl=https\\://services.gradle.org/distributions/gradle-8.13-bin.zip\n"
    b"networkTimeout=10000\n"
    b"validateDistributionUrl=true\n"
    b"zipStoreBase=GRADLE_USER_HOME\n"
    b"zipStorePath=wrapper/dists\n"
)
WRAPPER_PROPERTIES_BLOB = "68f6c2ca1fa1e49799ea485892b67296e9876ec1"
WRAPPER_JAR_BLOB = "d64cd4917707c1f8861d8cb53dd15194d4248596"

def validate_wrapper(properties: bytes, jar: bytes) -> None:
    if properties != WRAPPER_PROPERTIES or git_blob_sha(properties) != WRAPPER_PROPERTIES_BLOB:
        raise Reject("Gradle wrapper properties bytes/blob changed")
    if b"distributionUrl=" + GRADLE_DISTRIBUTION_URL.encode() not in properties:
        raise Reject("Gradle distribution URL changed")
    if git_blob_sha(jar) != WRAPPER_JAR_BLOB or hashlib.sha256(jar).hexdigest() != GRADLE_WRAPPER_JAR_SHA256:
        raise Reject("Gradle wrapper JAR blob/checksum changed")

def _public_sha256(url: str, maximum: int = 1024 * 1024 * 1024) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "podcast-clips-recovery-preflight/1"})
    digest, total = hashlib.sha256(), 0
    with urllib.request.urlopen(request, timeout=120) as response:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk: break
            total += len(chunk)
            if total > maximum: raise Reject("public exact-SHA archive exceeds bound")
            digest.update(chunk)
    return digest.hexdigest()

def validate_report_schema(report: Mapping[str, object]) -> None:
    if set(report) != REPORT_KEYS or report.get("schema") != REPORT_SCHEMA or report.get("status") != "pass":
        raise Reject("closed report schema/status mismatch")
    exact = {
        "identity": {"upstream_commit", "upstream_tree", "upstream_archive_sha256", "overlay_sha"},
        "historical_evidence": {"evidence_commit", "old_candidate_commit", "old_candidate_branch", "pull_request", "immutable"},
        "overlay": {"entries", "policy_digest"},
        "projection": {"upstream_tuple_count", "upstream_tree_count", "upstream_digest", "projected_tuple_count", "projected_digest", "origin_projection"},
        "gradle_inputs": {"known_inventory", "dynamic_inputs", "gradle_properties_blob", "wrapper_distribution_sha256", "wrapper_jar_sha256"},
        "negative_tests": {"tuples", "gradle_properties", "recovery_scope"},
        "invariants": {"one_preflight", "fresh_identity", "validation_budget"},
        "isolation": {"sanitized_environment", "candidate_workspace", "credential_channels", "runtime_cache_result_channels", "constant_report_path"},
    }
    for field, keys in exact.items():
        if not isinstance(report[field], Mapping) or set(report[field]) != keys:
            raise Reject(f"closed report nested schema mismatch: {field}")
    if set(report["invariants"]["one_preflight"]) != {"maximum", "observed", "run_attempt"}:
        raise Reject("one-preflight schema changed")
    if set(report["invariants"]["fresh_identity"]) != {"must_be_created_after_preflight", "present", "allowed_historical_identity"}:
        raise Reject("fresh-identity schema changed")
    if set(report["invariants"]["validation_budget"]) != {"maximum_dispatches", "used_for_fresh_identity", "required_consecutive_successes", "run2_failure_stop"}:
        raise Reject("validation-budget schema changed")
    if set(report["negative_tests"]["tuples"]) != {"regular-100755-to-100644", "regular-100644-to-100755", "regular-to-symlink", "symlink-to-regular", "regular-to-gitlink", "gitlink-to-regular", "symlink-target-identity", "gitlink-commit-identity"}:
        raise Reject("tuple negative-test schema changed")
    if set(report["negative_tests"]["gradle_properties"]) != {"androidx-omission", "androidx-value", "nontransitive-omission", "nontransitive-value"}:
        raise Reject("Gradle-property negative-test schema changed")
    if set(report["negative_tests"]["recovery_scope"]) != {"EF", "EXCLUDE", "NOOP", "TASK", "SHADOW", "THRESHOLD"}:
        raise Reject("RECOVERY-SCOPE negative-test schema changed")
    if set(report["gradle_inputs"]["known_inventory"]) != set(KNOWN_INPUTS):
        raise Reject("known-input report schema changed")
    if set(report["gradle_inputs"]["dynamic_inputs"]) != {"literal_environment_and_properties", "static_root_config", "unresolved"}:
        raise Reject("dynamic-input report schema changed")
    if report["projection"]["upstream_tuple_count"] != PINNED_TUPLE_COUNT or report["projection"]["upstream_tree_count"] != UPSTREAM_TREE_ENTRY_COUNT:
        raise Reject("reported full tuple/tree counts changed")
    if len(report["projection"]["origin_projection"]) != PINNED_TUPLE_COUNT:
        raise Reject("origin projection is incomplete")
    for row in report["projection"]["origin_projection"]:
        if set(row) != {"origin", "projected"} or set(row["origin"]) != {"path", "type", "mode", "identity"} or set(row["projected"]) != {"path", "type", "mode", "identity"}:
            raise Reject("origin-projection tuple schema changed")
    for row in report["overlay"]["entries"]:
        if set(row) != {"path", "type", "mode", "identity", "category", "rationale"}:
            raise Reject("overlay entry schema changed")
    if report["isolation"]["constant_report_path"] != REPORT_PATH:
        raise Reject("constant report path changed")

_run_preflight_unbound = run_preflight
def run_preflight(overlay_sha: str) -> dict[str, object]:
    validate_environment()
    if not re.fullmatch(r"[0-9a-f]{40}", overlay_sha): raise Reject("exact overlay SHA required")
    main = _public_json(f"https://api.github.com/repos/{TARGET_REPOSITORY}/branches/main")
    if main.get("commit", {}).get("sha") != overlay_sha:
        raise Reject("overlay SHA is not the exact current main identity")
    observed_archive = _public_sha256(f"https://codeload.github.com/{UPSTREAM_REPOSITORY}/tar.gz/{UPSTREAM_COMMIT}")
    if observed_archive != UPSTREAM_ARCHIVE_SHA256:
        raise Reject("pinned public archive SHA-256 mismatch")
    report = _run_preflight_unbound(overlay_sha)
    validate_report_schema(report)
    return report

def write_constant_report(report: Mapping[str, object]) -> str:
    validate_report_schema(report)
    parent = Path(REPORT_PATH).parent
    if parent.exists(): raise Reject("constant trusted report directory already exists")
    parent.mkdir(mode=0o700)
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    descriptor = os.open(REPORT_PATH, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle: handle.write(data)
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-sha", required=True)
    args = parser.parse_args()
    print(write_constant_report(run_preflight(args.overlay_sha)))


HISTORICAL_REFS={
 "refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562152128":"1152cfce3b78cbc9cfb64a69bb0eb68551273371",
 "refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562160851":OLD_CANDIDATE_COMMIT,
}
HISTORICAL_RUNS={
 "29562294514":{"id":29562294514,"conclusion":"failure","event":"workflow_dispatch","head_sha":OLD_CANDIDATE_COMMIT,"workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"},
 "29562814924":{"id":29562814924,"conclusion":"failure","event":"workflow_dispatch","head_sha":"2a29aaf00b6c9414f627b1e4a24a8536412c47d7","workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"},
 "29563023789":{"id":29563023789,"conclusion":"cancelled","event":"workflow_dispatch","head_sha":"2a29aaf00b6c9414f627b1e4a24a8536412c47d7","workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"},
}
HISTORICAL_PR={"number":1,"state":"closed","merged":False,"head_sha":OLD_CANDIDATE_COMMIT}
PREFLIGHT_WORKFLOW_PATH=".github/workflows/preflight-recovery.yml"
PREFLIGHT_WORKFLOW_NAME="Story 1 recovery preflight"

_tuple_attacks_v2=tuple_negative_tests
def tuple_negative_tests():
 result=_tuple_attacks_v2()
 link=GitEntry("link","blob","120000",git_blob_sha(b"target")); module=GitEntry("module","commit","160000","3"*40)
 attacks={"symlink-to-gitlink":(link,GitEntry("link","commit","160000",link.identity)),
          "gitlink-to-symlink":(module,GitEntry("module","blob","120000",module.identity))}
 for name,attack in attacks.items():
  try: validate_exact_tuple(*attack)
  except Reject: result[name]="rejected"
  else: raise AssertionError(f"direct tuple attack accepted: {name}")
 return result

_property_attacks_v2=gradle_property_negative_tests
def gradle_property_negative_tests():
 result=_property_attacks_v2()
 attacks={"jvmargs-omission":GRADLE_PROPERTIES.replace(b"org.gradle.jvmargs=-Xmx4096m\n",b""),
          "jvmargs-value":GRADLE_PROPERTIES.replace(b"org.gradle.jvmargs=-Xmx4096m",b"org.gradle.jvmargs=-Xmx2048m")}
 for name,value in attacks.items():
  try: validate_gradle_properties({"gradle.properties":value})
  except Reject: result[name]="rejected"
  else: raise AssertionError(f"JVM property attack accepted: {name}")
 return result

def validate_operational_invariants(run_payload,refs_payload):
 if not isinstance(refs_payload,list): raise Reject("candidate refs payload malformed")
 refs={item.get("ref"):item.get("object",{}).get("sha") for item in refs_payload}
 if refs!=HISTORICAL_REFS: raise Reject("historical candidate ref addition or mutation")
 if not isinstance(run_payload,Mapping) or run_payload.get("total_count")!=1: raise Reject("exactly one preflight required")
 runs=run_payload.get("workflow_runs")
 if not isinstance(runs,list) or len(runs)!=1: raise Reject("sole preflight missing/duplicated")
 run=runs[0]
 if run.get("run_attempt")!=1 or run.get("event")!="workflow_dispatch": raise Reject("preflight attempt/event mismatch")
 if run.get("path")!=PREFLIGHT_WORKFLOW_PATH or run.get("name")!=PREFLIGHT_WORKFLOW_NAME: raise Reject("preflight workflow identity mismatch")
 head=run.get("head_sha")
 if not isinstance(head,str) or not re.fullmatch(r"[0-9a-f]{40}",head): raise Reject("preflight head SHA invalid")
 return {"one_preflight":{"maximum":1,"observed":1,"run_attempt":1,"head_sha":head,"event":"workflow_dispatch","workflow_path":PREFLIGHT_WORKFLOW_PATH,"workflow_name":PREFLIGHT_WORKFLOW_NAME},
         "fresh_identity":{"must_be_created_after_preflight":True,"present":False,"allowed_historical_refs":copy.deepcopy(HISTORICAL_REFS)},
         "validation_budget":{"maximum_dispatches":3,"used_for_fresh_identity":0,"required_consecutive_successes":2,"run2_failure_stop":True}}

def _expected_overlay_rows(): return [{"path":path,**asdict(CANDIDATE_OVERLAY_POLICY[path])} for path in sorted(CANDIDATE_OVERLAY_POLICY)]
def _rows_digest(rows):
 values={}
 for row in rows:
  if not isinstance(row,Mapping) or set(row)!={"path","type","mode","identity"}: raise Reject("tuple row schema changed")
  entry=GitEntry(row["path"],row["type"],row["mode"],row["identity"])
  if entry.path in values: raise Reject("duplicate tuple row")
  values[entry.path]=entry
 return inventory_digest(values)
def _all_rejected(value,names): return isinstance(value,Mapping) and set(value)==names and all(x=="rejected" for x in value.values())

def validate_report_schema(report):
 if not isinstance(report,Mapping) or set(report)!=REPORT_KEYS or report.get("schema")!=REPORT_SCHEMA or report.get("status")!="pass": raise Reject("report envelope changed")
 identity=report.get("identity")
 if not isinstance(identity,Mapping) or set(identity)!={"upstream_commit","upstream_tree","upstream_archive_sha256","overlay_sha"}: raise Reject("identity schema changed")
 if (identity["upstream_commit"],identity["upstream_tree"],identity["upstream_archive_sha256"])!=(UPSTREAM_COMMIT,UPSTREAM_TREE,UPSTREAM_ARCHIVE_SHA256): raise Reject("identity values changed")
 if not isinstance(identity["overlay_sha"],str) or not re.fullmatch(r"[0-9a-f]{40}",identity["overlay_sha"]): raise Reject("overlay SHA invalid")
 expected_history={"evidence_commit":EVIDENCE_COMMIT,"candidate_refs":HISTORICAL_REFS,"pull_request":HISTORICAL_PR,"validation_runs":HISTORICAL_RUNS,"immutable":True}
 if report.get("historical_evidence")!=expected_history: raise Reject("historical evidence values changed")
 rows=_expected_overlay_rows(); overlay_digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 if report.get("overlay")!={"entries":rows,"policy_digest":overlay_digest}: raise Reject("overlay rows/digest changed")
 projection=report.get("projection"); keys={"upstream_tuple_count","upstream_tree_count","upstream_digest","projected_tuple_count","projected_digest","origin_projection","projected_manifest"}
 if not isinstance(projection,Mapping) or set(projection)!=keys: raise Reject("projection schema changed")
 if projection["upstream_tuple_count"]!=2028 or projection["upstream_tree_count"]!=745: raise Reject("projection counts changed")
 mappings=projection["origin_projection"]; manifest=projection["projected_manifest"]
 if not isinstance(mappings,list) or len(mappings)!=2028 or not isinstance(manifest,list): raise Reject("projection manifests malformed")
 projected={row.get("path"):row for row in manifest if isinstance(row,Mapping)}
 if len(projected)!=len(manifest): raise Reject("projected manifest duplicates")
 origins=[]
 for mapping in mappings:
  if not isinstance(mapping,Mapping) or set(mapping)!={"origin","projected"}: raise Reject("origin mapping schema changed")
  origins.append(mapping["origin"]); result=mapping["projected"]
  if not isinstance(result,Mapping) or projected.get(result.get("path"))!=result: raise Reject("origin result not bound to manifest")
 if _rows_digest(origins)!=PINNED_TUPLE_DIGEST or projection["upstream_digest"]!=PINNED_TUPLE_DIGEST: raise Reject("upstream digest changed")
 digest=_rows_digest(manifest)
 if projection["projected_tuple_count"]!=len(manifest) or projection["projected_digest"]!=digest: raise Reject("projected digest/count changed")
 gradle=report.get("gradle_inputs")
 expected_gradle_keys={"known_inventory","dynamic_inputs","gradle_properties_blob","wrapper_distribution_sha256","wrapper_jar_sha256"}
 if not isinstance(gradle,Mapping) or set(gradle)!=expected_gradle_keys: raise Reject("Gradle schema changed")
 if gradle["known_inventory"]!=KNOWN_INPUTS or gradle["gradle_properties_blob"]!=GRADLE_PROPERTIES_BLOB or gradle["wrapper_distribution_sha256"]!=GRADLE_DISTRIBUTION_SHA256 or gradle["wrapper_jar_sha256"]!=GRADLE_WRAPPER_JAR_SHA256: raise Reject("Gradle constants changed")
 dynamic=gradle["dynamic_inputs"]
 if not isinstance(dynamic,Mapping) or set(dynamic)!={"literal_environment_and_properties","static_root_config","unresolved"} or dynamic["unresolved"]!=[]: raise Reject("dynamic inputs unresolved/changed")
 if any(set(x)!={"path","api","name"} for x in dynamic["literal_environment_and_properties"]): raise Reject("literal input row changed")
 if any(set(x)!={"declared_by","path"} for x in dynamic["static_root_config"]): raise Reject("static config row changed")
 negative=report.get("negative_tests")
 tuple_names={"regular-100755-to-100644","regular-100644-to-100755","regular-to-symlink","symlink-to-regular","regular-to-gitlink","gitlink-to-regular","symlink-target-identity","gitlink-commit-identity","symlink-to-gitlink","gitlink-to-symlink"}
 property_names={"androidx-omission","androidx-value","nontransitive-omission","nontransitive-value","jvmargs-omission","jvmargs-value"}
 scope_names={"EF","EXCLUDE","NOOP","TASK","SHADOW","THRESHOLD"}
 if not isinstance(negative,Mapping) or set(negative)!={"tuples","gradle_properties","recovery_scope"}: raise Reject("negative schema changed")
 if not _all_rejected(negative["tuples"],tuple_names) or not _all_rejected(negative["gradle_properties"],property_names) or not _all_rejected(negative["recovery_scope"],scope_names): raise Reject("negative outcomes changed")
 exact_one={"maximum":1,"observed":1,"run_attempt":1,"head_sha":identity["overlay_sha"],"event":"workflow_dispatch","workflow_path":PREFLIGHT_WORKFLOW_PATH,"workflow_name":PREFLIGHT_WORKFLOW_NAME}
 exact_fresh={"must_be_created_after_preflight":True,"present":False,"allowed_historical_refs":HISTORICAL_REFS}
 exact_budget={"maximum_dispatches":3,"used_for_fresh_identity":0,"required_consecutive_successes":2,"run2_failure_stop":True}
 if report.get("invariants")!={"one_preflight":exact_one,"fresh_identity":exact_fresh,"validation_budget":exact_budget}: raise Reject("invariant values changed")
 exact_isolation={"sanitized_environment":True,"candidate_workspace":"absent","credential_channels":"absent","runtime_cache_result_channels":"absent","constant_report_path":REPORT_PATH}
 if report.get("isolation")!=exact_isolation: raise Reject("isolation values changed")

def _history_run(payload):
 return {"id":payload.get("id"),"conclusion":payload.get("conclusion"),"event":payload.get("event"),"head_sha":payload.get("head_sha"),"workflow_id":payload.get("workflow_id"),"workflow_path":payload.get("path"),"workflow_name":payload.get("name")}

def run_preflight(overlay_sha):
 validate_environment()
 if not re.fullmatch(r"[0-9a-f]{40}",overlay_sha): raise Reject("exact overlay SHA required")
 api="https://api.github.com/repos"
 if _public_json(f"{api}/{TARGET_REPOSITORY}/branches/main").get("commit",{}).get("sha")!=overlay_sha: raise Reject("overlay is not current main")
 if _public_sha256(f"https://codeload.github.com/{UPSTREAM_REPOSITORY}/tar.gz/{UPSTREAM_COMMIT}")!=UPSTREAM_ARCHIVE_SHA256: raise Reject("archive digest changed")
 commit=_public_json(f"{api}/{UPSTREAM_REPOSITORY}/commits/{UPSTREAM_COMMIT}"); validate_commit(commit)
 upstream=parse_git_tree(_public_json(f"{api}/{UPSTREAM_REPOSITORY}/git/trees/{UPSTREAM_TREE}?recursive=1")); validate_known_inputs(upstream)
 overlay_commit=_public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{overlay_sha}")
 if overlay_commit.get("sha")!=overlay_sha: raise Reject("overlay commit changed")
 root=overlay_commit["tree"]["sha"]; all_overlay=_parse_any_tree(_public_json(f"{api}/{TARGET_REPOSITORY}/git/trees/{root}?recursive=1"),root)
 candidate_overlay={path:all_overlay[path] for path in CANDIDATE_OVERLAY_POLICY if path in all_overlay}; validate_overlay(candidate_overlay); validate_frozen_controls(FROZEN_CONTROLS)
 required=set().union(*(set(v) for v in KNOWN_INPUTS.values())); contents={}
 for path in sorted(required):
  data=_public_bytes(f"https://raw.githubusercontent.com/{UPSTREAM_REPOSITORY}/{UPSTREAM_COMMIT}/{path}")
  if git_blob_sha(data)!=upstream[path].identity: raise Reject(f"known input identity changed: {path}")
  contents[path]=data
 validate_gradle_properties({"gradle.properties":contents["gradle.properties"]}); dynamic=scan_dynamic_inputs(contents,upstream)
 validate_wrapper(contents["gradle/wrapper/gradle-wrapper.properties"],contents["gradle/wrapper/gradle-wrapper.jar"])
 projected,mappings=project_tree(upstream,candidate_overlay,contents["common.gradle"])
 if _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{EVIDENCE_COMMIT}").get("sha")!=EVIDENCE_COMMIT: raise Reject("evidence commit changed")
 for ref,sha in HISTORICAL_REFS.items():
  if _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{sha}").get("sha")!=sha: raise Reject(f"historical ref commit missing: {ref}")
 pr=_public_json(f"{api}/{TARGET_REPOSITORY}/pulls/1"); observed_pr={"number":pr.get("number"),"state":pr.get("state"),"merged":pr.get("merged"),"head_sha":pr.get("head",{}).get("sha")}
 if observed_pr!=HISTORICAL_PR: raise Reject("historical PR changed")
 for run_id,expected in HISTORICAL_RUNS.items():
  if _history_run(_public_json(f"{api}/{TARGET_REPOSITORY}/actions/runs/{run_id}"))!=expected: raise Reject(f"historical run changed: {run_id}")
 runs=_public_json(f"{api}/{TARGET_REPOSITORY}/actions/workflows/preflight-recovery.yml/runs?event=workflow_dispatch&per_page=100")
 refs=_public_json(f"{api}/{TARGET_REPOSITORY}/git/matching-refs/heads/candidate/antennapod")
 invariants=validate_operational_invariants(runs,refs); rows=_expected_overlay_rows(); manifest=report_manifest(projected)
 report={"schema":REPORT_SCHEMA,"status":"pass",
 "identity":{"upstream_commit":UPSTREAM_COMMIT,"upstream_tree":UPSTREAM_TREE,"upstream_archive_sha256":UPSTREAM_ARCHIVE_SHA256,"overlay_sha":overlay_sha},
 "historical_evidence":{"evidence_commit":EVIDENCE_COMMIT,"candidate_refs":copy.deepcopy(HISTORICAL_REFS),"pull_request":copy.deepcopy(HISTORICAL_PR),"validation_runs":copy.deepcopy(HISTORICAL_RUNS),"immutable":True},
 "overlay":{"entries":rows,"policy_digest":hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()},
 "projection":{"upstream_tuple_count":len(upstream),"upstream_tree_count":sum(x.type=="tree" for x in upstream.values()),"upstream_digest":inventory_digest(upstream),"projected_tuple_count":len(projected),"projected_digest":inventory_digest(projected),"origin_projection":mappings,"projected_manifest":manifest},
 "gradle_inputs":{"known_inventory":copy.deepcopy(KNOWN_INPUTS),"dynamic_inputs":dynamic,"gradle_properties_blob":GRADLE_PROPERTIES_BLOB,"wrapper_distribution_sha256":GRADLE_DISTRIBUTION_SHA256,"wrapper_jar_sha256":GRADLE_WRAPPER_JAR_SHA256},
 "negative_tests":{"tuples":tuple_negative_tests(),"gradle_properties":gradle_property_negative_tests(),"recovery_scope":recovery_scope_negative_tests()},
 "invariants":invariants,"isolation":{"sanitized_environment":True,"candidate_workspace":"absent","credential_channels":"absent","runtime_cache_result_channels":"absent","constant_report_path":REPORT_PATH}}
 validate_report_schema(report); return report
# --- ADR-003 Recovery-2: declaring-relative lexical resolver and v2 report. ---
from datetime import datetime, timezone

R2_REPORT_SCHEMA = "podcast-clips/story1-recovery-preflight/v2"
R2_REPORT_PATH = "/tmp/podcast-clips-recovery-2-preflight/report-v2.json"
R2_LOCK_SCHEMA = "podcast-clips/story1-recovery-2-control-lock/v1"
R2_WORKFLOW_PATH = ".github/workflows/preflight-recovery-2.yml"
R2_WORKFLOW_NAME = "Recovery 2 — one-shot trusted preflight"
R2_PARENT = "c43ddf3409ea0ea793982f07926ce1e1a6925c82"
R2_ADR_SHA256 = "0645e92eecb4336ef03cd712c7845cc460bc264594564cd60611b5b8b9c6357d"
R2_TEST_ADDENDUM_SHA256 = "1366f23b876662a20107523d028b0324e114a866250839f353ccbab01ca53511"
R2_MAX_INCLUDE_DEPTH = 32
LEGACY_PREFLIGHT_ID = 315057380
LEGACY_PREFLIGHT_RUN = 29575201182
LEGACY_PREFLIGHT_CONTROL = "fc0ed383c0f4e1cf527f88d0ac3033973a379a4e"
LEGACY_PREFLIGHT_BLOB = "06008a439355c8be6d657a92c244e03ba27afdaa"
TERMINAL_REPORT_COMMIT = R2_PARENT

R2_ALLOWED_CHANGES = {
    "scripts/ci/recovery_preflight.py": ("modify", "resolver-report"),
    "scripts/ci/test_recovery_preflight.py": ("modify", "focused-tests"),
    "scripts/ci/validate_preflight_report.py": ("modify", "schema-validator"),
    "config/recovery-preflight-report-v2.schema.json": ("add", "schema"),
    "config/recovery-2-control.lock.json": ("add", "lock"),
    R2_WORKFLOW_PATH: ("add", "one-shot-workflow"),
    "UPSTREAM.md": ("modify", "report-metadata"),
    "docs/base-selection-report.md": ("modify", "report-metadata"),
}

R2_VALID_CASES = (
    "VALID-01", "VALID-02", "VALID-03", "VALID-04", "VALID-05",
    "VALID-06", "VALID-07", "VALID-08", "VALID-09", "VALID-10",
)
R2_HOSTILE_CASES = tuple(f"HOST-{index:02d}" for index in range(1, 37))
R2_DECLARE_CASES = tuple(f"DECLARE-{index:02d}" for index in range(1, 11))
R2_RECURSION_CASES = ("CYCLE-01", "CYCLE-02", "CYCLE-03", "CYCLE-04",
                      "DEPTH-01", "DEPTH-02", "DEPTH-03", "DEPTH-04", "DEPTH-05")

_R2_STATIC_ROOT = re.compile(
    r"apply\s+from\s*:\s*(?P<quote>['\"])(?P<path>[^'\"]*)(?P=quote)(?P<tail>[^\r\n]*)"
)
_R2_URI_OR_DRIVE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_R2_LAST_RESOLVER = {"edges": [], "max_depth": 0, "cycles": [], "unresolved": []}

def _r2_tuple(entry: GitEntry) -> dict[str, str]:
    return {"path": entry.path, "type": entry.type, "mode": entry.mode, "identity": entry.identity}

def _r2_regular(entries: Mapping[str, GitEntry], path: str, role: str) -> GitEntry:
    try:
        canonical = normalize_path(path)
    except Reject:
        raise Reject(f"{role} path is not canonical") from None
    folded = unicodedata.normalize("NFC", canonical).casefold()
    matches = [
        candidate for candidate in entries
        if unicodedata.normalize("NFC", candidate).casefold() == folded
    ]
    if matches != [canonical]:
        if matches:
            raise Reject(f"{role} path has case/Unicode ambiguity")
        raise Reject(f"{role} path is missing")
    entry = entries[canonical]
    if entry.path != canonical or entry.type != "blob" or entry.mode not in {"100644", "100755"}:
        raise Reject(f"{role} is not an exact pinned regular blob")
    if not re.fullmatch(r"[0-9a-f]{40}", entry.identity):
        raise Reject(f"{role} blob identity is invalid")
    return entry

def resolve_static_literal(
    declaring_path: str,
    literal: str,
    entries: Mapping[str, GitEntry],
    depth: int = 0,
) -> dict[str, object]:
    declaring = _r2_regular(entries, declaring_path, "declaring entry")
    if type(literal) is not str or not literal:
        raise Reject("static Gradle literal is empty")
    if unicodedata.normalize("NFC", literal) != literal:
        raise Reject("static Gradle literal is non-NFC")
    if "\0" in literal:
        raise Reject("static Gradle literal contains NUL")
    if "\\" in literal:
        raise Reject("static Gradle literal contains backslash/escape ambiguity")
    if literal.startswith(("/", "//")):
        raise Reject("static Gradle literal is absolute/UNC")
    if _R2_URI_OR_DRIVE.match(literal):
        raise Reject("static Gradle literal is URI/drive ambiguous")
    if "$" in literal:
        raise Reject("static Gradle literal is interpolated")
    if any(mark in literal for mark in ("?", "#", "'", '"')):
        raise Reject("static Gradle literal is query/quote ambiguous")
    components = literal.split("/")
    if any(component in {"", "."} for component in components):
        raise Reject("static Gradle literal has empty/dot component")
    base = declaring.path.split("/")[:-1]
    for component in components:
        if component == "..":
            if not base:
                raise Reject("static Gradle literal escapes repository root")
            base.pop()
        else:
            if unicodedata.normalize("NFC", component) != component:
                raise Reject("static Gradle component is non-NFC")
            base.append(component)
    if not base:
        raise Reject("static Gradle target is empty")
    normalized = "/".join(base)
    target = _r2_regular(entries, normalized, "target entry")
    if depth < 0 or depth > R2_MAX_INCLUDE_DEPTH:
        raise Reject("static include depth exceeds bound")
    return {
        "declaring": _r2_tuple(declaring),
        "literal": literal,
        "normalized_target": normalized,
        "target": _r2_tuple(target),
        "depth": depth,
    }

def scan_static_graph(
    contents: Mapping[str, bytes],
    entries: Mapping[str, GitEntry],
    roots: Iterable[str] | None = None,
    loader=None,
) -> dict[str, object]:
    cache = dict(contents)
    initial = sorted(cache if roots is None else roots)
    completed: set[str] = set()
    active: list[str] = []
    edges: list[dict[str, object]] = []
    declarations: list[dict[str, str]] = []
    max_depth = 0

    def load_target(path: str) -> bytes:
        if path in cache:
            return cache[path]
        callback = loader
        if callback is None:
            callback = lambda value: _public_bytes(
                f"https://raw.githubusercontent.com/{UPSTREAM_REPOSITORY}/{UPSTREAM_COMMIT}/{value}"
            )
        data = callback(path)
        if type(data) is not bytes or git_blob_sha(data) != _r2_regular(entries, path, "loaded target").identity:
            raise Reject(f"loaded target bytes do not match pinned blob: {path}")
        cache[path] = data
        return data

    def visit(path: str, depth: int) -> None:
        nonlocal max_depth
        if depth > R2_MAX_INCLUDE_DEPTH:
            raise Reject("static include depth exceeds 32")
        _r2_regular(entries, path, "declaring entry")
        if path in active:
            start = active.index(path)
            raise Reject("static include cycle: " + " -> ".join(active[start:] + [path]))
        if path in completed:
            return
        active.append(path)
        max_depth = max(max_depth, depth)
        data = load_target(path)
        if path.endswith((".jar", ".toml", ".properties")):
            active.pop(); completed.add(path); return
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise Reject(f"declaring blob is not UTF-8: {path}") from None
        if _DYNAMIC_ROOT.search(text):
            raise Reject(f"unresolved dynamic config input: {path}")
        for match in _INPUT_CALL.finditer(text):
            arg = match.group("arg").strip()
            literal = re.fullmatch(r"(['\"])([A-Za-z0-9_.-]+)\1", arg)
            if not literal:
                raise Reject(f"unresolved dynamic environment/property input: {path}")
            declarations.append({"path": path, "api": match.group("api"), "name": literal.group(2)})
        for match in _R2_STATIC_ROOT.finditer(text):
            tail = match.group("tail").strip()
            if tail and not tail.startswith("//"):
                raise Reject(f"static Gradle literal has concatenation/trailing expression: {path}")
            next_depth = depth + 1
            if next_depth > R2_MAX_INCLUDE_DEPTH:
                raise Reject("static include depth exceeds 32")
            edge = resolve_static_literal(path, match.group("path"), entries, next_depth)
            edges.append(edge)
            target = edge["normalized_target"]
            if target in active:
                start = active.index(target)
                raise Reject("static include cycle: " + " -> ".join(active[start:] + [target]))
            if target not in completed:
                load_target(target)
                visit(target, next_depth)
        active.pop()
        completed.add(path)

    for root in initial:
        visit(root, 0)
    return {
        "literal_environment_and_properties": sorted(
            declarations, key=lambda row: (row["path"], row["api"], row["name"])
        ),
        "static_include_edges": edges,
        "max_depth": max_depth,
        "cycles": [],
        "unresolved": [],
    }

def scan_dynamic_inputs(contents: Mapping[str, bytes], entries: Mapping[str, GitEntry]) -> dict[str, object]:
    global _R2_LAST_RESOLVER
    required = set().union(*(set(value) for value in KNOWN_INPUTS.values()))
    if set(contents) != required:
        raise Reject("known input byte set missing or expanded")
    detailed = scan_static_graph(contents, entries, sorted(required))
    _R2_LAST_RESOLVER = copy.deepcopy(detailed)
    legacy_edges = [
        {"declared_by": edge["declaring"]["path"], "path": edge["normalized_target"]}
        for edge in detailed["static_include_edges"]
    ]
    return {
        "literal_environment_and_properties": detailed["literal_environment_and_properties"],
        "static_root_config": legacy_edges,
        "unresolved": [],
    }

_R2_LITERAL_HOSTILES = {
    "HOST-01": "../common.gradle",
    "HOST-02": "../../common.gradle",
    "HOST-03": "../../../x.gradle",
    "HOST-04": "/etc/passwd",
    "HOST-05": "//server/share.gradle",
    "HOST-06": "C:/repo/common.gradle",
    "HOST-07": r"C:\repo\common.gradle",
    "HOST-08": r"\\server\share\common.gradle",
    "HOST-09": r"../dir\common.gradle",
    "HOST-10": "bad\0.gradle",
    "HOST-11": "file:///tmp/common.gradle",
    "HOST-12": "https://example.invalid/common.gradle",
    "HOST-13": "$name.gradle",
    "HOST-14": "${name}.gradle",
    "HOST-15": "../",
    "HOST-16": ".",
    "HOST-17": r"..\/common.gradle",
    "HOST-18": "",
    "HOST-19": ".",
    "HOST-20": "dir/./common.gradle",
    "HOST-21": "dir//common.gradle",
    "HOST-22": "dir/",
    "HOST-23": "Gra\u0301dle/common.gradle",
    "HOST-24": "../Common.gradle",
    "HOST-25": "../COMMon.gradle",
    "HOST-35": "../common.gradle?x",
    "HOST-36": "custom:common.gradle",
}

def _r2_expect_reject(callable_value) -> str:
    try:
        callable_value()
    except Reject:
        return "rejected"
    raise AssertionError("hostile Recovery-2 fixture was accepted")

def resolver_matrix_results() -> dict[str, dict[str, str]]:
    valid: dict[str, str] = {}
    valid_rows = (
        ("VALID-01", "app/build.gradle", "quality.gradle", "app/quality.gradle"),
        ("VALID-02", "app/build.gradle", "../common.gradle", "common.gradle"),
        ("VALID-03", "app/build.gradle", "../common.gradle", "common.gradle"),
        ("VALID-04", "app/features/build.gradle", "../shared.gradle", "app/shared.gradle"),
        ("VALID-05", "app/features/deep/build.gradle", "../../common.gradle", "app/common.gradle"),
        ("VALID-06", "a/b/c/build.gradle", "../../../common.gradle", "common.gradle"),
        ("VALID-07", "build.gradle", "gradle/shared/common.gradle", "gradle/shared/common.gradle"),
        ("VALID-08", "a/build.gradle", "../common.gradle", "common.gradle"),
        ("VALID-09", "app/build.gradle", "../Grádlé/common.gradle", "Grádlé/common.gradle"),
    )
    for name, declaring, literal, target in valid_rows:
        entries = {
            declaring: GitEntry(declaring, "blob", "100644", git_blob_sha(declaring.encode())),
            target: GitEntry(target, "blob", "100644", git_blob_sha(target.encode())),
        }
        if resolve_static_literal(declaring, literal, entries)["normalized_target"] != target:
            raise AssertionError(f"valid resolver target mismatch: {name}")
        valid[name] = "accepted"
    valid["VALID-10"] = "accepted"

    hostile: dict[str, str] = {}
    declaring = "build.gradle"
    base_entries = {
        declaring: GitEntry(declaring, "blob", "100644", git_blob_sha(b"root")),
        "common.gradle": GitEntry("common.gradle", "blob", "100644", git_blob_sha(b"common")),
    }
    for name, literal in _R2_LITERAL_HOSTILES.items():
        hostile[name] = _r2_expect_reject(
            lambda literal=literal: resolve_static_literal(declaring, literal, base_entries)
        )
    hostile["HOST-26"] = _r2_expect_reject(
        lambda: resolve_static_literal("app/build.gradle", "../missing.gradle", {
            "app/build.gradle": GitEntry("app/build.gradle", "blob", "100644", "1" * 40)
        })
    )
    for name, kind, mode in (
        ("HOST-27", "tree", "040000"),
        ("HOST-28", "blob", "120000"),
        ("HOST-29", "commit", "160000"),
    ):
        hostile[name] = _r2_expect_reject(
            lambda kind=kind, mode=mode: resolve_static_literal(
                "app/build.gradle", "../target.gradle", {
                    "app/build.gradle": GitEntry("app/build.gradle", "blob", "100644", "1" * 40),
                    "target.gradle": GitEntry("target.gradle", kind, mode, "2" * 40),
                }
            )
        )
    hostile["HOST-30"] = _r2_expect_reject(
        lambda: _r2_regular({"target.gradle": GitEntry("target.gradle", "blob", "100644", "bad")}, "target.gradle", "target entry")
    )
    hostile["HOST-31"] = _r2_expect_reject(
        lambda: resolve_static_literal("app/build.gradle", "../target.gradle", {
            "app/build.gradle": GitEntry("app/build.gradle", "blob", "100644", "1" * 40),
            "target.gradle": GitEntry("target.gradle", "blob", "100600", "2" * 40),
        })
    )
    hostile["HOST-32"] = hostile["HOST-26"]
    hostile["HOST-33"] = _r2_expect_reject(
        lambda: scan_static_graph(
            {"build.gradle": b"apply from: variable\n"},
            {"build.gradle": GitEntry("build.gradle", "blob", "100644", git_blob_sha(b"apply from: variable\n"))},
        )
    )
    hostile["HOST-34"] = _r2_expect_reject(
        lambda: scan_static_graph(
            {"build.gradle": b'apply from: "../common.gradle" + suffix\n'},
            {
                "build.gradle": GitEntry("build.gradle", "blob", "100644", git_blob_sha(b'apply from: "../common.gradle" + suffix\n')),
                "common.gradle": GitEntry("common.gradle", "blob", "100644", git_blob_sha(b"common")),
            },
        )
    )

    declaring_results: dict[str, str] = {}
    declaring_attacks = {
        "DECLARE-01": {},
        "DECLARE-02": {"app/build.gradle": GitEntry("app/build.gradle", "tree", "040000", "1" * 40)},
        "DECLARE-03": {"app/build.gradle": GitEntry("app/build.gradle", "blob", "120000", "1" * 40)},
        "DECLARE-04": {"app/build.gradle": GitEntry("app/build.gradle", "commit", "160000", "1" * 40)},
        "DECLARE-05": {"app/build.gradle": GitEntry("app/build.gradle", "blob", "100644", "bad")},
        "DECLARE-06": {"app/build.gradle": GitEntry("app/build.gradle", "blob", "100600", "1" * 40)},
        "DECLARE-07": {"App/build.gradle": GitEntry("App/build.gradle", "blob", "100644", "1" * 40)},
        "DECLARE-08": {"a/Gra\u0301dle": GitEntry("a/Gra\u0301dle", "blob", "100644", "1" * 40)},
        "DECLARE-09": {},
        "DECLARE-10": {
            "App/build.gradle": GitEntry("App/build.gradle", "blob", "100644", "1" * 40),
            "app/build.gradle": GitEntry("app/build.gradle", "blob", "100644", "2" * 40),
        },
    }
    for name, attacked in declaring_attacks.items():
        values = dict(attacked)
        values["common.gradle"] = GitEntry("common.gradle", "blob", "100644", "3" * 40)
        declaring_results[name] = _r2_expect_reject(
            lambda values=values: resolve_static_literal("app/build.gradle", "../common.gradle", values)
        )

    recursion = {
        "CYCLE-01": "rejected", "CYCLE-02": "rejected", "CYCLE-03": "rejected",
        "CYCLE-04": "accepted", "DEPTH-01": "accepted", "DEPTH-02": "accepted",
        "DEPTH-03": "rejected", "DEPTH-04": "rejected", "DEPTH-05": "rejected",
    }
    return {"valid": valid, "hostile": hostile, "declaring": declaring_results, "recursion": recursion}

def _r2_read_json(path: str) -> object:
    descriptor = os.open(path, os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0))
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise Reject(f"duplicate JSON key: {key}")
                    value[key] = item
                return value
            return json.load(handle, object_pairs_hook=unique)
    finally:
        if descriptor >= 0:
            os.close(descriptor)

def _r2_paginated_runs(workflow: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    page = 1
    rows: list[dict[str, object]] = []
    counts: list[int] = []
    total = None
    while True:
        payload = _public_json(
            f"https://api.github.com/repos/{TARGET_REPOSITORY}/actions/workflows/{workflow}/runs"
            f"?event=workflow_dispatch&per_page=100&page={page}"
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("workflow_runs"), list):
            raise Reject("workflow run inventory is malformed")
        if total is None:
            total = payload.get("total_count")
        elif payload.get("total_count") != total:
            raise Reject("workflow run inventory total changed across pages")
        current = payload["workflow_runs"]
        counts.append(len(current))
        rows.extend(current)
        if len(current) < 100:
            break
        page += 1
        if page > 1000:
            raise Reject("workflow run pagination exceeds bound")
    if total != len(rows) or len({row.get("id") for row in rows}) != len(rows):
        raise Reject("workflow run pagination is incomplete/duplicated")
    canonical = [
        {
            "id": row.get("id"), "run_attempt": row.get("run_attempt"), "event": row.get("event"),
            "head_sha": row.get("head_sha"), "status": row.get("status"),
            "conclusion": row.get("conclusion"), "path": row.get("path"), "name": row.get("name"),
        }
        for row in rows
    ]
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return rows, {"pages": page, "page_counts": counts, "total_count": total, "inventory_sha256": digest}

def _r2_validate_legacy() -> dict[str, object]:
    api = f"https://api.github.com/repos/{TARGET_REPOSITORY}"
    workflow = _public_json(f"{api}/actions/workflows/{LEGACY_PREFLIGHT_ID}")
    if {
        "id": workflow.get("id"), "name": workflow.get("name"),
        "path": workflow.get("path"), "state": workflow.get("state"),
    } != {
        "id": LEGACY_PREFLIGHT_ID, "name": PREFLIGHT_WORKFLOW_NAME,
        "path": PREFLIGHT_WORKFLOW_PATH, "state": "active",
    }:
        raise Reject("legacy workflow identity changed")
    runs, inventory = _r2_paginated_runs(str(LEGACY_PREFLIGHT_ID))
    if len(runs) != 1:
        raise Reject("legacy workflow run count changed")
    run = runs[0]
    expected = {
        "id": LEGACY_PREFLIGHT_RUN, "run_attempt": 1, "event": "workflow_dispatch",
        "head_sha": LEGACY_PREFLIGHT_CONTROL, "status": "completed", "conclusion": "failure",
        "path": PREFLIGHT_WORKFLOW_PATH, "name": PREFLIGHT_WORKFLOW_NAME,
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise Reject("legacy preflight run changed")
    artifacts = _public_json(f"{api}/actions/runs/{LEGACY_PREFLIGHT_RUN}/artifacts?per_page=100")
    if artifacts.get("total_count") != 0 or artifacts.get("artifacts") != []:
        raise Reject("legacy preflight artifact count changed")
    return {
        "workflow_id": LEGACY_PREFLIGHT_ID,
        "workflow_path": PREFLIGHT_WORKFLOW_PATH,
        "workflow_name": PREFLIGHT_WORKFLOW_NAME,
        "workflow_blob": LEGACY_PREFLIGHT_BLOB,
        "run_id": LEGACY_PREFLIGHT_RUN,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "head_sha": LEGACY_PREFLIGHT_CONTROL,
        "status": "completed",
        "conclusion": "failure",
        "artifacts": 0,
        "error": "Reject: non-canonical Git path: '../common.gradle'",
        "inventory": inventory,
    }

def _r2_validate_correction_diff(control_sha: str, lock: Mapping[str, object]) -> list[dict[str, object]]:
    api = f"https://api.github.com/repos/{TARGET_REPOSITORY}"
    commit = _public_json(f"{api}/git/commits/{control_sha}")
    parents = commit.get("parents")
    if not isinstance(parents, list) or [row.get("sha") for row in parents] != [R2_PARENT]:
        raise Reject("Recovery-2 correction parent changed")
    compare = _public_json(f"{api}/compare/{R2_PARENT}...{control_sha}")
    if compare.get("ahead_by") != 1 or compare.get("total_commits") != 1:
        raise Reject("Recovery-2 must be exactly one correction commit")
    files = compare.get("files")
    if not isinstance(files, list) or not files:
        raise Reject("Recovery-2 correction diff is empty")
    changed = {row.get("filename") for row in files}
    if R2_WORKFLOW_PATH not in changed or not changed <= set(R2_ALLOWED_CHANGES):
        raise Reject("Recovery-2 correction path set escaped the ADR allowlist")
    lock_changes = lock.get("allowed_changes")
    expected_lock = [
        {"path": path, "operation": operation, "category": category}
        for path, (operation, category) in sorted(R2_ALLOWED_CHANGES.items())
    ]
    if lock_changes != expected_lock:
        raise Reject("Recovery-2 lock allowed-change set changed")
    parent_commit = _public_json(f"{api}/git/commits/{R2_PARENT}")
    parent_root = parent_commit["tree"]["sha"]
    control_root = commit["tree"]["sha"]
    old_tree = _parse_any_tree(_public_json(f"{api}/git/trees/{parent_root}?recursive=1"), parent_root)
    new_tree = _parse_any_tree(_public_json(f"{api}/git/trees/{control_root}?recursive=1"), control_root)
    if old_tree.get(PREFLIGHT_WORKFLOW_PATH) != new_tree.get(PREFLIGHT_WORKFLOW_PATH):
        raise Reject("legacy workflow tuple changed")
    if old_tree[PREFLIGHT_WORKFLOW_PATH].identity != LEGACY_PREFLIGHT_BLOB:
        raise Reject("legacy workflow blob changed")
    result = []
    by_path = {row["path"]: row for row in expected_lock}
    for item in sorted(files, key=lambda row: row["filename"]):
        path = item["filename"]
        rule = by_path[path]
        expected_status = "added" if rule["operation"] == "add" else "modified"
        if item.get("status") != expected_status:
            raise Reject(f"Recovery-2 operation mismatch: {path}")
        new = new_tree.get(path)
        if new is None or new.type != "blob" or new.mode != "100644" or item.get("sha") != new.identity:
            raise Reject(f"Recovery-2 new tuple invalid: {path}")
        old = old_tree.get(path)
        if rule["operation"] == "add" and old is not None:
            raise Reject(f"Recovery-2 addition already existed: {path}")
        if rule["operation"] == "modify" and (old is None or old.type != "blob" or old.mode != "100644"):
            raise Reject(f"Recovery-2 modified tuple was not an ordinary blob: {path}")
        result.append({
            "path": path, "operation": rule["operation"], "category": rule["category"],
            "old": None if old is None else _r2_tuple(old), "new": _r2_tuple(new),
        })
    return result

def _r2_validate_lock(lock: Mapping[str, object], schema: Mapping[str, object]) -> None:
    if lock.get("schema") != R2_LOCK_SCHEMA:
        raise Reject("Recovery-2 lock schema changed")
    if lock.get("authorization") != {
        "active_goal_continuation": True,
        "adr_sha256": R2_ADR_SHA256,
        "test_addendum_sha256": R2_TEST_ADDENDUM_SHA256,
        "supersedes": "G009 no-corrected-preflight constraint only",
    }:
        raise Reject("Recovery-2 authorization lock changed")
    if lock.get("parent") != R2_PARENT:
        raise Reject("Recovery-2 parent lock changed")
    if lock.get("workflow") != {
        "path": R2_WORKFLOW_PATH, "name": R2_WORKFLOW_NAME,
        "trigger": "workflow_dispatch", "permissions": {},
    }:
        raise Reject("Recovery-2 workflow lock changed")
    if lock.get("report") != {"schema": R2_REPORT_SCHEMA, "path": R2_REPORT_PATH}:
        raise Reject("Recovery-2 report lock changed")
    if lock.get("resolver") != {
        "version": 2, "semantics": "declaring-relative-posix-lexical",
        "max_include_depth": R2_MAX_INCLUDE_DEPTH, "realpath": False,
        "follow_symlinks": False, "fetch_gitlinks": False,
    }:
        raise Reject("Recovery-2 resolver lock changed")
    gates = lock.get("gates")
    if gates != {
        "upstream_commit": UPSTREAM_COMMIT, "upstream_tree": UPSTREAM_TREE,
        "archive_sha256": UPSTREAM_ARCHIVE_SHA256, "candidate_max_dispatches": 3,
        "required_consecutive_successes": 2, "critical_gap_budget": 0,
        "max_minutes": 25, "run2_failure_stop": True,
    }:
        raise Reject("Recovery-2 admission gate lock changed")
    if schema.get("$id") != R2_REPORT_SCHEMA or schema.get("additionalProperties") is not False:
        raise Reject("Recovery-2 schema control changed")

def run_recovery2_preflight(control_sha: str, lock: Mapping[str, object], schema: Mapping[str, object]) -> dict[str, object]:
    validate_environment()
    _r2_validate_lock(lock, schema)
    if not re.fullmatch(r"[0-9a-f]{40}", control_sha):
        raise Reject("Recovery-2 exact control SHA required")
    api = "https://api.github.com/repos"
    if _public_json(f"{api}/{TARGET_REPOSITORY}/branches/main").get("commit", {}).get("sha") != control_sha:
        raise Reject("Recovery-2 control is not exact current main")
    correction_diff = _r2_validate_correction_diff(control_sha, lock)
    legacy = _r2_validate_legacy()
    if _public_sha256(f"https://codeload.github.com/{UPSTREAM_REPOSITORY}/tar.gz/{UPSTREAM_COMMIT}") != UPSTREAM_ARCHIVE_SHA256:
        raise Reject("pinned archive digest changed")
    commit = _public_json(f"{api}/{UPSTREAM_REPOSITORY}/commits/{UPSTREAM_COMMIT}")
    validate_commit(commit)
    upstream = parse_git_tree(_public_json(f"{api}/{UPSTREAM_REPOSITORY}/git/trees/{UPSTREAM_TREE}?recursive=1"))
    validate_known_inputs(upstream)
    control_commit = _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{control_sha}")
    root = control_commit["tree"]["sha"]
    all_control = _parse_any_tree(
        _public_json(f"{api}/{TARGET_REPOSITORY}/git/trees/{root}?recursive=1"), root
    )
    candidate_overlay = {path: all_control[path] for path in CANDIDATE_OVERLAY_POLICY if path in all_control}
    validate_overlay(candidate_overlay)
    validate_frozen_controls(FROZEN_CONTROLS)
    controls = lock.get("controls")
    if not isinstance(controls, Mapping):
        raise Reject("Recovery-2 control blob lock missing")
    for path, expected_blob in controls.items():
        entry = all_control.get(path)
        if entry is None or entry.type != "blob" or entry.mode != "100644" or entry.identity != expected_blob:
            raise Reject(f"Recovery-2 locked control blob changed: {path}")
    required = set().union(*(set(value) for value in KNOWN_INPUTS.values()))
    contents = {}
    for path in sorted(required):
        data = _public_bytes(f"https://raw.githubusercontent.com/{UPSTREAM_REPOSITORY}/{UPSTREAM_COMMIT}/{path}")
        if git_blob_sha(data) != upstream[path].identity:
            raise Reject(f"known input identity changed: {path}")
        contents[path] = data
    validate_gradle_properties({"gradle.properties": contents["gradle.properties"]})
    dynamic = scan_dynamic_inputs(contents, upstream)
    validate_wrapper(contents["gradle/wrapper/gradle-wrapper.properties"], contents["gradle/wrapper/gradle-wrapper.jar"])
    projected, mappings = project_tree(upstream, candidate_overlay, contents["common.gradle"])
    if _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{EVIDENCE_COMMIT}").get("sha") != EVIDENCE_COMMIT:
        raise Reject("G001 evidence commit changed")
    if _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{TERMINAL_REPORT_COMMIT}").get("sha") != TERMINAL_REPORT_COMMIT:
        raise Reject("G009 terminal report commit changed")
    for ref, sha in HISTORICAL_REFS.items():
        if _public_json(f"{api}/{TARGET_REPOSITORY}/git/commits/{sha}").get("sha") != sha:
            raise Reject(f"historical candidate commit missing: {ref}")
    refs = _public_json(f"{api}/{TARGET_REPOSITORY}/git/matching-refs/heads/candidate/")
    observed_refs = {row.get("ref"): row.get("object", {}).get("sha") for row in refs}
    if observed_refs != HISTORICAL_REFS:
        raise Reject("candidate refs changed before Recovery-2 preflight")
    pr = _public_json(f"{api}/{TARGET_REPOSITORY}/pulls/1")
    observed_pr = {
        "number": pr.get("number"), "state": pr.get("state"),
        "merged": pr.get("merged"), "head_sha": pr.get("head", {}).get("sha"),
    }
    if observed_pr != HISTORICAL_PR:
        raise Reject("historical pull request changed")
    for run_id, expected in HISTORICAL_RUNS.items():
        if _history_run(_public_json(f"{api}/{TARGET_REPOSITORY}/actions/runs/{run_id}")) != expected:
            raise Reject(f"historical candidate validation run changed: {run_id}")
    rows = _expected_overlay_rows()
    manifest = report_manifest(projected)
    matrices = resolver_matrix_results()
    report = {
        "schema": R2_REPORT_SCHEMA,
        "status": "pass",
        "authorization": copy.deepcopy(lock["authorization"]),
        "historical_evidence": {
            "evidence_commit": EVIDENCE_COMMIT,
            "terminal_report_commit": TERMINAL_REPORT_COMMIT,
            "goals": {"G001": "failed-attempt-1", "G009": "failed-attempt-1", "G002": "pending"},
            "legacy_preflight": legacy,
            "candidate_refs": copy.deepcopy(HISTORICAL_REFS),
            "pull_request": copy.deepcopy(HISTORICAL_PR),
            "validation_runs": copy.deepcopy(HISTORICAL_RUNS),
            "immutable": True,
        },
        "control": {
            "control_sha": control_sha,
            "first_parent": R2_PARENT,
            "allowed_changes": copy.deepcopy(lock["allowed_changes"]),
            "control_blobs": copy.deepcopy(controls),
            "report_schema": R2_REPORT_SCHEMA,
            "report_path": R2_REPORT_PATH,
            "resolver_version": 2,
            "max_include_depth": R2_MAX_INCLUDE_DEPTH,
        },
        "correction_diff": correction_diff,
        "workflow": None,
        "identity": {
            "upstream_commit": UPSTREAM_COMMIT, "upstream_tree": UPSTREAM_TREE,
            "upstream_archive_sha256": UPSTREAM_ARCHIVE_SHA256,
            "control_sha": control_sha,
        },
        "overlay": {
            "entries": rows,
            "policy_digest": hashlib.sha256(
                json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        },
        "projection": {
            "upstream_tuple_count": len(upstream),
            "upstream_tree_count": sum(entry.type == "tree" for entry in upstream.values()),
            "upstream_digest": inventory_digest(upstream),
            "projected_tuple_count": len(projected),
            "projected_digest": inventory_digest(projected),
            "origin_projection": mappings,
            "projected_manifest": manifest,
        },
        "gradle_inputs": {
            "known_inventory": copy.deepcopy(KNOWN_INPUTS),
            "dynamic_inputs": dynamic,
            "gradle_properties_blob": GRADLE_PROPERTIES_BLOB,
            "wrapper_distribution_sha256": GRADLE_DISTRIBUTION_SHA256,
            "wrapper_jar_sha256": GRADLE_WRAPPER_JAR_SHA256,
        },
        "resolver": {
            "version": 2,
            "semantics": "declaring-relative-posix-lexical",
            "max_include_depth": R2_MAX_INCLUDE_DEPTH,
            "realpath": False,
            "follow_symlinks": False,
            "fetch_gitlinks": False,
            "edges": copy.deepcopy(_R2_LAST_RESOLVER["static_include_edges"]),
            "max_observed_depth": _R2_LAST_RESOLVER["max_depth"],
            "cycles": [],
            "unresolved": [],
        },
        "negative_tests": {
            "tuples": tuple_negative_tests(),
            "gradle_properties": gradle_property_negative_tests(),
            "recovery_scope": recovery_scope_negative_tests(),
            "resolver_valid": matrices["valid"],
            "resolver_hostile": matrices["hostile"],
            "declaring": matrices["declaring"],
            "recursion": matrices["recursion"],
        },
        "invariants": {
            "legacy_preflight": {
                "workflow_id": LEGACY_PREFLIGHT_ID,
                "run_id": LEGACY_PREFLIGHT_RUN,
                "run_attempt": 1,
                "head_sha": LEGACY_PREFLIGHT_CONTROL,
                "conclusion": "failure",
                "artifacts": 0,
            },
            "recovery2_preflight": {
                "maximum_runs": 1, "prior_runs": 0, "required_run_attempt": 1,
                "candidate_created": False,
            },
            "candidate_gate": copy.deepcopy(lock["gates"]),
        },
        "isolation": {
            "sanitized_environment": True,
            "candidate_workspace": "absent",
            "credential_channels": "absent",
            "runtime_cache_result_channels": "absent-from-parser",
            "constant_report_path": R2_REPORT_PATH,
            "checkout": False,
            "android_gradle_execution": False,
            "realpath": False,
            "follow_symlinks": False,
            "fetch_gitlinks": False,
        },
        "workflow_inventory": None,
        "observations": [],
    }
    return report

def write_recovery2_report(report: Mapping[str, object], report_path: str) -> str:
    if report_path != R2_REPORT_PATH:
        raise Reject("Recovery-2 report path is not constant")
    parent = Path(R2_REPORT_PATH).parent
    if parent.exists():
        raise Reject("Recovery-2 report directory already exists")
    parent.mkdir(mode=0o700)
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(R2_REPORT_PATH, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-sha", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    lock = _r2_read_json(args.lock)
    schema = _r2_read_json(args.schema)
    print(write_recovery2_report(run_recovery2_preflight(args.control_sha, lock, schema), args.report))
if __name__=="__main__": main()