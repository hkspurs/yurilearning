#!/usr/bin/env python3
"""Offline phonics-aware speech validation for Brighter phonics clips.

The script cuts each configured clip, runs a local speech engine, and validates
speech output with phonics-aware rules instead of exact transcript matching only.
No API key is used.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "phonics-game"
CONFIG = GAME / "level2-clips-config.js"
CLIP_MANIFEST = GAME / "audio_clip_manifest.json"
REPORT = GAME / "audio_speech_qa_report.json"
SUMMARY_MD = GAME / "audio_speech_qa_summary.md"

TRUE_WORDS = {"IF", "IN", "IS", "IT", "OF", "ON", "OR", "UP", "US", "UM"}
MANUAL_ENDINGS = {"Q", "X", "Y"}
VOWEL_TOKENS = {
    "A": ["A", "AH", "AT", "AM", "AN", "AS", "AD", "AP"],
    "E": ["E", "EH", "EGG", "ED", "EN", "ET"],
    "I": ["I", "IH", "IF", "IN", "IS", "IT", "ICK", "EEL", "EEP"],
    "O": ["O", "OH", "ON", "OR", "OF", "OCK"],
    "U": ["U", "UH", "UM", "UP", "US", "UCK"],
}
PHONEME_ROOT = {"A": "/æ/", "E": "/e/", "I": "/ɪ/", "O": "/ɒ/", "U": "/ʌ/"}


def strip_query(value: str) -> str:
    return str(value).split("?", 1)[0]


def parse_level2_config(text: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    row_re = re.compile(
        r'"(?P<row>[AEIOU] row - [A-Z]{2} to [A-Z]{2})"\s*:\s*\{\s*audio:\s*"(?P<audio>[^"]+)"\s*,\s*clips:\s*\{(?P<body>.*?)\n\s*\}\s*\}',
        re.S,
    )
    clip_re = re.compile(r'"(?P<label>[AEIOU][A-Z])"\s*:\s*\[(?P<start>[0-9.]+)\s*,\s*(?P<end>[0-9.]+)\]')
    for m in row_re.finditer(text):
        clips = []
        for c in clip_re.finditer(m.group("body")):
            clips.append({"label": c.group("label"), "start": float(c.group("start")), "end": float(c.group("end"))})
        rows.append({"row": m.group("row"), "audio": strip_query(m.group("audio")), "clips": clips})
    return rows


def normalize_text(text: str) -> str:
    words = text.upper()
    replacements = {
        " EH ": " A ", " EYE ": " I ", " WHY ": " Y ", " YOU ": " U ",
        " SEE ": " C ", " SEA ": " C ", " BEE ": " B ", " BE ": " B ",
        " ARE ": " R ", " JAY ": " J ", " KAY ": " K ", " CUE ": " Q ",
        " QUEUE ": " Q ", " EX ": " X ", " ZED ": " Z ", " ZEE ": " Z ",
        " OH ": " OH ", " AH ": " AH ", " UH ": " UH ", " UM ": " UM ",
    }
    words = " " + re.sub(r"[^A-Z]+", " ", words).strip() + " "
    for src, dst in replacements.items():
        words = words.replace(src, dst)
    return re.sub(r"[^A-Z]", "", words)


def expected_variants(label: str) -> List[str]:
    return [label.upper(), " ".join(label.upper()), "-".join(label.upper()), ".".join(label.upper())]


def default_clip_meta(row_name: str, file_path: str, label: str) -> Dict[str, object]:
    vowel, ending = label[0], label[1]
    mode = "exact_text" if label in TRUE_WORDS else ("manual_only" if ending in MANUAL_ENDINGS else "phonics_similarity")
    accepted = sorted({label.lower(), f"{vowel.lower()} {ending.lower()}", f"{vowel.lower()}{ending.lower()}"})
    return {
        "id": f"{vowel.lower()}_{label.lower()}",
        "row": row_name,
        "file": file_path,
        "expectedText": label,
        "expectedPhoneme": f"{PHONEME_ROOT.get(vowel, '/') }+/{ending.lower()}/",
        "vowelFamily": vowel,
        "endingConsonant": ending,
        "acceptedTranscripts": accepted,
        "validationMode": mode,
        "qaStatus": "review_required",
        "qaNotes": [],
    }


def load_clip_manifest_defaults(rows: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    meta: Dict[str, Dict[str, object]] = {}
    for row in rows:
        for clip in row["clips"]:  # type: ignore[index]
            label = str(clip["label"])
            item = default_clip_meta(str(row["row"]), str(row["audio"]), label)
            meta[str(item["id"])] = item
    if CLIP_MANIFEST.exists():
        try:
            data = json.loads(CLIP_MANIFEST.read_text(encoding="utf-8"))
            for override in data.get("items", []):
                oid = override.get("id")
                if oid:
                    base = meta.get(oid, {})
                    base.update(override)
                    meta[oid] = base
        except Exception:
            pass
    return meta


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def cut_clip(src: Path, start: float, end: float, out: Path) -> None:
    duration = max(0.1, end - start)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src), "-ar", "16000", "-ac", "1", str(out)]
    result = run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


class SpeechEngine:
    name = "none"
    available = False
    init_error = "no engine selected"
    def transcribe(self, wav: Path) -> Tuple[str, Optional[float]]:
        return "", None


class FasterWhisperEngine(SpeechEngine):
    name = "faster-whisper"
    def __init__(self, model_name_or_path: str, local_only: bool):
        from faster_whisper import WhisperModel
        kwargs = {"device": "cpu", "compute_type": "int8"}
        if local_only:
            kwargs["local_files_only"] = True
        self.model = WhisperModel(model_name_or_path, **kwargs)
        self.available = True
        self.init_error = ""
    def transcribe(self, wav: Path) -> Tuple[str, Optional[float]]:
        segments, _ = self.model.transcribe(str(wav), language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        texts, probs = [], []
        for s in segments:
            texts.append(s.text.strip())
            if getattr(s, "avg_logprob", None) is not None:
                probs.append(float(s.avg_logprob))
        conf = None if not probs else sum(probs) / len(probs)
        return " ".join(texts).strip(), conf


class OpenAIWhisperEngine(SpeechEngine):
    name = "openai-whisper"
    def __init__(self, model_name: str, download_root: Optional[str]):
        import whisper
        self.model = whisper.load_model(model_name, download_root=download_root)
        self.available = True
        self.init_error = ""
    def transcribe(self, wav: Path) -> Tuple[str, Optional[float]]:
        result = self.model.transcribe(str(wav), language="en", fp16=False, condition_on_previous_text=False)
        return str(result.get("text", "")).strip(), None


class WhisperCppEngine(SpeechEngine):
    name = "whisper.cpp"
    def __init__(self, binary: str, model: str):
        self.binary = binary
        self.model = model
        self.available = True
        self.init_error = ""
    def transcribe(self, wav: Path) -> Tuple[str, Optional[float]]:
        out_base = str(wav.with_suffix(""))
        result = run([self.binary, "-m", self.model, "-f", str(wav), "-otxt", "-of", out_base])
        txt = wav.with_suffix(".txt")
        if txt.exists():
            return txt.read_text(encoding="utf-8", errors="ignore").strip(), None
        return (result.stdout or result.stderr).strip(), None


def pick_engine(args: argparse.Namespace) -> SpeechEngine:
    engine = SpeechEngine()
    engine.init_error = "No local speech engine available. Install faster-whisper, openai-whisper, or provide whisper.cpp binary/model."
    model_ref = args.model_path or args.model
    if args.engine in ("auto", "faster-whisper") and importlib.util.find_spec("faster_whisper") is not None:
        try:
            return FasterWhisperEngine(model_ref, local_only=args.local_files_only)
        except Exception as exc:
            if args.engine == "faster-whisper":
                engine.init_error = f"faster-whisper model unavailable: {exc}"
                return engine
    if args.engine in ("auto", "openai-whisper") and importlib.util.find_spec("whisper") is not None:
        try:
            return OpenAIWhisperEngine(args.model, args.model_path)
        except Exception as exc:
            if args.engine == "openai-whisper":
                engine.init_error = f"openai-whisper model unavailable: {exc}"
                return engine
    cpp_bin = args.whisper_cpp_bin or os.environ.get("WHISPER_CPP_BIN")
    cpp_model = args.whisper_cpp_model or os.environ.get("WHISPER_CPP_MODEL")
    if args.engine in ("auto", "whispercpp"):
        if cpp_bin and cpp_model and Path(cpp_bin).exists() and Path(cpp_model).exists():
            return WhisperCppEngine(cpp_bin, cpp_model)
        if args.engine == "whispercpp":
            engine.init_error = "whisper.cpp selected but binary/model path is missing or invalid"
    return engine


def vowel_family_match(vowel: str, normalized: str) -> bool:
    return any(tok in normalized for tok in VOWEL_TOKENS.get(vowel, []))


def accepted_match(accepted: List[str], normalized: str) -> bool:
    normalized_accepted = [normalize_text(x) for x in accepted]
    return any(a and (a == normalized or a in normalized) for a in normalized_accepted)


def validate_phonics(meta: Dict[str, object], transcript: str) -> Tuple[str, List[str], Dict[str, bool]]:
    label = str(meta.get("expectedText", ""))
    mode = str(meta.get("validationMode", "phonics_similarity"))
    vowel = str(meta.get("vowelFamily", label[:1]))
    normalized = normalize_text(transcript)
    accepted = list(meta.get("acceptedTranscripts", []))  # type: ignore[arg-type]
    flags = {
        "acceptedTranscriptMatched": accepted_match(accepted, normalized),
        "vowelFamilyMatched": vowel_family_match(vowel, normalized),
        "exactTextMatched": normalize_text(label) == normalized or normalize_text(label) in normalized,
    }
    notes: List[str] = []
    if mode == "manual_only":
        notes.append("manual_only: abstract/high-risk phonics code; speech recognition is advisory only")
        if flags["vowelFamilyMatched"]:
            notes.append("vowel family appears to match")
        return "review_required", notes, flags
    if not normalized:
        return "review_required", ["empty transcript"], flags
    if mode == "exact_text":
        if flags["exactTextMatched"] or flags["acceptedTranscriptMatched"]:
            return "pass", ["exact/accepted transcript matched"], flags
        return "review_required", [f"transcript '{transcript}' normalized to '{normalized}', expected '{label}'"], flags
    if flags["acceptedTranscriptMatched"] or flags["exactTextMatched"]:
        return "pass", ["phonics accepted transcript matched"], flags
    if flags["vowelFamilyMatched"]:
        return "review_required", ["vowel family matched, ending consonant not confirmed by speech recognition"], flags
    return "review_required", [f"transcript '{transcript}' normalized to '{normalized}', expected phonics label '{label}'"], flags


def write_summary(path: Path, report: Dict[str, object]) -> None:
    items = report.get("items", [])
    by_row: Dict[str, Dict[str, int]] = {}
    high_risk = []
    for item in items:  # type: ignore[assignment]
        row = item.get("row", "?")
        stat = by_row.setdefault(row, {"pass": 0, "review_required": 0, "fail": 0, "vowelFamilyMatched": 0})
        status = item.get("qaStatus", "review_required")
        stat[status] = stat.get(status, 0) + 1
        if item.get("vowelFamilyMatched"):
            stat["vowelFamilyMatched"] += 1
        if status != "pass" and (item.get("validationMode") == "manual_only" or not item.get("vowelFamilyMatched")):
            high_risk.append(item)
    lines = ["# Audio Speech QA Summary", "", "## Overall", "", "```json", json.dumps(report.get("summary", {}), indent=2), "```", "", "## By row", "", "| Row | Pass | Review | Fail | Vowel family matched |", "|---|---:|---:|---:|---:|"]
    for row, s in by_row.items():
        lines.append(f"| {row} | {s.get('pass',0)} | {s.get('review_required',0)} | {s.get('fail',0)} | {s.get('vowelFamilyMatched',0)} |")
    lines += ["", "## High risk / manual review clips", ""]
    for item in high_risk[:60]:
        lines.append(f"- {item.get('id')} expected `{item.get('expectedText')}`, transcript `{item.get('transcript')}`, mode `{item.get('validationMode')}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["auto", "faster-whisper", "openai-whisper", "whispercpp"], default="auto")
    parser.add_argument("--model", default="base.en")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--whisper-cpp-bin", default=None)
    parser.add_argument("--whisper-cpp-model", default=None)
    parser.add_argument("--clip-manifest", default=str(CLIP_MANIFEST))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default=str(REPORT))
    parser.add_argument("--summary-output", default=str(SUMMARY_MD))
    args = parser.parse_args()

    rows = parse_level2_config(CONFIG.read_text(encoding="utf-8"))
    if not rows:
        print("No rows parsed from level2 config", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None:
        report = {"summary": {"totalClips": 0, "pass": 0, "reviewRequired": 0, "fail": 1, "speechEngine": "none", "speechEngineAvailable": False}, "error": "ffmpeg is required", "items": []}
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1

    # Allow custom clip manifest path while still using defaults for missing items.
    global CLIP_MANIFEST
    CLIP_MANIFEST = Path(args.clip_manifest)
    clip_meta = load_clip_manifest_defaults(rows)
    engine = pick_engine(args)
    results = []
    total = pass_count = review_count = fail_count = 0

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for row in rows:
            src = GAME / str(row["audio"])
            for clip in row["clips"]:  # type: ignore[index]
                if args.limit and total >= args.limit:
                    break
                total += 1
                label = str(clip["label"])
                item_id = f"{label[0].lower()}_{label.lower()}"
                meta = dict(clip_meta.get(item_id, default_clip_meta(str(row["row"]), str(row["audio"]), label)))
                wav = tmp / f"{item_id}.wav"
                item = {**meta, "clipStart": clip["start"], "clipEnd": clip["end"], "speechEngine": engine.name, "speechEngineAvailable": engine.available, "transcript": "", "transcriptConfidence": None, "qaStatus": "review_required", "qaNotes": []}
                if not src.exists():
                    item["qaStatus"] = "fail"; item["qaNotes"].append("audio file missing"); fail_count += 1; results.append(item); continue
                try:
                    cut_clip(src, float(clip["start"]), float(clip["end"]), wav)
                    if not engine.available:
                        item["qaNotes"].append(engine.init_error); review_count += 1
                    else:
                        text, conf = engine.transcribe(wav)
                        status, notes, flags = validate_phonics(meta, text)
                        item.update(flags)
                        item["transcript"] = text; item["transcriptConfidence"] = conf; item["qaStatus"] = status; item["qaNotes"].extend(notes)
                        if status == "pass": pass_count += 1
                        elif status == "fail": fail_count += 1
                        else: review_count += 1
                except Exception as exc:
                    item["qaStatus"] = "fail"; item["qaNotes"].append(str(exc)); fail_count += 1
                results.append(item)
            if args.limit and total >= args.limit:
                break

    report = {"summary": {"totalClips": total, "pass": pass_count, "reviewRequired": review_count, "fail": fail_count, "speechEngine": engine.name, "speechEngineAvailable": engine.available, "engineInitError": "" if engine.available else engine.init_error, "validation": "phonics_aware"}, "items": results}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_summary(Path(args.summary_output), report)
    print(json.dumps(report, indent=2))
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
