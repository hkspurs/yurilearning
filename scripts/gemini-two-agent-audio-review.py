#!/usr/bin/env python3
"""Gemini two-agent audio timing review for Brighter phonics clips.

Goal: do NOT directly trust energy/silence timing. For each expected label, create
several candidate windows around the current timing, then ask two independent
Gemini prompts:

Agent 1 - Segmenter: choose which candidate best contains the complete teaching
pattern, e.g. AB = A ~ B ~ A ~ B ~ AB.

Agent 2 - Reviewer: listen to Agent 1's selected candidate and verify whether it
matches the expected label/pattern.

Only consensus results are written to level2-clips-config.two-agent-suggested.js.
Production config is never overwritten.
"""
from __future__ import annotations

import argparse, base64, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, wave
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "phonics-game"
CONFIG = GAME / "level2-clips-config.js"
REPORT = GAME / "two_agent_audio_review_report.json"
SUMMARY_MD = GAME / "two_agent_audio_review_summary.md"
SUGGESTED_CONFIG = GAME / "level2-clips-config.two-agent-suggested.js"


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


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def cut_wav(src: Path, start: float, end: float, out: Path) -> None:
    duration = max(0.1, end - start)
    result = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src), "-ar", "16000", "-ac", "1", str(out)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def make_silence(out: Path, seconds: float = 0.45) -> None:
    result = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", f"{seconds:.3f}", str(out)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg silence failed")


def concat_wavs(parts: List[Path], out: Path) -> None:
    list_file = out.with_suffix(".txt")
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
    result = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-ar", "16000", "-ac", "1", str(out)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg concat failed")


def build_candidates(start: float, end: float, audio_len: float) -> List[Dict[str, float]]:
    # Current timing is usually near the final blend sound. Full teaching pattern
    # likely starts before it. We offer fixed backward windows rather than one
    # fragile energy-detected answer.
    offsets = [1.6, 2.1, 2.6, 3.1, 3.6, 4.1, 4.6]
    candidates = []
    for i, off in enumerate(offsets, start=1):
        s = max(0.0, start - off)
        e = min(audio_len, end + 0.35)
        if e - s >= 1.0:
            candidates.append({"id": i, "start": round(s, 3), "end": round(e, 3), "duration": round(e-s, 3)})
    return candidates


def extract_gemini_text(data: Dict[str, object]) -> str:
    texts: List[str] = []
    for cand in data.get("candidates", []) if isinstance(data.get("candidates"), list) else []:
        content = cand.get("content", {}) if isinstance(cand, dict) else {}
        for part in content.get("parts", []) if isinstance(content.get("parts"), list) else []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def parse_json(text: str) -> Dict[str, object]:
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
    return {"error": f"Could not parse JSON: {text[:200]}"}


def call_gemini(audio_wav: Path, prompt: str, model: str, api_key: str, timeout: int, retries: int) -> Tuple[Dict[str, object], str]:
    audio_b64 = base64.b64encode(audio_wav.read_bytes()).decode("ascii")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model, safe='')}:generateContent?key={urllib.parse.quote(api_key)}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}, {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 300, "responseMimeType": "application/json"},
    }
    body = json.dumps(payload).encode("utf-8")
    last_error = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = extract_gemini_text(data)
                return parse_json(text), text
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')[:700]}"
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(2 ** attempt)
    return {"error": last_error or "Gemini call failed"}, last_error


def agent1_prompt(label: str, candidates: List[Dict[str, float]]) -> str:
    cand_text = "\n".join(f"Candidate {c['id']}: {c['start']:.3f}-{c['end']:.3f}s" for c in candidates)
    return f"""You are Agent 1: Audio Segmenter.

Task: choose which candidate contains the COMPLETE teaching pattern for expected label {label}.
The pattern should sound like: {label[0]} ~ {label[1]} ~ {label[0]} ~ {label[1]} ~ {label}
It should not be only the final blended sound. It should not start from the previous label.

The audio contains the candidates in this order, separated by short silences:
{cand_text}

Return JSON only:
{{
  "selectedCandidate": 1,
  "confidence": 0.0,
  "completePattern": true,
  "heardPatternLabel": "{label} or another label or UNKNOWN",
  "reason": "short reason"
}}
"""


def agent2_prompt(label: str) -> str:
    return f"""You are Agent 2: Audio Reviewer.

Listen to this single selected audio clip. Verify whether it contains the full teaching pattern for expected label {label}:
{label[0]} ~ {label[1]} ~ {label[0]} ~ {label[1]} ~ {label}

Reject if it is only the final blended sound, starts with the previous label, contains the next label, or does not match {label}.

Return JSON only:
{{
  "approved": true,
  "confidence": 0.0,
  "heardPatternLabel": "{label} or another label or UNKNOWN",
  "completePattern": true,
  "reason": "short reason"
}}
"""


