# Design

## Source of truth

- Status: Active
- Last refreshed: 2026-07-21
- Product surfaces: Home, Discover, Library/Up Next, Clips, full player, clip editor, Settings
- Evidence: approved v1 scope, shipped Compose implementation, hosted baseline renders, Android 35 smoke path

## Brand

- Personality: editorial, attentive, exact, warm, quietly confident
- Trust signals: explicit price, local-first clips, literal upload states, visible timecodes
- Avoid: purple gradients, glass, neon, decorative waveforms, AI mascots, fake profiles, generic dashboard grids

## Product contract

- Full listener: discover/RSS, subscribe, background playback, speed/seek, persistent queue, offline episodes, process restoration
- Differentiator: exact 3-second–5-minute AAC/M4A clips, preceding-30-second default
- Optional transcript: bring-your-own Groq key, explicit upload, durable result states, no automatic resend after unknown outcome
- Clip lifecycle: play, source return, delete confirmation, audio/text/both sharing
- Non-goals: accounts, social feeds, video, recommendations, cloud sync, Cast, Android Auto

## Information architecture

- Primary navigation: Home, Discover, Library, Clips
- Home: resume listening and latest subscribed episodes
- Discover: query-led Apple directory search and direct RSS
- Library: subscriptions, persistent Up Next, recent episodes, offline controls
- Clips: local saved moments, transcript states, source/lifecycle/share actions
- Player/editor/settings remain task-focused sheets

## Visual system

- Color: warm paper, near-black ink, one rust accent; warm charcoal dark mode
- Type: Android system font with strong editorial hierarchy, compact literal controls
- Layout: 8dp rhythm, 20–24dp gutters, 720dp maximum reading width, lazy lists
- Shape: 14–26dp functional corners, minimal elevation, no ornamental pills
- Imagery: podcast artwork carries expression; controls use text labels
- Motion: no essential animation, loops, bounce, confetti, or spring overshoot

## Interaction and content

- Common actions are immediate and labelled; destructive clip deletion requires confirmation.
- Precision is never drag-only: the clip editor includes ±0.1s and ±1s controls.
- A local clip is committed before transcription starts.
- OUTCOME_UNKNOWN explains possible billing and offers only a deliberate manual retry.
- Copy says clip, transcript, podcast, episode, subscribe, RSS, Up Next, and offline—never “magic” or “AI-powered.”

## Accessibility and adaptation

- Text-labelled controls, state conveyed by words as well as color, large-font sheets that scroll
- 48dp-class touch targets for primary controls and a linear TalkBack reading order
- Light/dark support; bounded phone/tablet layout; no state depends on motion
- Runtime navigation and persistence/offline paths execute on a hosted Android 35 emulator

## Implementation constraints

- Kotlin, Jetpack Compose Material 3, Media3, SQLite, OkHttp, Coil
- minSdk 26, target/compileSdk 36, JDK 17, Gradle 9.4.1
- One compact UI system; do not add a new design-system dependency for v1
- Android lint, tests, APK, CodeQL, SBOM, checksums, baselines, and emulator evidence are GitHub Actions responsibilities

## Known follow-up

- Validate final one-handed player and clip-editor ergonomics on physical hardware after installing the hosted APK.
- Reconsider a server proxy only if real usage makes bring-your-own Groq keys unsuitable.
