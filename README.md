# Podcast Clips

Podcast Clips is a full Android podcast player built around one useful extra: keep the exact part you want and optionally get its transcript.

## v1

- Search Apple’s public podcast directory or add any RSS feed.
- Subscribe locally and refresh recent episodes without an account.
- Stream in the background with system media controls, speed control, precise seeking, a persistent **Up Next** queue, and last-position restoration.
- Download or remove app-private offline episodes.
- Select an exact 3-second–5-minute range; the editor defaults to the preceding 30 seconds.
- Export a playable local AAC/M4A clip before any network request.
- Replay, return to the source timestamp, delete with confirmation, or share audio, transcript text, or both.
- Optionally send a saved clip to Groq whisper-large-v3-turbo.
- Store the user-supplied Groq key with Android Keystore; no key is embedded or committed.
- Use a restrained warm-paper/rust Compose UI in light and dark themes, with literal labels and explicit empty/loading/error states.

Groq currently lists Whisper Large V3 Turbo at **$0.04 per audio hour**, with a minimum billed length per request. Playback and local clipping never require a key. If the network drops after an upload starts, the app marks the outcome unknown and asks the user to check provider usage before manually retrying; it never auto-resends a potentially billable request.

## Hosted Android development

The operator machine is intentionally not an Android build environment. [Android CI](.github/workflows/android-ci.yml) performs the entire development verification path on GitHub-hosted runners:

1. install JDK, Android 36, and Gradle 9.4.1;
2. run Android lint, JVM/Robolectric tests, build the debug APK, and render deterministic UI baselines;
3. run CodeQL, a tracked-source credential scan, APK SHA-256 generation, and an SPDX JSON SBOM;
4. boot an Android 35 emulator, run instrumentation tests, launch the app, and capture a runtime screenshot;
5. upload the APK, checksum, SBOM, test/lint reports, baselines, and device evidence.

Every external action is pinned to a full commit SHA and workflow permissions are explicit. No Android artifact is downloaded to the operator device.

## Privacy and storage

RSS and audio requests go directly to publishers. Discovery uses Apple’s iTunes Search API. Episodes, queue state, playback position, clips, and transcripts stay in app-private storage. Only a clip explicitly submitted for transcription is sent to Groq.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE), [UPSTREAM.md](UPSTREAM.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
