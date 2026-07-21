# Podcast Clips

Podcast Clips is a full Android podcast player built around one useful extra: save the exact part you want and optionally get its transcript.

## What works in v1

- Search the public iTunes podcast directory or add any RSS feed
- Subscribe and persist shows and episodes locally
- Stream episodes with background playback, system controls, speed, and ±30 second seeking
- Capture a precise 3 second–5 minute range around the current playhead
- Export clips to local MP4 audio, replay them, and share them
- Optionally transcribe a saved clip with Groq Whisper Large V3 Turbo
- Keep the Groq API key encrypted by Android Keystore; no key is committed or embedded
- Use light/dark editorial Compose UI with explicit empty, loading, and error states

Groq currently lists Whisper Large V3 Turbo at **$0.04 per audio hour**. A personal API key is optional; playback and local clipping work without one.

## Build and verification

Android development is intentionally remote-only for this repository. The Android CI workflow installs the Android toolchain, runs lint and unit tests, assembles the debug APK, renders deterministic UI baselines, and uploads reports/artifacts.

Trigger **Android CI** from the Actions tab or push to main. Download the podcast-clips-debug-apk artifact from the completed run.

## Privacy

Podcast RSS and audio requests go directly to their publishers. Discovery searches use Apple’s public iTunes Search API. Only a clip explicitly submitted for transcription is sent to Groq. The API key stays encrypted on the device.

## License

GPL-3.0-or-later. See LICENSE, UPSTREAM.md, and THIRD_PARTY_NOTICES.md.
