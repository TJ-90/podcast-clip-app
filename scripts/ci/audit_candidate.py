#!/usr/bin/env python3
"""Trusted, deterministic Story 1 provenance/capability prerequisite audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EXPECTED = {
    "podaura": {
        "commit": "9c154cbba2936725e1aef4a09a8f82be49ccb9a0",
        "tree": "59b4ac49f35e2314ddcb40ca8f6a0358e4924024",
        "required": {
            "rss_subscription_refresh": [
                "shared/src/commonMain/kotlin/com/skyd/podaura/model/db/dao/RssModuleDao.kt",
                "platform/android/app/src/main/java/com/skyd/podaura/model/worker/rsssync/RssSyncWorker.kt",
            ],
            "playback_media_session": [
                "platform/android/app/src/main/java/com/skyd/podaura/ui/player/service/MediaSessionManager.kt",
                "platform/android/app/src/main/java/com/skyd/podaura/ui/player/service/PlayerService.kt",
            ],
            "complete_download_offline": [
                "downloader/src/commonMain/kotlin/com/skyd/downloader/db/DownloadEntity.kt",
                "downloader/src/androidMain/kotlin/com/skyd/downloader/download/DownloadWorker.kt",
            ],
        },
        # Repository mapping proved these critical admission capabilities absent.
        "known_critical_gaps": [
            "persistent conventional Up Next queue semantics",
            "queue/current-position restoration after process death",
        ],
    },
    "antennapod": {
        "commit": "1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7",
        "tree": "ebfc8990216aded7ad4ab6d393fa6e0131a69fee",
        "required": {
            "rss_subscription_refresh": [
                "parser/feed/src/main/java/de/danoeh/antennapod/parser/feed/FeedHandler.java",
                "net/download/service/src/main/java/de/danoeh/antennapod/net/download/service/feed/FeedUpdateWorker.java",
            ],
            "playback_media_session": [
                "playback/service/src/main",
                "app/src/androidTest/java/de/test/antennapod/service/playback/PlaybackServiceMediaPlayerTest.java",
            ],
            "persistent_queue": [
                "app/src/main/java/de/danoeh/antennapod/ui/screen/queue/QueueFragment.java",
                "app/src/androidTest/java/de/test/antennapod/ui/QueueFragmentTest.java",
            ],
            "complete_download_offline": [
                "net/download/service/src/main/java/de/danoeh/antennapod/net/download/service/episode/EpisodeDownloadWorker.java",
                "app/src/main/java/de/danoeh/antennapod/ui/screen/download/CompletedDownloadsFragment.java",
            ],
            "process_restoration": [
                "storage/database/src/main",
                "storage/preferences/src/main",
            ],
        },
        "known_critical_gaps": [],
    },
}

TRUSTED_WORKFLOWS = {"import-upstream.yml", "validate-candidate.yml"}


def exists(root: Path, rel: str) -> bool:
    path = root / rel
    return path.is_dir() or path.is_file()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=sorted(EXPECTED), required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    expected = EXPECTED[args.candidate]
    lock = json.loads((root / "provenance/import-lock.json").read_text(encoding="utf-8"))
    identity_ok = (
        lock.get("candidate") == args.candidate
        and lock.get("upstream_commit") == expected["commit"]
        and lock.get("upstream_tree") == expected["tree"]
        and lock.get("archive_entry_count", 0) > 0
        and len(lock.get("observed_archive_sha256", "")) == 64
    )
    design_text = (root / "DESIGN.md").read_text(encoding="utf-8", errors="replace")
    design_ok = all(
        anchor in design_text
        for anchor in ("Product character", "Navigation and information architecture", "Player and clipping", "Accessibility", "Adaptive layout")
    )
    license_text = (root / "LICENSE").read_text(encoding="utf-8", errors="replace")
    license_ok = "GNU GENERAL PUBLIC LICENSE" in license_text and "Version 3" in license_text
    active_workflows = {
        path.name for path in (root / ".github/workflows").glob("*.yml") if path.is_file()
    }
    workflow_quarantine_ok = active_workflows == TRUSTED_WORKFLOWS
    capabilities = {
        name: all(exists(root, path) for path in paths)
        for name, paths in expected["required"].items()
    }
    gaps = list(expected["known_critical_gaps"])
    for name, passed in capabilities.items():
        if not passed:
            gaps.append(f"missing mapped prerequisite: {name}")
    admitted = identity_ok and design_ok and license_ok and workflow_quarantine_ok and not gaps
    report = {
        "schema": 1,
        "candidate": args.candidate,
        "identity": {
            "commit": lock.get("upstream_commit"),
            "tree": lock.get("upstream_tree"),
            "archive_sha256": lock.get("observed_archive_sha256"),
            "ok": identity_ok,
        },
        "design_bootstrap": design_ok,
        "gpl_v3": license_ok,
        "trusted_workflow_allowlist": workflow_quarantine_ok,
        "capability_prerequisites": capabilities,
        "critical_gaps": gaps,
        "admission_prerequisite_result": "pass" if admitted else "reject",
        "note": "Static/source and existing-test prerequisite audit; qualifying acceptance also requires the workflow's clean build/unit/lint/launch evidence twice at identical identity.",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if admitted else 1


if __name__ == "__main__":
    sys.exit(main())
