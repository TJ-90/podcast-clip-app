# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-07-21
- Primary product surfaces: Home, Discover, Library, Clips, full player, clip editor, Settings
- Evidence reviewed: approved v1 scope, the existing Compose foundation, hosted baseline generator, and accessibility tests

## Brand
- Personality: editorial, attentive, exact, warm, quietly confident
- Trust signals: explicit prices, local-first clips, plain transcript states, visible timecodes
- Avoid: purple gradients, glass, neon, oversized hero copy, decorative waveforms, AI mascots, fake profiles, excessive cards

## Product goals
- Goals: be a complete podcast listener; make a precise clip in seconds; make transcription optional and inexpensive
- Non-goals: accounts, social feeds, video, recommendations, cloud sync, Cast, Android Auto
- Success signals: a feed can be added, played in the background, clipped locally, and optionally transcribed

## Personas and jobs
- Primary personas: regular podcast listeners, researchers, students, writers
- User jobs: find and subscribe; resume listening; preserve a precise moment; read, copy, or share it
- Key contexts: headphones, commute, one-handed use, intermittent networks

## Information architecture
- Primary navigation: Home, Discover, Library, Clips
- Core routes/screens: four destinations plus player, clip editor, and settings sheets
- Content hierarchy: listening state first, episode identity second, operations third

## Design principles
- Content before chrome: artwork and episode identity carry the visual character
- Precision without clutter: common actions stay simple; exact time controls appear in the editor
- Calm honesty: no anthropomorphic transcription language and no fake certainty
- Tradeoff: v1 favors a small dependable feature set over social and recommendation surfaces

## Visual language
- Color: warm paper, near-black ink, restrained secondary text, one rust accent; warm charcoal in dark mode
- Typography: system type with deliberate scale and weight; no decorative font
- Spacing/layout rhythm: 8dp base rhythm, 20–24dp page gutters, bounded 720dp content width
- Shape/radius/elevation: 14–24dp soft functional corners, minimal elevation, pills only for compact state
- Motion: routine transitions under 300ms; no bounce, loops, confetti, or spring overshoot
- Imagery/iconography: podcast artwork is the expressive material; icons and text labels stay literal

## Components
- Existing components to reuse: mini-player, bottom navigation, artwork rows, editorial feature panel
- New/changed components: search result, subscription row, clip row, player sheet, clip range editor, settings sheet
- Variants and states: loading, empty, offline/error, subscribed, playing, exporting, transcribing, complete
- Token/component ownership: PodcastClipApp.kt owns the compact v1 system; colors and spacing are private tokens

## Accessibility
- Target standard: WCAG AA-like contrast and Android accessibility guidance
- Keyboard/focus behavior: task and reading order; no required drag-only interaction
- Contrast/readability: 48dp touch targets, timecodes as text, state never only color
- Screen-reader semantics: literal labels for play, clip, subscribe, seek, save, and transcription actions
- Reduced motion: no essential state depends on animation

## Responsive behavior
- Supported breakpoints/devices: Android API 26+, compact phones through tablets
- Layout adaptations: bounded center column; compact bottom navigation; sheets scroll on large fonts
- Touch/hover differences: all primary actions are touch-first and remain text-labelled

## Interaction states
- Loading: preserve layout and name the operation
- Empty: explain the next useful action
- Error: say what remains safe and provide recovery
- Success: update the affected row; avoid celebration
- Disabled: explain missing feed, playback, or key prerequisite
- Offline/slow network: saved clips and library remain available; network work fails without losing local data

## Content voice
- Tone: direct, calm, specific
- Terminology: clip, transcript, podcast, episode, subscribe, add RSS
- Microcopy rules: no “magic,” “thinking,” or “AI-powered”; show Groq price and key behavior plainly

## Implementation constraints
- Framework/styling system: Kotlin, Jetpack Compose Material 3, Media3, SQLite, OkHttp, Coil
- Design-token constraints: one accent; no new theme layer until the compact system has outgrown one file
- Performance constraints: stream playback, keep lists lazy, cap discovery results at 20
- Compatibility constraints: minSdk 26, targetSdk 36, background playback service
- Test/screenshot expectations: lint, unit tests, debug APK, and deterministic baseline renders run only in GitHub Actions

## Open questions
- [ ] Validate final player/clip-editor ergonomics on physical devices after the first APK is installed
- [ ] Decide whether a server-side proxy should replace bring-your-own Groq keys after v1 usage is known
