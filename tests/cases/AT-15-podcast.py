import json
import sys as _sys

from _common import *  # noqa: F403

_sys.path.insert(0, str(ROOT / "scripts"))


def _script(d, claim_ids, uncited=False):
    lines = [
        {"n": 1, "speaker": "Ana", "segment": "open", "kind": "transition",
         "text": "Here is the question.", "claims": []},
        {"n": 2, "speaker": "Ana", "segment": "open", "kind": "factual",
         "text": "The operator's own page does not list the partner as live.",
         "claims": [] if uncited else [claim_ids[0]]},
        {"n": 3, "speaker": "Ravi", "segment": "open", "kind": "opinion",
         "text": "So plan as though it does not work.", "claims": []},
    ]
    payload = {"schema_version": 1, "episode": "A fixture episode",
               "speakers": [{"name": "Ana", "voice_hint": "warm mid-range"},
                            {"name": "Ravi", "voice_hint": "brighter"}],
               "lines": lines}
    path = d / "build" / "podcast.script.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_factual_line_needs_a_claim():
    """AT-15: a factual line with an empty claims array fails the gate."""
    with tempdir() as d:
        bootstrap(d)
        cids = seed_claims(d)
        _script(d, cids, uncited=True)
        rc, out = sb(d, "verify", "--podcast")
        assert rc == 2, out
        assert "E-POD-UNCITED" in out, out

        _script(d, cids)
        rc, out = sb(d, "verify", "--podcast")
        assert rc == 0, out


def test_tts_plan_validates_and_audio_is_optional():
    """AT-15: the emitted plan validates, and a missing build/audio fails no gate."""
    from sourcebook.manifest import check

    with tempdir() as d:
        bootstrap(d)
        cids = seed_claims(d)
        _script(d, cids)
        rc, out = sb(d, "tts-plan")
        assert rc == 0, out
        plan = json.loads((d / "build" / "podcast.ttsplan.json").read_text(encoding="utf-8"))
        assert check(plan, "ttsplan", "podcast.ttsplan.json") == []
        assert len(plan["segments"]) == 3
        assert (d / "build" / "audio" / "concat.txt").is_file()

        shutil.rmtree(d / "build" / "audio")
        rc, out = sb(d, "verify", "--podcast")
        assert rc == 0, f"absent audio must never fail a gate:\n{out}"
