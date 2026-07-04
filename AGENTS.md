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

## Required Agent Workflow

Every future change to the phonics game must proceed through these agents in order:

```text
1. Game Designer
2. Art Director
3. Phonics Learning Designer
4. Frontend Game Developer
5. Playtest QA Agent
```

Do not jump directly into coding unless the change is a tiny bug fix. For feature work, design and learning review must happen before implementation.

## Agent 1: Game Designer

Responsible for making the gameplay less boring.

Role prompt:

```text
You are the Game Designer.

Before coding, propose 3 different gameplay concepts for the phonics homework game.

Avoid generic quiz-card UI.

Each concept must include:
- core loop
- reward system
- level progression
- child interaction
- how phonics learning happens
- why it is different from a normal quiz webpage

Do not write code yet.
```

Rules:

- Avoid boring flashcard-only gameplay.
- Make sure the child has an obvious goal within 5 seconds.
- Prefer short rounds and immediate feedback.
- The game must still support Brighter phonics rows.

## Agent 2: Art Director

Responsible for making the screen look different from a generic AI webpage.

Role prompt:

```text
You are the Art Director.

Create a visual style direction before implementation.

Avoid generic AI webpage style:
- no default gradient hero
- no boring centered card only
- no generic rounded quiz buttons only
- no random emoji overload

Suggest 3 visual themes:
1. classroom homework desk
2. storybook adventure map
3. phonics train journey

For each theme, define:
- color palette
- layout style
- button style
- reward animation
- background elements
- mobile layout behavior
```

Rules:

- Keep the design child-friendly but not messy.
- Do not overload the interface with random emojis.
- Mobile and iPad layouts must be considered from the start.
- Use visual direction before CSS implementation.

## Agent 3: Phonics Learning Designer

Responsible for making the learning content suitable for 5-7 year old children.

Role prompt:

```text
You are the Phonics Learning Designer.

Review the phonics content.

Make sure:
- sounds are age appropriate
- words are simple
- levels progress from easy to harder
- no confusing similar sounds too early
- questions are short
- instructions are child-friendly

Suggest homework sessions of 5 to 10 questions only.
```

Rules:

- Keep instructions short and friendly.
- Avoid overloading the child with too many choices too early.
- Prefer 5-10 questions per short homework session.
- If using 20 questions, explain why and allow shorter session mode.
- Check that audio labels match actual audio timings.

## Agent 4: Frontend Game Developer

Responsible for implementation after the design direction is confirmed.

Role prompt:

```text
You are the Frontend Game Developer.

Implement only after Game Designer and Art Director decisions are confirmed.

Use static HTML, CSS, and JavaScript.
No backend.
No database.
No API key.
No external CDN unless approved.
Must work on GitHub Pages.
Keep paths relative.
```

Rules:

- Use plain HTML, CSS, and JavaScript unless explicitly approved.
- Keep paths relative for GitHub Pages.
- No backend, database, or API key.
- Do not add external CDN unless approved.
- Keep teacher audio as preferred source.
- Web Speech API is fallback only.
- Avoid inline event handlers.
- Prefer `addEventListener`, `textContent`, and `createElement`.

## Agent 5: Playtest QA Agent

Responsible for playtesting, not only reviewing code.

Role prompt:

```text
You are the Playtest QA Agent.

Test the game like a 5-7 year old child.

Check:
- Can the child understand what to do in 5 seconds?
- Are buttons large enough?
- Is feedback clear?
- Is the game too boring?
- Is the game too hard?
- Does audio work?
- Does restart work?
- Does it work on mobile?
- Any console error?
```

Rules:

- Test by actually playing through the game.
- Check mobile width.
- Check at least one first, middle, and last audio clip per row.
- Check console errors.
- Report issues in child-experience language, not only technical language.

## Current Important Files

```text
phonics-game/homework.html              Main homework game page
phonics-game/js/homework-game.js        Game logic: levels, review mode, quiz, audio playback
phonics-game/css/homework-game.css      Kid-friendly responsive styling
phonics-game/clips-config.js            Level 1 consonant + vowel clips, e.g. BA BE BI BO BU
phonics-game/level2-clips-config.js     Brighter vowel-first clip timings
phonics-game/assets/                    Audio / video assets used by the static page
```

## High Priority Roadmap

1. Keep `homework.html` as the main homework entry point.
2. Keep Level 2 display text as `Brighter Vowel Rows: A/E/I/O/U + consonant`.
3. Maintain A/E/I/O/U rows in `level2-clips-config.js`.
4. Keep one audio source per row.
5. Fix `Follow Row` so it works on iOS Safari.
6. Add shorter homework sessions of 5-10 questions.
7. Improve the game design so it is not only a quiz webpage.
8. Add or update README when audio paths, clip timings, or learning content change.

## WebGameTemplateForAgents Principles

Use these principles whenever changing the game:

- One clear player goal: the child should always know what to do next.
- Short feedback loop: tap, hear sound, answer, get instant feedback.
- Big touch targets: buttons should work well on iPhone and iPad.
- No login, no server, no build step required unless explicitly added.
- Data-driven content: phonics rows and audio timings should be in config/data files, not hardcoded in HTML.
- Small safe changes: prefer improving existing static files over introducing a large framework.
- Offline-friendly direction: avoid unnecessary external CDN dependencies for the phonics game.
- Parent/teacher readable: keep labels and helper text understandable for non-technical users.

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
  - Plays the selected row in order.
  - Highlights the current active cell.
  - Can be cancelled when user changes row, starts quiz, or presses a stop button.
  - On iOS Safari, do not call `audio.play()` repeatedly for every cell. One row follow should use one user-triggered play call.

### Quiz Mode

Required behaviour:

- Prefer short homework sessions of 5-10 questions.
- If 20-question mode remains, provide a shorter option.
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
- Avoid too many similar sounds too early for young children.

## Audio Rules

The preferred source is teacher audio/video clips. Web Speech API is only fallback.

Preferred multi-audio structure:

```js
window.PHONICS_LEVEL2_CLIPS = {
  "A row - AB to AZ": {
    audio: "assets/brighter-a.mp3?v=2",
    clips: {
      "AB": [6.089, 6.443]
    }
  }
};
```

When adding timings:

- Use seconds with three decimals where possible.
- Keep labels exactly uppercase, e.g. `AB`, `EZ`, `IY`.
- Do not add unsupported labels such as `AE` if not present in the Brighter video.
- Validate mapping with actual audio, not only file loading.

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
4. Review mode can play at least the first, middle, and last clip in each configured row.
5. Follow Row can start, highlight, continue, and stop/cancel.
6. Quiz starts with the selected session length.
7. Correct answers increase score.
8. Wrong answers reduce tries and reveal after 3 wrong attempts.
9. Result page appears after the session finishes.
10. Audio fallback does not crash if source file is missing.
11. iOS Safari works after a user tap.
12. No console errors.

## Do Not Do

- Do not convert this to a heavy framework without explicit approval.
- Do not remove the existing homework flow.
- Do not replace teacher audio with only computer speech.
- Do not use copyrighted song lyrics as the main learning content for this homework game.
- Do not create a backend or database for this simple static game.
- Do not proceed with coding feature work before running the required agent workflow.
