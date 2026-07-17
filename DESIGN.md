# Podcast Clips Design Constitution

Status: canonical, base-agnostic, and binding from the initial bootstrap commit.

## Product character

Podcast Clips is a serious listening tool with clipping built into playback. It should feel editorial, attentive, exact, warm, and quietly confident. Content and listening state lead; transcription is a useful operation, never a spectacle.

## Navigation and information architecture

- Primary destinations are Home, Discover, Library, and Clips.
- A persistent mini-player sits above primary navigation when audio is active.
- Queue is reached from the full player. Settings is reached through a plain settings control, not a fake profile or avatar.
- Full player, clip editor, clip detail, podcast detail, episode detail, queue, and settings are supporting flows rather than extra top-level tabs.
- Accounts, social feeds, video, recommendations, Android Auto, Cast, cloud sync, and “coming soon” placeholders are absent in v1.

## Visual language

- Use warm paper surfaces, near-black ink, restrained secondary text, and one rust accent. Dark mode uses warm charcoal rather than blue-black.
- Typography uses the system family with deliberate scale, weight, line length, and hierarchy. Do not add a decorative font.
- Artwork is the dominant expressive material. Layout, spacing, rules, labels, and timecodes provide structure.
- Prefer rectangular or softly rounded functional controls. Pills are reserved for true filters, states, or compact toggles.
- Forbidden: purple/blue gradients, neon glows, glass panels, floating orbs, sparkles, robots, “AI magic” copy, oversized empty hero areas, decorative waveform wallpaper, excessive cards, and gratuitous expressive shapes.

## Player and clipping

- The full player prioritizes artwork, episode/podcast identity, scrubber, elapsed/remaining time, playback controls, speed, queue, download, and a clearly labelled scissors Clip action.
- Pressing Clip captures the current playhead, pauses playback, and opens a full-height editor selecting the preceding 30 seconds, clamped to episode bounds.
- Clip range is 3 seconds through 5 minutes. Start and end handles are visually and semantically distinct. Exact timecodes, ±0.1s and ±1s controls, direct time entry, and a waveform/timeline alternative make precision available without relying on drag alone.
- Preview plays the unsaved range once. Save persists playable local audio before any upload. With no credential, offer Save clip; with a usable credential, offer Save & transcribe without making transcription mandatory.
- Transcript states are expressed plainly: awaiting key, queued/offline, sending, outcome unknown, rate limited, failed, invalid response, and complete. Avoid chat bubbles, typing indicators, “thinking,” or anthropomorphic language.

## Motion and feedback

- Routine motion stays under 300ms: press feedback 80–120ms, enter near 220ms, exit near 160ms.
- Motion clarifies continuity, selection, and hierarchy. Avoid bounce, looping decoration, spring overshoot, and celebratory confetti.
- Reduced-motion mode removes nonessential transitions while preserving state feedback.

## Accessibility

- Minimum touch target is 48dp. Text and meaningful controls meet WCAG AA-like contrast.
- Every icon-only action has a specific accessible name; state is never conveyed only by color.
- Focus order follows reading and task order. Player, queue, editor, transcript, error, and share flows remain operable with screen readers and switch access.
- Layouts support 200% font scaling for critical flows without hiding required actions. Scrolling is acceptable; clipping or overlap is not.
- The waveform editor exposes start/end values and increment/decrement actions plus direct entry, so precision never depends on vision or fine motor control.

## Adaptive layout

- Compact layouts use one content column and bottom navigation.
- Medium layouts may use a navigation rail and two-pane detail where it preserves context.
- Expanded layouts use bounded reading widths and stable master/detail relationships; they do not merely stretch compact cards.
- Mini-player, system bars, IME, and navigation never overlap primary actions.

## State design

Every major screen has deliberate loading, empty, offline, error, disabled, and recovery states. Errors say what remains safe and the next available action. Missing transcription credentials never block discovery, subscriptions, playback, downloads, queue, clipping, local save, library, or sharing.

## Review gate

Presentation changes must cite the governing section above. Screenshot baselines are deterministic and verify-only on pull requests. A baseline author cannot self-approve a changed baseline. This file may evolve only through a reviewed decision that records the reason and accessibility impact.

