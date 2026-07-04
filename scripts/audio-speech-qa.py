#!/usr/bin/env python3
"""Offline speech validation for Brighter phonics clips.

This script cuts each configured clip, runs a local speech engine, and compares
transcript output with the expected phonics label. No API key is used.

Local model modes:
- faster-whisper with --model-path /models/faster-whisper/base.en
- faster-whisper with --model base.en, when model is already cached locally
- openai-whisper with --model base.en, when model is already cached locally
- whisper.cpp with --engine whispercpp --whisper-cpp-bin ... --whisper-cpp-model ...
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
REPORT = GAME / "audio_speech_qa_report.json"


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
        " EH ": " A ",
        " EYE ": " I ",
        " WHY ": " Y ",
        " YOU ": " U ",
        " SEE ": " C ",
        " SEA ": " C ",
        " BEE ": " B ",
        " BE ": " B ",
        " ARE ": " R ",
        " JAY ": " J ",
        " KAY ": " K ",
        " CUE ": " Q ",
        " QUEUE ": " Q ",
        " EX ": " X ",
        " ZED ": " Z ",
        " ZEE ": " Z ",
    }
    words = " " + re.sub(r"[^A-Z]+", " ", words).strip() + " "
    for src, dst in replacements.items():
        words = words.replace(src, dst)
    return re.sub(r"[^A-Z]", "", words)


def expected_variants(label: str) -> List[str]:
    letters = list(label.upper())
    return [label.upper(), " ".join(letters), "-".join(letters), ".".join(letters)]


def compare_transcript(label: str, transcript: str) -> Tuple[str, str]:
    norm = normalize_text(transcript)
    target = label.upper()
    if norm == target:
        return "pass", "exact letter match"
    if target in norm:
        return "pass", "target appears in transcript"
    if not norm:
        return "review_required", "empty transcript"
    return "review_required", f"transcript '{transcript}' normalized to '{norm}', expected '{target}'"


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
        cmd = [self.binary, "-m", self.model, "-f", str(wav), "-otxt", "-of", out_base]
        result = run(cmd)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["auto", "faster-whisper", "openai-whisper", "whispercpp"], default="auto")
    parser.add_argument("--model", default="base.en", help="model name, or faster-whisper model id when no --model-path")
    parser.add_argument("--model-path", default=None, help="local faster-whisper model directory, or openai-whisper download root")
    parser.add_argument("--local-files-only", action="store_true", help="do not download model files; use local cache/model only")
    parser.add_argument("--whisper-cpp-bin", default=None)
    parser.add_argument("--whisper-cpp-model", default=None)
    parser.add_argument("--limit", type=int, default=0, help="limit clips for quick test")
    parser.add_argument("--output", default=str(REPORT))
    args = parser.parse_args()

    rows = parse_level2_config(CONFIG.read_text(encoding="utf-8"))
    if not rows:
        print("No rows parsed from level2 config", file=sys.stderr)
        return 2

    if shutil.which("ffmpeg") is None:
        report = {"summary": {"totalClips": 0, "pass": 0, "reviewRequired": 0, "fail": 1, "speechEngine": "none", "speechEngineAvailable": False}, "error": "ffmpeg is required", "items": []}
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1

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
                wav = tmp / f"{str(row['row'])[0]}_{label}.wav"
                item = {
                    "id": f"{str(row['row'])[0].lower()}_{label.lower()}",
                    "row": row["row"],
                    "file": row["audio"],
                    "expectedText": label,
                    "expectedVariants": expected_variants(label),
                    "clipStart": clip["start"],
                    "clipEnd": clip["end"],
                    "speechEngine": engine.name,
                    "speechEngineAvailable": engine.available,
                    "transcript": "",
                    "transcriptConfidence": None,
                    "qaStatus": "review_required",
                    "qaNotes": [],
                }
                if not src.exists():
                    item["qaStatus"] = "fail"
                    item["qaNotes"].append("audio file missing")
                    fail_count += 1
                    results.append(item)
                    continue
                try:
                    cut_clip(src, float(clip["start"]), float(clip["end"]), wav)
                    if not engine.available:
                        item["qaNotes"].append(engine.init_error)
                        review_count += 1
                    else:
                        text, conf = engine.transcribe(wav)
                        status, note = compare_transcript(label, text)
                        item["transcript"] = text
                        item["transcriptConfidence"] = conf
                        item["qaStatus"] = status
                        item["qaNotes"].append(note)
                        if status == "pass":
                            pass_count += 1
                        else:
                            review_count += 1
                except Exception as exc:
                    item["qaStatus"] = "fail"
                    item["qaNotes"].append(str(exc))
                    fail_count += 1
                results.append(item)
            if args.limit and total >= args.limit:
                break

    report = {
        "summary": {
            "totalClips": total,
            "pass": pass_count,
            "reviewRequired": review_count,
            "fail": fail_count,
            "speechEngine": engine.name,
            "speechEngineAvailable": engine.available,
            "engineInitError": "" if engine.available else engine.init_error,
        },
        "items": results,
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
