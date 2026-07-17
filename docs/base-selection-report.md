# Story 1 base-selection report

Status: **RECOVERY_PREFLIGHT_FAILED**  
Recorded: 2026-07-17 UTC  
Repository: https://github.com/TJ-90/podcast-clip-app

## Verdict

No podcast base is admitted. Do not merge the AntennaPod candidate and do not spend the final dispatch under the current plan.

The approved gate requires two consecutive successful clean runs at one exact candidate identity within three counted dispatches. AntennaPod dispatches 1 and 2 both failed. Even if dispatch 3 succeeded, a second consecutive success would require a prohibited fourth dispatch. The gate is therefore mathematically unsatisfiable without a reviewed plan change.

## PodAura rejection

| Field | Evidence |
| --- | --- |
| Upstream | `SkyD666/PodAura` |
| Pinned commit | `9c154cbba2936725e1aef4a09a8f82be49ccb9a0` |
| GitHub tree | `59b4ac49f35e2314ddcb40ca8f6a0358e4924024` |
| Verdict | Rejected before product investment |

Repository mapping found zero-budget critical gaps: no dedicated persistent conventional Up Next queue, MediaSession queue handling remained TODO, playback/queue process restoration was absent (`START_NOT_STICKY` and an in-memory player list), and Discover search was local-only. These are missing engine behaviors, not a permissible minor presentation/adapter gap. They were not repaired in the viability overlay.

## AntennaPod candidate identity

| Field | Evidence |
| --- | --- |
| Upstream | `AntennaPod/AntennaPod` |
| Pinned commit | `1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7` |
| GitHub tree | `ebfc8990216aded7ad4ab6d393fa6e0131a69fee` |
| Observed archive SHA-256 | `99c9d77996595d6d75ed170240d5849ce381931f6d5e726d12e198ff15dae8a2` |
| Trusted bootstrap overlay | `58d007bb4bf495f035263da5a869849708486336` |
| Candidate commit | `c58e2607c57925486b856416e1b3f9044673e2be` |
| Preserved branch | `candidate/antennapod-1d2bd1c8f9d3-r29562160851` |
| Review PR | [#1](https://github.com/TJ-90/podcast-clip-app/pull/1) — closed, not merged |

The trusted importer verified GitHub commit/tree metadata and every regular archive blob, recorded the observed archive digest, kept GPL provenance, and quarantined 28 upstream control/link entries. Only the two repository-owned workflows remained active. Three reviewed symlink identities and the optional StoreMetadata gitlink were recorded but never materialized or fetched. Candidate content did not execute in the write-token import job.

## Dispatch ledger

| Budget event | Run | Result | Classification |
| --- | --- | --- | --- |
| Dispatch 1 | [29562294514](https://github.com/TJ-90/podcast-clip-app/actions/runs/29562294514) | Identity, provenance, quarantine, design ancestry, and capability prerequisite audit passed. Android task configuration failed because the trusted import/control path omitted upstream `android.useAndroidX=true` and `android.nonTransitiveRClass=false`. | Counted failure; exposed the single permitted environment/task overlay correction. |
| Dispatch 2 | [29562814924](https://github.com/TJ-90/podcast-clip-app/actions/runs/29562814924) | Identity/capability audit passed and clean assembly advanced through extensive compilation. Gradle stopped for GC thrashing with a 512 MiB heap because the same omitted upstream control file also specified `org.gradle.jvmargs=-Xmx4096m`. | Counted failure; the reviewed correction was incomplete. |
| Accidental duplicate | [29563023789](https://github.com/TJ-90/podcast-clip-app/actions/runs/29563023789) | Cancelled; no qualifying conclusion. | Not evidence and not a replacement for a counted run. |
| Dispatch 3 | Not dispatched | A single possible success cannot establish two consecutive successes. | Preserved; spending it cannot satisfy the approved gate. |

Two duplicate trusted-import runs, [29562152128](https://github.com/TJ-90/podcast-clip-app/actions/runs/29562152128) and [29562160851](https://github.com/TJ-90/podcast-clip-app/actions/runs/29562160851), both completed inert source import before GitHub rejected Actions-created PRs under the then-current repository setting. The latter identity was selected and opened as PR #1 with the authenticated repository owner. This PR-policy failure did not execute Android code or count as a candidate validation dispatch.

## Control root cause

The safe importer deliberately treated upstream controls conservatively, but the admission workflow failed to reproduce the complete reviewed contents of AntennaPod's root `gradle.properties` in its tokenless task environment. The first correction supplied two Android properties and omitted the third JVM memory property. This is a trusted control-plane defect, not an AntennaPod source change, but both attempted validations still consumed the approved candidate budget.

Candidate commit `c58e2607c57925486b856416e1b3f9044673e2be` was never amended. No Gradle, Android SDK, dependency, source archive, emulator, APK, or CI artifact was downloaded or executed on the operator device.

## Acceptance impact

- AC-01 Base admission: **not satisfied**.
- AC-02 License/provenance/import safety: import-safety evidence passed for the preserved candidate, but Story 1 is not complete because the candidate is not admitted.
- Candidate merge: **forbidden under the current plan**.
- Next workflow state: **RALPLAN_REQUIRED**.

RALPLAN must explicitly decide whether to authorize a fresh exact candidate identity with a complete reviewed environment overlay and a reset evidence budget, select a different base under an equal gate, or stop. Implementation must not silently relax the two-success rule or reinterpret either counted failure.

## One-time recovery terminal evidence

The reviewed one-time recovery reopened only a single preflight attempt; it did not reset or relax any candidate-validation condition. Trusted control commit [fc0ed383c0f4e1cf527f88d0ac3033973a379a4e](https://github.com/TJ-90/podcast-clip-app/commit/fc0ed383c0f4e1cf527f88d0ac3033973a379a4e) registered workflow ID 315057380 with zero prior dispatches. Main, workflow identity, and the zero-run count were re-read immediately before dispatch.

The workflow was dispatched exactly once as [run 29575201182](https://github.com/TJ-90/podcast-clip-app/actions/runs/29575201182), attempt 1, at the exact control head. Job 87867988858 proved the sole workflow_dispatch identity, fetched and Git-blob-verified the immutable parser/test/validator controls without checkout, and passed all 11 stdlib control tests. The sanitized non-executing parser then failed closed with: Reject: non-canonical Git path: '../common.gradle'.

The path is a relative static Gradle input encountered by the trusted parser. This is a preflight-control rejection; no candidate source was executed. The closed-report validator and pinned uploader were skipped, so no preflight report artifact was published or downloaded. The workflow concluded failure; its dispatch count remains exactly one. Main remained fc0ed383c0f4e1cf527f88d0ac3033973a379a4e throughout the run.

Per the approved recovery contract, failure or cancellation of the sole preflight is terminal. The run was not rerun, no second preflight was created, no fresh candidate identity/branch/PR was created, and no fresh candidate-validation dispatch was spent. AntennaPod remains unadmitted and Story 2 must not start.

Only GitHub API metadata and the job log were inspected from the operator device. No source archive, Gradle distribution, Android SDK, dependency, CI artifact, APK, or candidate content was downloaded locally.
