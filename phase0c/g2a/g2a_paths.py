"""Path helpers and g1 import bootstrap for G2a (never writes into g1/)."""
from __future__ import annotations

import sys
from pathlib import Path

G2A_ROOT = Path(__file__).resolve().parent
PHASE0C = G2A_ROOT.parent
G1_ROOT = PHASE0C / "g1"
FIXTURE_POLICY_PATH = G1_ROOT / "fixtures" / "policy_fixture_eval.json"


def ensure_g1_on_path() -> Path:
    """Insert g1 onto sys.path without enabling bytecode writes into g1."""
    sys.dont_write_bytecode = True
    root = str(G1_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return G1_ROOT
