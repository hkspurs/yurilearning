# SKILL.md - Brighter Phonics Web Game

Use this guide when editing `phonics-game/homework.html` and related files.

Main goal: keep the game as a static GitHub Pages phonics homework game focused on Brighter vowel-first rows.

Rows:

```text
A: AB AC AD AF AG AH AJ AK AL AM AN AP AQ AR AS AT AV AW AX AY AZ
E: EB EC ED EF EG EH EJ EK EL EM EN EP EQ ER ES ET EV EW EX EY EZ
I: IB IC ID IF IG IH IJ IK IL IM IN IP IQ IR IS IT IV IW IX IY IZ
O: OB OC OD OF OG OH OJ OK OL OM ON OP OQ OR OS OT OV OW OX OY OZ
U: UB UC UD UF UG UH UJ UK UL UM UN UP UQ UR US UT UV UW UX UY UZ
```

Keep the static flow:

```text
Start -> Review -> Quiz -> Result
```

Rules:

- No backend.
- No database.
- Keep GitHub Pages compatible.
- Use teacher audio clips first.
- Use Web Speech API only as fallback.
- Put labels and clip timings in config files.
- Avoid inline onclick.
- Prefer addEventListener.
- Avoid unnecessary innerHTML.
- Keep Level 1 working.

Next task:

```text
Extend Level 2 from A row only to A/E/I/O/U rows. Add Follow Row playback with active-cell highlight. Add quiz row filter All/A/E/I/O/U. Improve aria-label, aria-live, focus-visible, and prefers-reduced-motion.
```

Manual checks:

```text
[ ] homework.html opens directly
[ ] Review plays clips
[ ] Quiz plays clips
[ ] Correct answer increases score
[ ] Wrong answer reduces tries
[ ] Result appears after 20 questions
[ ] Missing audio falls back safely
[ ] Mobile layout is usable
[ ] No console errors
```
