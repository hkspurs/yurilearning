# Game Redesign: Five-Round Agent Meeting Requirement

## Purpose

Before redesigning `phonics-game/homework.html`, the project agents must run a five-round design meeting and agree on the game direction. Do not jump straight into implementation.

The current game is a static GitHub Pages phonics homework game for a 5-7 year old child. The learning priority is Brighter vowel-first phonics rows and correct teacher audio timing.

## Agents Required

Use the newly added game-development agents together with the existing project agents:

```text
1. Game Designer
2. Level Designer
3. Narrative Designer
4. Technical Artist
5. Art Director
6. Phonics Learning Designer
7. Frontend Game Developer
8. Playtest QA Agent
```

Agent source files:

```text
agents/game-development/game-designer.md
agents/game-development/level-designer.md
agents/game-development/narrative-designer.md
agents/game-development/technical-artist.md
AGENTS.md
```

If `agents/game-development/narrative-designer.md` is missing, run:

```bash
bash scripts/import-narrative-designer-agent.sh
```

## Non-Negotiable Product Requirements

```text
- Main entry remains: phonics-game/homework.html
- Static HTML / CSS / JavaScript only
- Must work on GitHub Pages
- No backend
- No database
- No API key
- No external CDN unless explicitly approved
- Must be mobile-first: iPhone and iPad friendly
- Must preserve Brighter Level 2 A/E/I/O/U rows
- Teacher audio is primary; Web Speech API is fallback only
- Audio clips must remain data-driven in level2-clips-config.js
- Game sessions should prefer 5 or 10 questions
- 20 questions may exist only as challenge mode
- The child should understand what to do within 5 seconds
```

## Five-Round Meeting Process

### Round 1 — Problem Framing

Goal: agree what is wrong with the current game and what must improve.

Each agent must answer:

```text
- What is boring / confusing now?
- What should a 5-7 year old feel in the first 10 seconds?
- Which parts must not be broken?
- What is the main risk of redesigning this game?
```

Required output:

```markdown
## Round 1 Notes
### Game Designer
...
### Level Designer
...
### Narrative Designer
...
### Technical Artist
...
### Art Director
...
### Phonics Learning Designer
...
### Frontend Game Developer
...
### Playtest QA Agent
...

### Round 1 Consensus
- Problem statement:
- Design risks:
- Must preserve:
```

### Round 2 — Three Competing Game Concepts

Goal: create three different redesign directions.

The three concepts must not be minor reskins of the same quiz.

Each concept must define:

```text
- Name
- Child fantasy
- Core loop
- Level / station structure
- Reward system
- Audio interaction
- How phonics learning happens
- Mobile layout idea
- Why this is not a generic quiz webpage
```

Required output:

```markdown
## Round 2 Concepts
### Concept A
...
### Concept B
...
### Concept C
...
```

### Round 3 — Agent Critique and Scoring

Goal: each agent reviews the three concepts using their own specialty.

Scoring scale: 1 to 5.

```text
5 = excellent fit
4 = good with small changes
3 = workable but risky
2 = weak
1 = reject
```

Each agent must score:

```text
- Fun for child
- Phonics learning correctness
- Audio clarity
- Mobile usability
- Visual originality
- Implementation risk
- GitHub Pages suitability
```

Required output:

```markdown
## Round 3 Scoring Matrix
| Agent | Concept A | Concept B | Concept C | Preferred Concept | Reason |
|---|---:|---:|---:|---|---|

### Round 3 Critique Notes
...
```

### Round 4 — Final Direction and Scope Cut

Goal: pick one direction and cut anything too risky.

The meeting must decide:

```text
- Final game direction
- What to build first
- What to postpone
- What not to build
- Which existing files will change
- Which existing features must remain
```

Required output:

```markdown
## Round 4 Final Direction
### Selected Concept

### MVP Scope

### Explicitly Out of Scope

### Files Expected to Change

### Files That Should Not Change Unless Necessary
```

### Round 5 — Implementation Plan and QA Gate

Goal: create the concrete development plan, but still do not code until the meeting document is complete.

The plan must include:

```text
- Step-by-step implementation tasks
- CSS / layout tasks
- JavaScript logic tasks
- Audio config safety rules
- Mobile QA checklist
- Playwright QA checklist
- Manual parent/child playtest checklist
- Rollback plan
```

Required output:

```markdown
## Round 5 Implementation Plan
### Task List

### QA Gate

### Rollback Plan

### Final Approval Statement
```

## Required Deliverable Before Coding

Before any code change, create or update:

```text
docs/game-redesign-meeting-result.md
```

This file must contain all five rounds.

No implementation should start until `docs/game-redesign-meeting-result.md` contains:

```text
- Round 1 notes
- Round 2 concepts
- Round 3 scoring matrix
- Round 4 final direction
- Round 5 implementation plan
- Final approval statement
```

## Codex Prompt

Use this prompt when asking Codex to redesign the game:

```text
Read AGENTS.md and all files under agents/game-development/.

You must redesign the phonics game, but before coding you must run a five-round agent meeting exactly as specified in docs/game-redesign-five-round-agent-meeting.md.

Create docs/game-redesign-meeting-result.md first.

The meeting must include these agents:
1. Game Designer
2. Level Designer
3. Narrative Designer
4. Technical Artist
5. Art Director
6. Phonics Learning Designer
7. Frontend Game Developer
8. Playtest QA Agent

Do not modify homework.html, homework-game.css, homework-game.js, or audio config until the five-round meeting document is complete.

After the meeting document is complete, propose the smallest safe implementation plan. Do not rewrite the whole app unless the meeting explicitly justifies it.

Keep the game static and GitHub Pages compatible.
Keep Brighter phonics A/E/I/O/U rows and teacher audio timings.
Run Playwright smoke test after implementation:

HOMEWORK_URL="https://hkspurs.github.io/yurilearning/phonics-game/homework.html?v=gggeeeggu" npx playwright test tests/homework-pages-smoke.spec.js --project=chromium --reporter=list
```
