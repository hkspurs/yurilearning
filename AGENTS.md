# AGENTS.md - YURI Brighter Phonics Web Game

## Project Goal

This repository contains a kid-friendly static web game for a 5-7 year old child to practise phonics homework. The current priority is the `phonics-game/homework.html` game.

The game must follow the Brighter homework videos in Google Drive. The Brighter content is vowel-first phonics:

```text
A row: AB AC AD AF AG AH AJ AK AL AM AN AP AQ AR AS AT AV AW AX AY AZ
E row: EB EC ED EF EG EH EJ EK EL EM EN EP EQ ER ES ET EV EW EX EY EZ
I row: IB IC ID IF IG IH IJ IK IL IM IN IP IQ IR IS IT IV IW IX IY IZ
O row: OB OC OD OF OG OH OJ OK OL OM ON OP OQ OR OS OT OV OW OX OY OZ
U row: UB UC UD UF UG UH UJ UK UL UM UN UP UQ UR US UT UV UW UX UY UZ
```

The game should not drift back into a generic lyrics reader. Keep the learning focus on listening, repeating, choosing, and practising the Brighter vowel rows.

## Current Important Files

```text
phonics-game/homework.html              Main homework game page
phonics-game/js/homework-game.js        Game logic: levels, review mode, quiz, audio playback
phonics-game/css/homework-game.css      Kid-friendly responsive styling
phonics-game/clips-config.js            Level 1 consonant + vowel clips, e.g. BA BE BI BO BU
phonics-game/level2-clips-config.js     Brighter vowel-first clips, currently A row AB-AZ only
phonics-game/assets/                    Audio / video assets used by the static page
```

## High Priority Roadmap

1. Keep `homework.html` as the main homework entry point.
2. Rename Level 2 display text to `Brighter Vowel Rows: A/E/I/O/U + consonant`.
3. Extend `level2-clips-config.js` from A row only to A/E/I/O/U rows.
4. Support one audio/video source per row, while keeping compatibility with the existing `normalize()` function.
5. Add a `Follow Row` review mode that automatically plays the selected row in order and highlights the active cell.
6. Add row filter for quiz: `All / A / E / I / O / U`.
7. Keep the app deployable as static GitHub Pages. No backend.
8. Add or update README when audio paths, clip timings, or learning content change.

## WebGameTemplateForAgents Principles

Use these principles whenever changing the game:

- **One clear player goal:** the child should always know what to do next.
- **Short feedback loop:** tap, hear sound, answer, get instant feedback.
- **Big touch targets:** buttons should work well on iPhone and iPad.
- **No login, no server, no build step required unless explicitly added.**
- **Data-driven content:** phonics rows and audio timings should be in config/data files, not hardcoded in HTML.
- **Small safe changes:** prefer improving existing static files over introducing a large framework.
- **Offline-friendly direction:** avoid unnecessary external CDN dependencies for the phonics game.
- **Parent/teacher readable:** keep labels and helper text understandable for non-technical users.

## Game Requirements

### Screens

Maintain this flow:

```text
Start screen -> Learn/review screen -> Quiz screen -> Result screen
```

### Learn / Review Mode

Required behaviour:

- Show the selected row as large phonics cells.
- Tapping a cell plays the correct teacher audio clip.
- If teacher audio fails, fallback to Web Speech API.
- Show clear status text: which sound is playing.
- Add `Follow Row`:
  - Plays every clip in the selected row in order.
  - Highlights the current active cell.
  - Can be cancelled when user changes row, starts quiz, or presses a stop button.

### Quiz Mode

Required behaviour:

- Default homework is 20 questions.
- Each question gives 3 tries.
- Child presses `聽一聽` before choosing.
- Correct answer increases score by 1.
- Wrong answer disables only the wrong button and gives supportive feedback.
- After 3 wrong tries, reveal the correct answer.
- Result page shows final score and encouragement.

### Brighter Row Quiz

