#!/usr/bin/env python3
"""Fast two-pass Audio Alignment QA for Brighter phonics clips.

Pass 1: scan candidate timings with audio energy/silence only.
Pass 2: optionally run Whisper only on top candidates per clip.
It never overwrites production config; it writes suggested files only.
"""
from __future__ import annotations

import argparse, json, math, re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "phonics-game"
CONFIG = GAME / "level2-clips-config.js"
REPORT = GAME / "audio_alignment_report.json"
SUMMARY_MD = GAME / "audio_alignment_summary.md"
SUGGESTED_CONFIG = GAME / "level2-clips-config.suggested.js"
VOWEL_TOKENS = {"A":["A","AH","AT","AM","AN","AS","AD","AP"],"E":["E","EH","EGG","ED","EN","ET"],"I":["I","IH","IF","IN","IS","IT","ICK","EEL","EEP"],"O":["O","OH","ON","OR","OF","OCK"],"U":["U","UH","UM","UP","US","UCK"]}
TRUE_WORDS = {"IF","IN","IS","IT","OF","ON","OR","UP","US","UM"}
MANUAL_ENDINGS = {"Q","X","Y"}


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


def cut_wav(src: Path, start: float, duration: float, out: Path) -> None:
    result = run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",f"{start:.3f}","-t",f"{duration:.3f}","-i",str(src),"-ar","16000","-ac","1",str(out)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def wav_energy(path: Path) -> Dict[str, float]:
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
        if not frames:
            return {"rms":0.0,"peak":0.0,"leadingSilenceMs":0.0,"trailingSilenceMs":0.0}
        import struct
        vals = struct.unpack("<" + "h" * (len(frames)//2), frames)
        abs_vals = [abs(v)/32768.0 for v in vals]
        rms = math.sqrt(sum(v*v for v in abs_vals)/max(1,len(abs_vals)))
        peak = max(abs_vals) if abs_vals else 0.0
        threshold = max(0.015, rms*0.25)
        first = next((i for i,v in enumerate(abs_vals) if v >= threshold), len(abs_vals))
        last = len(abs_vals)-1-next((i for i,v in enumerate(reversed(abs_vals)) if v >= threshold), len(abs_vals))
        sr = w.getframerate()
        return {"rms":rms,"peak":peak,"leadingSilenceMs":first/sr*1000,"trailingSilenceMs":max(0,len(abs_vals)-1-last)/sr*1000}


def normalize_text(text: str) -> str:
    words = " " + re.sub(r"[^A-Z]+", " ", text.upper()).strip() + " "
    repl = {" EH ":" A "," EYE ":" I "," WHY ":" Y "," YOU ":" U "," SEE ":" C "," SEA ":" C "," BEE ":" B "," BE ":" B "," ARE ":" R "," JAY ":" J "," KAY ":" K "," CUE ":" Q "," QUEUE ":" Q "," EX ":" X "," ZED ":" Z "," ZEE ":" Z "}
    for src,dst in repl.items():
        words = words.replace(src,dst)
    return re.sub(r"[^A-Z]", "", words)


def vowel_score(label: str, transcript: str) -> float:
    norm = normalize_text(transcript)
    if not norm: return 0.0
    if label in norm: return 1.0
    if label in TRUE_WORDS and normalize_text(label) in norm: return 1.0
    if any(tok in norm for tok in VOWEL_TOKENS.get(label[0], [])): return 0.35
    return 0.0


def load_whisper(model_name: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe(model_obj, wav: Path) -> Tuple[str, float | None]:
    if model_obj is None: return "", None
    segments, _ = model_obj.transcribe(str(wav), language="en", beam_size=3, vad_filter=False, condition_on_previous_text=False)
    texts, probs = [], []
    for s in segments:
        texts.append(s.text.strip())
        if getattr(s, "avg_logprob", None) is not None: probs.append(float(s.avg_logprob))
    return " ".join(texts).strip(), (None if not probs else sum(probs)/len(probs))


def energy_score(metrics: Dict[str,float], duration: float) -> float:
    score = 0.0
    score += min(metrics["rms"]*20, 0.50)
    score += min(metrics["peak"]*0.35, 0.20)
    score += max(0.0, 0.18 - min(metrics["leadingSilenceMs"],600)/600*0.18)
    score += max(0.0, 0.12 - min(metrics["trailingSilenceMs"],600)/600*0.12)
    if 0.45 <= duration <= 1.35: score += 0.15
    elif 0.30 <= duration <= 1.70: score += 0.07
    return round(score,4)


def final_score(label: str, energy: float, transcript: str) -> float:
    speech = vowel_score(label, transcript)
    if label[1] in MANUAL_ENDINGS: speech *= 0.35
    return round(energy + speech*0.25, 4)


def suggest_config(rows: List[Dict[str, object]], suggestions: Dict[str, Tuple[float,float]]) -> str:
    lines = ["window.PHONICS_LEVEL2_CLIPS = {"]
    for ri,row in enumerate(rows):
        lines.append(f'  "{row["row"]}": {{')
        lines.append(f'    audio: "{row["audio"]}?v=2",')
        lines.append("    clips: {")
        clips = row["clips"]
        for ci,clip in enumerate(clips):
            label = clip["label"]
            start,end = suggestions.get(label,(clip["start"],clip["end"]))
            comma = "," if ci < len(clips)-1 else ""
            lines.append(f'      "{label}": [{start:.3f}, {end:.3f}]{comma}')
        lines.append("    }")
        lines.append(f"  }}{',' if ri < len(rows)-1 else ''}")
    lines.append("};")
    return "\n".join(lines)+"\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="base.en")
    p.add_argument("--search-window", type=float, default=1.0)
    p.add_argument("--step", type=float, default=0.15)
    p.add_argument("--duration-padding", type=float, default=0.28)
    p.add_argument("--top-n-speech", type=int, default=3)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--output", default=str(REPORT))
    p.add_argument("--summary-output", default=str(SUMMARY_MD))
    p.add_argument("--suggested-config", default=str(SUGGESTED_CONFIG))
    p.add_argument("--use-speech", action="store_true")
    args = p.parse_args()
    if shutil.which("ffmpeg") is None:
        print("ffmpeg is required", file=sys.stderr); return 1
    rows = parse_config(CONFIG.read_text(encoding="utf-8"))
    results=[]; suggestions: Dict[str,Tuple[float,float]] = {}; processed=0
    model_obj = load_whisper(args.model) if args.use_speech else None
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for row in rows:
            src = GAME / str(row["audio"])
            for clip in row["clips"]:
                if args.limit and processed >= args.limit: break
                processed += 1
                label = str(clip["label"]); current_start=float(clip["start"]); current_end=float(clip["end"])
                base_duration = max(0.32, current_end-current_start+args.duration_padding)
                start_min=max(0.0,current_start-args.search_window); start_max=current_start+args.search_window
                candidates=[]; i=0; s=start_min
                while s <= start_max + 1e-9:
                    wav = tmp / f"{label}_{i}.wav"
                    try:
                        cut_wav(src,s,base_duration,wav); metrics=wav_energy(wav); e_score=energy_score(metrics,base_duration)
                        candidates.append({"start":round(s,3),"end":round(s+base_duration,3),"energyScore":e_score,"score":e_score,"transcript":"","confidence":None,**metrics})
                    except Exception as exc:
                        candidates.append({"start":round(s,3),"end":round(s+base_duration,3),"energyScore":-1,"score":-1,"error":str(exc)})
                    i += 1; s += args.step
                top = sorted(candidates, key=lambda x:x.get("energyScore",-1), reverse=True)[:max(1,args.top_n_speech)]
                if args.use_speech:
                    for cand in top:
                        wav = tmp / f"{label}_speech_{cand['start']}.wav"
                        try:
                            cut_wav(src,float(cand["start"]),base_duration,wav)
                            text,conf = transcribe(model_obj,wav)
                            cand["transcript"] = text; cand["confidence"] = conf; cand["score"] = final_score(label,float(cand["energyScore"]),text)
                        except Exception as exc:
                            cand["speechError"] = str(exc)
                best = max(top if args.use_speech else candidates, key=lambda x:x.get("score",-1)) if candidates else {"start":current_start,"end":current_end,"score":0}
                shift_ms = round((float(best["start"])-current_start)*1000)
                action = "keep_current" if abs(shift_ms) <= 120 else "review_suggested_timing"
                if best.get("score",0) > 0: suggestions[label] = (float(best["start"]),float(best["end"]))
                results.append({"label":label,"row":row["row"],"file":row["audio"],"currentStart":current_start,"currentEnd":current_end,"bestStart":best.get("start"),"bestEnd":best.get("end"),"shiftMs":shift_ms,"bestScore":best.get("score"),"energyOnlyBestScore":max([c.get('energyScore',-1) for c in candidates] or [-1]),"action":action,"bestTranscript":best.get("transcript",""),"topCandidates":sorted(top if args.use_speech else candidates,key=lambda x:x.get("score",-1),reverse=True)[:5]})
            if args.limit and processed >= args.limit: break
    report={"summary":{"clips":processed,"searchWindowSec":args.search_window,"stepSec":args.step,"useSpeech":args.use_speech,"topNSpeech":args.top_n_speech,"reviewSuggestedTiming":sum(1 for r in results if r["action"]!="keep_current")},"items":results}
    Path(args.output).write_text(json.dumps(report,indent=2),encoding="utf-8")
    Path(args.suggested_config).write_text(suggest_config(rows,suggestions),encoding="utf-8")
    lines=["# Audio Alignment QA Summary","","```json",json.dumps(report["summary"],indent=2),"```","","## Suggested timing review","","| Label | Current | Suggested | Shift ms | Score | Transcript |","|---|---:|---:|---:|---:|---|"]
    for r in results:
        if r["action"] != "keep_current": lines.append(f"| {r['label']} | {r['currentStart']:.3f}-{r['currentEnd']:.3f} | {r['bestStart']:.3f}-{r['bestEnd']:.3f} | {r['shiftMs']} | {r['bestScore']} | {r.get('bestTranscript','')} |")
    Path(args.summary_output).write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report["summary"],indent=2)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
