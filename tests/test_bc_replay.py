"""The committed Phase 0 run replays offline from recordings and reproduces its numbers."""

import json
from pathlib import Path

from packs.building_control.run_gate import main

RUN = Path(__file__).parents[1] / "bench" / "runs" / "phase0" / "metrics.json"


def test_phase0_gate_replays_offline_with_the_same_result(tmp_path):
    main(["--out", str(tmp_path), "--self-judge", str(RUN.parents[2] / "self_judge")])
    got, committed = json.loads((tmp_path / "metrics.json").read_text()), json.loads(RUN.read_text())
    assert got["jev"]["live_calls"] == 0
    for arm in ("A", "B", "C", "B_oracle", "D", "D_blind"):
        for split in ("test", "reference"):
            assert got["arms"][arm][split]["accuracy"] == committed["arms"][arm][split]["accuracy"]
    assert got["gate"] == committed["gate"]
