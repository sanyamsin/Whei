"""Unit tests for the WHEI pipeline (pytest)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_index import INDICATOR_COLS, build, impute, normalize  # noqa: E402

RAW = pd.read_csv(Path(__file__).resolve().parents[1] / "data/raw/whei_indicators_snapshot.csv")


def test_normalization_bounds():
    imputed, _ = impute(RAW)
    norm = normalize(imputed)
    for col in INDICATOR_COLS:
        assert norm[col].min() >= 0.0
        assert norm[col].max() <= 100.0


def test_direction_inversion():
    """The country with the WORST maternal mortality must get the LOWEST normalized mmr score."""
    imputed, _ = impute(RAW)
    norm = normalize(imputed)
    worst = imputed["mmr"].idxmax()
    assert norm.loc[worst, "mmr"] == 0.0


def test_scores_within_range():
    scores, _ = build(RAW)
    for scheme in ("equal", "pca", "expert"):
        assert scores[f"whei_{scheme}"].between(0, 100).all()


def test_ranks_are_complete():
    scores, _ = build(RAW)
    assert sorted(scores["rank_equal"]) == list(range(1, len(scores) + 1))


def test_imputation_flags():
    _, flags = impute(RAW)
    assert flags.values.sum() == RAW[INDICATOR_COLS].isna().values.sum()