For vowel-first Brighter practice:

- Include A/E/I/O/U row filter.
- If a row filter is selected, question deck should only use that row.
- Choice options should prefer same-row distractors first.
- Keep option count reasonable on mobile. Ten options is acceptable if layout remains usable.

## Audio Rules

The preferred source is teacher audio/video clips. Web Speech API is only fallback.

Existing structure supports:

```js
window.PHONICS_LEVEL2_CLIPS = {
  "A row - AB to AZ": {
    "AB": [6.090, 6.570]
  }
};
```

The preferred multi-audio structure is:

```js
window.PHONICS_LEVEL2_CLIPS = {
  "A row - AB to AZ": {
    audio: "assets/brighter-a.mp4?v=1",
    clips: {
      "AB": [6.090, 6.570]
    }
  }
};
```

Keep `homework-game.js` compatible with both formats unless intentionally migrating all configs.

When adding timings:

- Use seconds with three decimals where possible.
- Keep labels exactly uppercase, e.g. `AB`, `EZ`, `IY`.
- Do not add unsupported labels such as `AE` if not present in the Brighter video.

## Code Style Rules

- Use plain HTML/CSS/JavaScript unless the user explicitly asks for a framework.
- Avoid inline event handlers in HTML.
- Prefer `addEventListener` over `onclick` for new code.
- Prefer `textContent` and `createElement` for dynamic user-visible content.
- Avoid unnecessary `innerHTML`; only use it for safe static template snippets.
- Keep game state in one clear object.
- Keep functions small and named by behaviour, e.g. `startQuiz`, `renderReviewGrid`, `playRowSequence`.
- Do not break old Level 1 config while adding Brighter Level 2 rows.
- Use cache-busting query strings only when needed, e.g. `?v=19`.

## Accessibility Rules

Add and preserve:

- `aria-label` for level buttons, audio buttons, and answer buttons.
- `aria-live="polite"` for audio status and quiz feedback.
- Visible `:focus-visible` styles.
- Keyboard usable buttons and selects.
- Respect `prefers-reduced-motion` for animations/transitions.
- Avoid relying on colour only; correct/wrong states should also use text or symbols.

## Mobile / iPad Rules

- Test at 375px width and iPad width.
- Buttons must be easy to tap.
- Avoid layouts that create tiny answer cells.
- Keep important buttons above the fold where possible.
- Do not require hover.

## Testing Checklist

Before finishing any change, manually check:

1. `phonics-game/homework.html` opens directly in browser.
2. Start screen shows available levels.
3. Brighter Level 2 shows A/E/I/O/U rows if configured.
4. Review mode can play at least the first and last clip in each configured row.
5. Follow Row can start, highlight, continue, and stop/cancel.
6. Quiz starts with 20 questions.
7. Correct answers increase score.
8. Wrong answers reduce tries and reveal after 3 wrong attempts.
9. Result page appears after 20 questions.
10. Audio fallback does not crash if source file is missing.
11. iOS Safari works after a user tap.
12. No console errors.

## Suggested Codex Task Prompt

Use this prompt when asking a coding agent to continue:

```text
Update hkspurs/yurilearning phonics-game/homework.html and related files to fully match the Brighter vowel-first homework videos.

Keep the current static GitHub Pages approach. Preserve the existing start / learn / quiz / result flow. Extend Level 2 from A row only to A/E/I/O/U rows. Add Follow Row playback with active-cell highlight and cancel support. Add row filtering for quiz. Improve accessibility with aria-label, aria-live, focus-visible, and prefers-reduced-motion. Avoid inline handlers and unnecessary innerHTML. Do not break Level 1.
```

## Do Not Do

- Do not convert this to a heavy framework without explicit approval.
- Do not remove the existing homework flow.
- Do not replace teacher audio with only computer speech.
- Do not use copyrighted song lyrics as the main learning content for this homework game.
- Do not create a backend or database for this simple static game.