def suggest_config(rows: List[Dict[str, object]], suggestions: Dict[str, Tuple[float, float]]) -> str:
    lines = ["window.PHONICS_LEVEL2_CLIPS = {"]
    for ri, row in enumerate(rows):
        lines.append(f'  "{row["row"]}": {{')
        lines.append(f'    audio: "{row["audio"]}?v=2",')
        lines.append("    clips: {")
        clips = row["clips"]
        for ci, clip in enumerate(clips):
            label = str(clip["label"])
            start, end = suggestions.get(label, (float(clip["start"]), float(clip["end"])))
            comma = "," if ci < len(clips)-1 else ""
            lines.append(f'      "{label}": [{start:.3f}, {end:.3f}]{comma}')
        lines.append("    }")
        lines.append(f"  }}{',' if ri < len(rows)-1 else ''}")
    lines.append("};")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemini-2.5-flash")
    p.add_argument("--row-prefix", default="A", choices=["A", "E", "I", "O", "U", "ALL"])
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--output", default=str(REPORT))
    p.add_argument("--summary-output", default=str(SUMMARY_MD))
    p.add_argument("--suggested-config", default=str(SUGGESTED_CONFIG))
    args = p.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY is missing", file=sys.stderr)
        return 2
    if shutil.which("ffmpeg") is None:
        print("ffmpeg is required", file=sys.stderr)
        return 1

    rows = parse_config(CONFIG.read_text(encoding="utf-8"))
    results = []
    suggestions: Dict[str, Tuple[float, float]] = {}
    processed = 0

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for row in rows:
            row_name = str(row["row"])
            if args.row_prefix != "ALL" and not row_name.startswith(args.row_prefix + " row"):
                continue
            src_mp3 = GAME / str(row["audio"])
            src_wav = tmp / f"{row_name[0]}.wav"
            cut_wav(src_mp3, 0.0, 999.0, src_wav)
            dur = audio_duration(src_wav)
            silence = tmp / "silence.wav"
            make_silence(silence)
            for clip in row["clips"]:
                if args.limit and processed >= args.limit:
                    break
                processed += 1
                label = str(clip["label"])
                current_start = float(clip["start"])
                current_end = float(clip["end"])
                candidates = build_candidates(current_start, current_end, dur)
                cand_files: List[Path] = []
                montage_parts: List[Path] = []
                for c in candidates:
                    f = tmp / f"{label}_cand{c['id']}.wav"
                    cut_wav(src_wav, c["start"], c["end"], f)
                    cand_files.append(f)
                    montage_parts.append(f)
                    montage_parts.append(silence)
                montage = tmp / f"{label}_montage.wav"
                concat_wavs(montage_parts, montage)

                a1, a1_raw = call_gemini(montage, agent1_prompt(label, candidates), args.model, api_key, args.timeout, args.max_retries)
                selected = int(a1.get("selectedCandidate", 0) or 0) if isinstance(a1, dict) else 0
                chosen = next((c for c in candidates if int(c["id"]) == selected), None)
                a2 = {"approved": False, "confidence": 0, "reason": "Agent 1 did not select a valid candidate"}
                a2_raw = ""
                consensus = False
                action = "review_required"
                if chosen:
                    chosen_file = tmp / f"{label}_chosen.wav"
                    cut_wav(src_wav, chosen["start"], chosen["end"], chosen_file)
                    a2, a2_raw = call_gemini(chosen_file, agent2_prompt(label), args.model, api_key, args.timeout, args.max_retries)
                    a1_ok = bool(a1.get("completePattern")) and str(a1.get("heardPatternLabel", "")).upper() == label and float(a1.get("confidence", 0) or 0) >= 0.65
                    a2_ok = bool(a2.get("approved")) and bool(a2.get("completePattern")) and str(a2.get("heardPatternLabel", "")).upper() == label and float(a2.get("confidence", 0) or 0) >= 0.65
                    consensus = a1_ok and a2_ok
                    if consensus:
                        suggestions[label] = (float(chosen["start"]), float(chosen["end"]))
                        action = "suggest_timing"
                results.append({
                    "label": label,
                    "row": row_name,
                    "current": [current_start, current_end],
                    "candidates": candidates,
                    "agent1": a1,
                    "agent2": a2,
                    "selectedCandidate": selected,
                    "suggested": [chosen["start"], chosen["end"]] if chosen else None,
                    "consensus": consensus,
                    "action": action,
                    "agent1Raw": a1_raw,
                    "agent2Raw": a2_raw,
                })
            if args.limit and processed >= args.limit:
                break

    report = {"summary": {"model": args.model, "clips": processed, "suggestTiming": sum(1 for r in results if r["action"] == "suggest_timing"), "reviewRequired": sum(1 for r in results if r["action"] != "suggest_timing")}, "items": results}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(args.suggested_config).write_text(suggest_config(rows, suggestions), encoding="utf-8")
    lines = ["# Two-Agent Audio Review Summary", "", "```json", json.dumps(report["summary"], indent=2), "```", "", "| Label | Action | Current | Suggested | Agent 1 | Agent 2 |", "|---|---|---:|---:|---|---|"]
    for r in results:
        a1 = r.get("agent1", {}) if isinstance(r.get("agent1"), dict) else {}
        a2 = r.get("agent2", {}) if isinstance(r.get("agent2"), dict) else {}
        lines.append(f"| {r['label']} | {r['action']} | {r['current']} | {r.get('suggested')} | {a1.get('heardPatternLabel')} / {a1.get('confidence')} | {a2.get('heardPatternLabel')} / {a2.get('confidence')} |")
    Path(args.summary_output).write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
