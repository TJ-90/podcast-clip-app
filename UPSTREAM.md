# Upstream provenance and base-selection status

This repository is a public GPL-3.0 project. Imported candidates are source snapshots; the repository does not claim to preserve upstream Git history.

Current selection status: **RECOVERY_PREFLIGHT_FAILED — no base admitted**.

## Rejected primary candidate: PodAura

- Repository: https://github.com/SkyD666/PodAura
- Pinned commit: `9c154cbba2936725e1aef4a09a8f82be49ccb9a0`
- GitHub-reported tree: `59b4ac49f35e2314ddcb40ca8f6a0358e4924024`
- License: GPL-3.0
- Reason: missing zero-budget critical capabilities, including a persistent conventional queue and process-death playback/queue restoration. MediaSession queue work was incomplete and Discover search was local-only. These gaps were not eligible for viability-overlay repair.

## Unadmitted fallback candidate: AntennaPod

- Repository: https://github.com/AntennaPod/AntennaPod
- Pinned commit: `1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7`
- GitHub-reported tree: `ebfc8990216aded7ad4ab6d393fa6e0131a69fee`
- Observed archive SHA-256: `99c9d77996595d6d75ed170240d5849ce381931f6d5e726d12e198ff15dae8a2`
- Preserved candidate commit: `c58e2607c57925486b856416e1b3f9044673e2be`
- Preserved candidate branch: `candidate/antennapod-1d2bd1c8f9d3-r29562160851`
- Review: https://github.com/TJ-90/podcast-clip-app/pull/1 (closed, not merged)
- License: GPL-3.0
- Result: not admitted. Counted dispatches 1 and 2 failed because the trusted validation environment incompletely reproduced the quarantined upstream Gradle properties. One dispatch remains, which cannot produce the required two consecutive successes.

The exact run ledger, security boundary, and stop rationale are recorded in [`docs/base-selection-report.md`](docs/base-selection-report.md). Do not merge or build product work on the preserved candidate unless a new RALPLAN decision explicitly reopens the gate.

## One-time recovery result

The independently reviewed recovery controls were frozen at [fc0ed383c0f4e1cf527f88d0ac3033973a379a4e](https://github.com/TJ-90/podcast-clip-app/commit/fc0ed383c0f4e1cf527f88d0ac3033973a379a4e). The permissions-empty preflight was dispatched exactly once as [run 29575201182](https://github.com/TJ-90/podcast-clip-app/actions/runs/29575201182), attempt 1. Its immutable identity guard, no-checkout control fetch, and 11 stdlib tests passed. The sanitized parser rejected the unresolved relative static input '../common.gradle', and the report validator/uploader were skipped.

This failure is terminal under the approved one-preflight contract. There was no rerun, no second preflight, no fresh candidate identity, no candidate PR, and no fresh validation dispatch. The two historical candidate branches and closed PR #1 remain evidence only. AntennaPod is not admitted; do not begin Story 2.

No Android/source archive, Gradle distribution, SDK, dependency, candidate content, CI artifact, or APK was downloaded to the operator device. Only GitHub API metadata and the failed job log were inspected.
