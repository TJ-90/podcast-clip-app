# Third-party notices

Podcast Clips is distributed under GPL-3.0-or-later. The shipped application is purpose-built and does not incorporate source from the evaluated podcast-app candidates documented in UPSTREAM.md.

Runtime and build libraries are resolved from the Gradle version catalog, including AndroidX/Jetpack Compose, Media3, OkHttp, Coil, Kotlin coroutines, JUnit, Truth, Robolectric, and AndroidX Test. Their respective licenses and notices remain authoritative.

Each successful Android CI run produces an SPDX JSON software bill of materials for the built APK and uploads it with dependency, checksum, lint, and test evidence. Nothing in this notice replaces the complete project license in LICENSE or the licenses of individual dependencies and services.

Optional transcription sends an explicitly selected saved clip to Groq under the user’s own Groq account and applicable service terms; Groq code is not bundled into the app.
