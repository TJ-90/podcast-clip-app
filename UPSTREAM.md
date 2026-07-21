# Upstream provenance

Podcast Clips v1 is a purpose-built implementation in this repository. No third-party podcast application source was admitted or copied into the shipped tree.

Two open-source bases were evaluated before implementation:

- PodAura at 9c154cbba2936725e1aef4a09a8f82be49ccb9a0 was rejected because its conventional persistent queue and process restoration did not meet the approved baseline.
- AntennaPod at 1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7 was quarantined and never merged after the remote validation gate could not be reproduced within its dispatch budget.

Historical candidate branches and closed pull request #1 are evidence only. They are not ancestors or dependencies of the v1 app. The selection record remains in [docs/base-selection-report.md](docs/base-selection-report.md).

Android source, SDKs, Gradle distributions, dependencies, APKs, and CI artifacts were not downloaded to the operator device. Android build and test work runs on GitHub-hosted infrastructure.
