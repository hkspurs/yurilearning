#!/usr/bin/env python3
"""AI forced-choice audio judge for Brighter phonics clips.

This is different from speech-to-text. It cuts each configured clip and asks an
audio-capable AI model to choose the closest phonics label from the row choices.

Requires OPENAI_API_KEY. Writes:
- phonics-game/ai_audio_judge_report.json
- phonics-game/ai_audio_judge_summary.md
"""
from __future__ import annotations

import argparse, base64, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "phonics-game"
CONFIG = GAME / "level2-clips-config.js"
REPORT = GAME / "ai_audio_judge_report.json"
SUMMARY_MD = GAME / "ai_audio_judge_summary.md"

PHONICS_HINTS = {
    "A": "short a family, like a in apple",
    "E": "short e family, like e in egg",
    "I": "short i family, like i in igloo",
    "O": "short o family, like o in on",
    "U": "short u family, like u in up",
}


def strip_query(value: str) -> str:
    return str(value).split("?", 1)[0]


def parse_config(text: str) -> List[Dict[str, object]]:
    rows = []
    row_re = re.compile(r'"(?P<row>[AEIOU] row - [A-Z]{2} to [A-Z]{2})"\s*:\s*\{\s*audio:\s*"(?P<audio>[^"]+)"\s*,\s*clips:\s*\{(?P<body>.*?)\n\s*\}\s*\}', re.S)
    clip_re = re.compile(r'"(?P<label>[AEIOU][A-Z])"\s*:\s*\[(?P<start>[0-9.]+)\s*,\s*(?P<end>[0-9.]+)\]')
    for m in row_re.finditer(text):
        clips = [{"label": c.group("label"), "start": float(c.group("start")), "end": float(c.group("end"))} for c in clip_re.finditer(m.group("body"))]
        rows.append({"row": m.group("row"), "audio": strip_query(m.group("audio")), "clips": clips})
    return rows


def run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def cut_wav(src: Path, start: float, end: float, out: Path, pad: float) -> None:
    s = max(0.0, start - pad)
    duration = max(0.1, end - start + pad * 2)
    result = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s:.3f}", "-t", f"{duration:.3f}", "-i", str(src), "-ar", "16000", "-ac", "1", str(out)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def nearby_choices(row_labels: List[str], label: str, radius: int) -> List[str]:
    if radius <= 0 or label not in row_labels:
        return row_labels
    idx = row_labels.index(label)
    start = max(0, idx - radius)
    end = min(len(row_labels), idx + radius + 1)
    choices = row_labels[start:end]
    if label not in choices:
        choices.insert(0, label)
    return choices


def build_prompt(label: str, row_name: str, choices: List[str]) -> str:
    vowel = label[0]
    hint = PHONICS_HINTS.get(vowel, "short vowel phonics")
    choice_text = ", ".join(choices)
    return f"""You are judging a children's Brighter phonics audio clip.
Do not do free transcription. This is a forced-choice listening task.

Expected hidden label: {label}
Row: {row_name}
Vowel hint: {hint}
Available labels: {choice_text}

Listen to the audio and choose the single label that best matches the spoken phonics sound.
Return JSON only, no Markdown:
{{
  "heardLabel": "one label from Available labels or UNKNOWN",
  "confidence": 0.0,
  "vowelFamilyMatched": true,
  "reason": "short reason"
}}
"""


def extract_output_text(data: Dict[str, object]) -> str:
    if isinstance(data.get("output_text"), str):
        return str(data["output_text"])
    texts: List[str] = []
    for out in data.get("output", []) if isinstance(data.get("output"), list) else []:
        if not isinstance(out, dict):
            continue
        for content in out.get("content", []) if isinstance(out.get("content"), list) else []:
            if isinstance(content, dict):
                if isinstance(content.get("text"), str):
                    texts.append(content["text"])
                elif isinstance(content.get("output_text"), str):
                    texts.append(content["output_text"])
    return "\n".join(texts).strip()


def parse_ai_json(text: str) -> Dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {"heardLabel": "UNKNOWN", "confidence": 0.0, "vowelFamilyMatched": False, "reason": f"Could not parse AI JSON: {text[:200]}"}


def call_openai(audio_wav: Path, prompt: str, model: str, api_key: str, timeout: int, max_retries: int) -> Tuple[Dict[str, object], Dict[str, object]]:
    audio_b64 = base64.b64encode(audio_wav.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
            ]
        }],
        "temperature": 0,
        "max_output_tokens": 220,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = extract_output_text(data)
                return parse_ai_json(text), {"rawText": text, "responseId": data.get("id")}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP {exc.code}: {detail[:500]}"
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except Exception as exc:
            last_error = str(exc)
        if attempt < max_retries:
            time.sleep(2 ** attempt)
    return {"heardLabel": "UNKNOWN", "confidence": 0.0, "vowelFamilyMatched": False, "reason": last_error or "OpenAI call failed"}, {"error": last_error}


