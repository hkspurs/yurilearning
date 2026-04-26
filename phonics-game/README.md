# YURI Learning - Two-letter Phonics Game

This is a simple phonics listening game for practising two-letter syllables such as BA, BE, BI, BO, BU.

## Files

- `index.html` - the game page
- `clips-config.js` - timestamp configuration for each phonics clip
- `assets/phonics_audio.mp3` - expected audio file path

## How to use

1. Open `index.html` in a browser.
2. The page will try to load `assets/phonics_audio.mp3` automatically.
3. If the audio is not available, use the file picker to select your MP3 manually.
4. Select a row, for example `B row`.
5. Press `開始遊戲`.
6. Listen to the original audio clip and choose the correct two-letter syllable.

## Adjusting clip timing

Edit `clips-config.js` or use the `Clips 設定` text box inside the page.

Example:

```javascript
window.PHONICS_CLIPS = {
  "B row": {
    "BA": [0.0, 1.1],
    "BE": [1.2, 2.3],
    "BI": [2.4, 3.5],
    "BO": [3.6, 4.7],
    "BU": [4.8, 5.9]
  }
};
```
