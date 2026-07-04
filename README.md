# YURI Brighter Phonics Homework Game

Static GitHub Pages phonics game for Brighter homework practice.

Main page:

```text
phonics-game/homework.html
```

## Current learning focus

Brighter vowel-first rows:

```text
A: AB AC AD AF AG AH AJ AK AL AM AN AP AQ AR AS AT AV AW AX AY AZ
E: EB EC ED EF EG EH EJ EK EL EM EN EP EQ ER ES ET EV EW EX EY EZ
I: IB IC ID IF IG IH IJ IK IL IM IN IP IQ IR IS IT IV IW IX IY IZ
O: OB OC OD OF OG OH OJ OK OL OM ON OP OQ OR OS OT OV OW OX OY OZ
U: UB UC UD UF UG UH UJ UK UL UM UN UP UQ UR US UT UV UW UX UY UZ
```

## Game flow

```text
Start -> Review -> Follow Row / Tap Cell -> 20-question Quiz -> Result
```

The quiz gives 20 questions. Each question allows 3 tries. Teacher audio is used first. If audio cannot play, the page falls back to browser speech.

## Important files

```text
phonics-game/homework.html
phonics-game/js/homework-game.js
phonics-game/css/homework-game.css
phonics-game/clips-config.js
phonics-game/level2-clips-config.js
phonics-game/assets/
AGENTS.md
SKILL.md
```

## Adding new audio rows

`phonics-game/level2-clips-config.js` supports per-row audio files:

```js
window.PHONICS_LEVEL2_CLIPS = {
  "A row - AB to AZ": {
    audio: "assets/phonics_level2_ab_az.mp3?v=7",
    clips: {
      "AB": [6.090, 6.570],
      "AC": [9.050, 9.550]
    }
  }
};
```

Each clip timing is `[startSecond, endSecond]`.

Recommended asset names for the extra Brighter videos:

```text
phonics-game/assets/brighter-e.mp4
phonics-game/assets/brighter-i.mp4
phonics-game/assets/brighter-o.mp4
phonics-game/assets/brighter-u.mp4
```

The config already includes E/I/O/U rows. If the audio files are not present yet, the game will try browser speech fallback.

## Manual test checklist

```text
[ ] Open phonics-game/homework.html directly
[ ] Select Brighter Vowel Rows
[ ] Review A/E/I/O/U rows
[ ] Tap first and last cell in each row
[ ] Follow Row highlights and plays in order
[ ] Stop button cancels Follow Row
[ ] Start 20-question quiz
[ ] Use All / A / E / I / O / U row filter
[ ] Correct answer increases score
[ ] Wrong answer reduces tries
[ ] Result appears after 20 questions
[ ] Missing audio does not crash the game
[ ] Mobile/iPad layout remains usable
```

## Agent notes

See `AGENTS.md` and `SKILL.md` before making future changes.