def result_status(expected: str, heard: str, confidence: float, vowel_matched: bool) -> str:
    heard = str(heard).upper()
    if heard == expected and confidence >= 0.65:
        return "pass"
    if heard == expected:
        return "review_required"
    if vowel_matched or (heard and heard[:1] == expected[:1]):
        return "review_required"
    return "high_risk"


def write_summary(path: Path, report: Dict[str, object]) -> None:
    items = report.get("items", [])
    by_row: Dict[str, Dict[str, int]] = {}
    for item in items:
        row = str(item.get("row", "?"))
        status = str(item.get("result", "review_required"))
        s = by_row.setdefault(row, {"pass": 0, "review_required": 0, "high_risk": 0, "fail": 0})
        s[status] = s.get(status, 0) + 1
    lines = ["# AI Audio Judge QA Summary", "", "## Overall", "", "```json", json.dumps(report.get("summary", {}), indent=2), "```", "", "## By row", "", "| Row | Pass | Review | High risk | Fail |", "|---|---:|---:|---:|---:|"]
    for row, s in by_row.items():
        lines.append(f"| {row} | {s.get('pass',0)} | {s.get('review_required',0)} | {s.get('high_risk',0)} | {s.get('fail',0)} |")
    lines += ["", "## Non-pass clips", "", "| Expected | AI heard | Confidence | Result | Reason |", "|---|---|---:|---|---|"]
    for item in items:
        if item.get("result") != "pass":
            reason = str(item.get("reason", "")).replace("|", "/")[:180]
            lines.append(f"| {item.get('expectedLabel')} | {item.get('aiHeardLabel')} | {item.get('confidence')} | {item.get('result')} | {reason} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gpt-4o-audio-preview")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--choice-radius", type=int, default=0, help="0 means use full row choices; otherwise use nearby labels only")
    p.add_argument("--pad", type=float, default=0.04)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--output", default=str(REPORT))
    p.add_argument("--summary-output", default=str(SUMMARY_MD))
    args = p.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        report = {"summary": {"status": "skipped", "reason": "OPENAI_API_KEY secret is missing"}, "items": []}
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_summary(Path(args.summary_output), report)
        print(json.dumps(report["summary"], indent=2))
        return 2
    if shutil.which("ffmpeg") is None:
        print("ffmpeg is required", file=sys.stderr)
        return 1

    rows = parse_config(CONFIG.read_text(encoding="utf-8"))
    items = []
    processed = pass_count = review_count = high_risk_count = fail_count = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for row in rows:
            row_labels = [str(c["label"]) for c in row["clips"]]
            src = GAME / str(row["audio"])
            for clip in row["clips"]:
                if args.limit and processed >= args.limit:
                    break
                processed += 1
                expected = str(clip["label"])
                wav = tmp / f"{expected}.wav"
                item = {"expectedLabel": expected, "row": row["row"], "file": row["audio"], "start": clip["start"], "end": clip["end"], "choices": nearby_choices(row_labels, expected, args.choice_radius)}
                try:
                    cut_wav(src, float(clip["start"]), float(clip["end"]), wav, args.pad)
                    prompt = build_prompt(expected, str(row["row"]), item["choices"])
                    ai, raw = call_openai(wav, prompt, args.model, api_key, args.timeout, args.max_retries)
                    heard = str(ai.get("heardLabel", "UNKNOWN")).upper().strip()
                    if heard not in item["choices"] and heard != "UNKNOWN":
                        heard = "UNKNOWN"
                    confidence = float(ai.get("confidence", 0.0) or 0.0)
                    vowel_matched = bool(ai.get("vowelFamilyMatched", False))
                    status = result_status(expected, heard, confidence, vowel_matched)
                    item.update({"aiHeardLabel": heard, "confidence": confidence, "vowelFamilyMatched": vowel_matched, "reason": ai.get("reason", ""), "result": status, "raw": raw})
                    if status == "pass": pass_count += 1
                    elif status == "high_risk": high_risk_count += 1
                    else: review_count += 1
                except Exception as exc:
                    item.update({"aiHeardLabel": "UNKNOWN", "confidence": 0.0, "vowelFamilyMatched": False, "reason": str(exc), "result": "fail"})
                    fail_count += 1
                items.append(item)
            if args.limit and processed >= args.limit:
                break
    report = {"summary": {"status": "completed", "model": args.model, "clips": processed, "pass": pass_count, "reviewRequired": review_count, "highRisk": high_risk_count, "fail": fail_count, "choiceRadius": args.choice_radius}, "items": items}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_summary(Path(args.summary_output), report)
    print(json.dumps(report["summary"], indent=2))
    return 1 if fail_count or high_risk_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
