"""`sb tts-plan` — a provider-agnostic synthesis plan. Audio hooks, not audio.

sourcebook ships no TTS dependency and implements no adapter. The script, the citation
track, and this plan are the deliverable; a missing build/audio/ never fails a gate.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import EXIT_GATE, EXIT_OK
from .manifest import check, write_json

PAUSE_SPEAKER_CHANGE = 320
PAUSE_SENTENCE_FINAL = 180
PAUSE_SEGMENT_BOUNDARY = 600


def build_plan(script: dict, voices: dict | None = None) -> dict:
    voices = voices or {}
    declared = {}
    for s in script.get("speakers", []):
        declared[s["name"]] = {
            "hint": voices.get(s["name"], {}).get("hint") or s.get("voice_hint", ""),
            "voice_id": voices.get(s["name"], {}).get("voice_id"),
        }

    lines = sorted(script.get("lines", []), key=lambda ln: ln["n"])
    segments = []
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if nxt is None:
            pause = PAUSE_SEGMENT_BOUNDARY
        elif nxt.get("segment") != line.get("segment"):
            pause = PAUSE_SEGMENT_BOUNDARY
        elif nxt["speaker"] != line["speaker"]:
            pause = PAUSE_SPEAKER_CHANGE
        elif re.search(r"[.!?]\"?$", line["text"].strip()):
            pause = PAUSE_SENTENCE_FINAL
        else:
            pause = 0
        sid = f"s{line['n']:04d}"
        segments.append({
            "id": sid,
            "speaker": line["speaker"],
            "text": line["text"],
            "pause_after_ms": pause,
            "out": f"build/audio/{sid}.wav",
        })

    return {
        "schema_version": 1,
        "output_dir": "build/audio",
        "sample_rate": 24000,
        "format": "wav",
        "voices": declared,
        "segments": segments,
        "concat": {"manifest": "build/audio/concat.txt", "out": "build/audio/episode.wav"},
    }


def tts_plan(root: Path, voices_file: str | None = None) -> int:
    root = Path(root)
    script_path = root / "build" / "podcast.script.json"
    if not script_path.is_file():
        print(f"E-TTS  {script_path}  no podcast script; compose it first", file=sys.stderr)
        return EXIT_GATE
    script = json.loads(script_path.read_text(encoding="utf-8"))
    voices = json.loads(Path(voices_file).read_text(encoding="utf-8")) if voices_file else {}
    plan = build_plan(script, voices)

    errs = check(plan, "ttsplan", "build/podcast.ttsplan.json")
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return EXIT_GATE

    write_json(root / "build" / "podcast.ttsplan.json", plan)
    audio = root / "build" / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    # ffmpeg concat-demuxer format, so joining the pieces is one command and no adapter code.
    (audio / "concat.txt").write_text(
        "".join(f"file '{Path(s['out']).name}'\n" for s in plan["segments"]), encoding="utf-8")
    print(f"wrote build/podcast.ttsplan.json  {len(plan['segments'])} segment(s)")
    print("wrote build/audio/concat.txt      ffmpeg -f concat -i concat.txt -c copy episode.wav")
    return EXIT_OK
