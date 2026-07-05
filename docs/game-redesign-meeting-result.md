# Game Redesign Meeting Result — Phonics Train Journey 2.0

## Summary

This document records the five-round agent meeting held before implementation. The approved direction is **Phonics Train Journey 2.0**: keep the existing static phonics homework game, but make the experience feel more like a train journey with stations, tickets, progress, and arrival feedback.

## Round 1 — Problem Framing

### Game Designer
The current game works, but it still feels close to a normal listen-and-choose quiz page. The child needs a stronger goal and a clearer sense of journey.

### Level Designer
The current flow is usable: start screen, learn/review screen, quiz screen, result screen. However, A/E/I/O/U are not yet expressed as a route. They should become real stations in the journey.

### Narrative Designer
The game only needs a very light story: YURI is helping the Phonics Train collect sound tickets and reach the final station.

### Technical Artist
The redesign should be CSS-based and lightweight. Avoid heavy assets, external libraries, and complex animation. Keep mobile performance safe.

### Art Director
The game should move away from generic card UI and toward a storybook train map / sound ticket board style. Avoid random emoji overload.

### Phonics Learning Designer
Audio correctness is the highest priority. The redesign must not break teacher audio, clip timing, or the Brighter vowel-first rows.

### Frontend Game Developer
Do not rewrite the whole app. Keep existing HTML/CSS/JS structure and add safe containers for the new route and progress visuals.

### Playtest QA Agent
A 5-7 year old should understand what to do within 5 seconds, buttons must be large, and the quiz should remain short.

### Round 1 Consensus

```text
Problem:
The app functions, but the game feeling and journey goal are not strong enough.

Must preserve:
- Brighter A/E/I/O/U rows
- teacher audio timing
- review mode
- 5-question short homework session
- static GitHub Pages compatibility

Main risk:
A large redesign could break audio, mobile layout, or the existing quiz flow.
```

## Round 2 — Three Competing Game Concepts

### Concept A — Phonics Train Journey

The child is the train conductor. They visit A/E/I/O/U stations, listen to sounds, choose the correct sound ticket, and move the train forward.

Core loop:

```text
Choose Station -> Hear Sound -> Pick Ticket -> Train Moves -> Collect Star
```

Why it works:

```text
- Best match for the existing train theme
- Safe to implement on top of current app
- Stronger journey goal without changing audio logic
```

### Concept B — Sound Ticket Collector

The child collects sound tickets into an album. Correct answers become stamped tickets or stickers.

Why it works:

```text
- Strong collection motivation
- Good for repeat practice
```

Risk:

```text
- More state management
- More UI complexity
```

### Concept C — Phonics Rescue Mission

The sound tickets are scattered. The child listens and rescues the correct ticket back to the train.

Why it works:

```text
- Stronger action fantasy
```

Risk:

```text
- Drag/drop or rescue interactions may be harder on iPhone Safari
- Higher implementation risk
```

## Round 3 — Agent Critique and Scoring

| Agent | Concept A Train Journey | Concept B Ticket Collector | Concept C Rescue Mission | Preferred |
|---|---:|---:|---:|---|
| Game Designer | 5 | 4 | 3 | A |
| Level Designer | 5 | 3 | 4 | A |
| Narrative Designer | 4 | 4 | 3 | A/B |
| Technical Artist | 5 | 4 | 3 | A |
| Art Director | 5 | 4 | 4 | A |
| Phonics Learning Designer | 5 | 4 | 3 | A |
| Frontend Game Developer | 5 | 4 | 2 | A |
| Playtest QA Agent | 5 | 4 | 3 | A |

### Round 3 Consensus

```text
Winner: Concept A — Phonics Train Journey

Reason:
It fits the current theme, is safest to implement, preserves audio learning, and is easiest for a 5-7 year old to understand.
```

## Round 4 — Final Direction and Scope Cut

### Selected Concept

```text
Phonics Train Journey 2.0
```

### MVP Scope

```text
1. Start screen copywriting should make Level 2 feel like a Brighter train journey.
2. Learn screen should include a station route visual: A -> E -> I -> O -> U -> Finish.
3. Review mode should visually support sound ticket cards.
4. Quiz screen should include a train journey progress container.
5. Result screen should feel like train arrival / homework completion.
```

### Explicitly Out of Scope

```text
- drag and drop
- complex map animation
- save progress
- login
- backend
- new audio cutting
- AI-generated images
- external libraries
- changing audio timing
```

### Files Expected to Change

```text
docs/game-redesign-meeting-result.md
phonics-game/homework.html
phonics-game/css/homework-game.css
phonics-game/js/homework-game.js
```

### Files That Should Not Change Unless Necessary

```text
phonics-game/level2-clips-config.js
phonics-game/clips-config.js
phonics-game/assets/*
```

## Round 5 — Implementation Plan and QA Gate

### Task List

```text
Phase 1:
- Create this meeting result document.

Phase 2:
- Update homework.html structure only.
- Add station route container.
- Add train journey progress container.
- Improve Level 2 copywriting.
- Improve result screen wording.

Phase 3:
- Update CSS for storybook train map, station route, ticket cards, and mobile layout.

Phase 4:
- Update JS to render route and journey progress.
- Keep audio playback core unchanged.

Phase 5:
- Run Playwright smoke test.
- Manual audio QA on first/middle/last clips per row.
- Manual iPhone Safari test.
```

### QA Gate

Must pass:

```text
- 5 rows still render
- each row still has 21 clips
- audio button still works or fallback works
- quiz still completes
- result screen appears
- no console error
- no real failed network requests
- mobile layout has no horizontal overflow
```

### Rollback Plan

If the redesign causes issues, rollback only:

```text
phonics-game/homework.html
phonics-game/css/homework-game.css
phonics-game/js/homework-game.js
```

Do not rollback or change audio config unless the issue is specifically in config.

### Final Approval Statement

```text
Approved direction: Phonics Train Journey 2.0

Implementation principle:
Small safe redesign. Do not rewrite the app. Audio correctness first. Game feeling second. Visual polish third.
```
