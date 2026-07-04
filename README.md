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
Start -> Station Review -> Follow Row / Tap Carriage -> 5/10/20-question Train Practice -> Result
```

Default practice is 5 questions with 4 choices. Homework mode is 10 questions with 6 choices. Challenge mode is 20 questions with 8 choices. Each question allows 3 tries.

Teacher audio is used first. If audio cannot play, the page falls back to browser speech.

## Important files

```text
phonics-game/homework.html
phonics-game/js/homework-game.js
phonics-game/css/homework-game.css
phonics-game/clips-config.js
phonics-game/level2-clips-config.js
phonics-game/audio_manifest.json
phonics-game/assets/
scripts/audio-qa.js
AGENTS.md
SKILL.md
```

## Audio QA workflow

Run from the repository root:

```bash
node scripts/audio-qa.js
```

The script reads `phonics-game/audio_manifest.json`, `phonics-game/level2-clips-config.js`, and `phonics-game/assets/`.

It reports missing audio, unused audio, duplicate audio ids, filename/letter mismatches, missing phoneme metadata, manifest/config clip mismatches, and items marked `review_required`.

If `ffprobe` is installed, it also reports basic duration and can catch zero-duration files.

## Adding new phonics audio

1. Put the audio file under `phonics-game/assets/`.
2. Add the row and timings in `phonics-game/level2-clips-config.js`.
3. Add the same file to `phonics-game/audio_manifest.json`.
4. Keep the manifest file path query-string free, for example `assets/brighter-a.mp3`.
5. Fill in `id`, `file`, `expectedText`, `expectedPhoneme`, `type`, `relatedLetter`, `relatedWord`, `qaStatus`, and `qaNotes`.
6. If the spoken sound has not been confirmed by human listening or speech recognition, keep `qaStatus` as `review_required`.

## Meaning of review_required

`review_required` means the audio is traceable and referenced correctly, but the actual spoken phonics content still needs human listening review.

Do not mark an item as pass just because the MP3 exists. Mark it pass only after confirming the expected row or label is correct, the timing does not cut off the sound, volume is acceptable, and no wrong phonics sound is inside the clip.

## QA report example

```text
summary:
  manifestItems: 5
  gameReferencedAudioFiles: 5
  gameReferencedRows: 5
  errors: 0
  warnings: 0
  reviewRequired: 5
```

## Manual test checklist

```text
[ ] Open phonics-game/homework.html directly
[ ] Select Brighter Phonics Train
[ ] Review A/E/I/O/U stations
[ ] Tap first, middle, and last carriage in each row
[ ] Confirm each sound matches the visible label
[ ] Follow Row highlights and plays in order
[ ] Stop button cancels Follow Row
[ ] Start 5-question practice
[ ] Try 10-question homework and 20-question challenge
[ ] Use All / A / E / I / O / U station filter
[ ] Correct answer increases score
[ ] Wrong answer reduces tries
[ ] Result appears after the session finishes
[ ] Missing audio does not crash the game
[ ] Mobile/iPad layout remains usable
```

## Agent notes

See `AGENTS.md` and `SKILL.md` before making future changes.
