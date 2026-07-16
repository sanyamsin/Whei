"""
WHEI — Index construction module.

Methodology (OECD/JRC Handbook on Constructing Composite Indicators):
  1. Imputation      — median imputation for missing values (flagged).
  2. Normalization   — min-max rescaling to [0, 100]; indicators where higher
                       values mean *worse* equity (MMR, anemia) are inverted.
  3. Weighting       — three schemes:
                         (a) equal weights (baseline),
                         (b) PCA-based weights (data-driven),
                         (c) expert weights (health outcomes emphasized).
  4. Aggregation     — weighted arithmetic mean.
  5. Sensitivity     — Spearman rank correlation between weighting schemes.

Usage:
    python src/build_index.py                                # uses bundled snapshot
    python src/build_index.py --input data/raw/whei_indicators.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Indicator direction: +1 if higher is better, -1 if higher is worse
DIRECTIONS = {
    "mmr": -1,
    "skilled_birth": +1,
    "anc4": +1,
    "mcpr": +1,
    "female_secondary_enroll": +1,
    "anemia_women": -1,
}

# Expert weighting scheme: outcomes (MMR) weighted higher than determinants
EXPERT_WEIGHTS = {
    "mmr": 0.25,
    "skilled_birth": 0.20,
    "anc4": 0.15,
    "mcpr": 0.15,
    "female_secondary_enroll": 0.10,
    "anemia_women": 0.15,
}

INDICATOR_COLS = list(DIRECTIONS.keys())


def impute(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Median-impute missing indicator values; return data + missingness flags."""
    flags = df[INDICATOR_COLS].isna()
    out = df.copy()
    for col in INDICATOR_COLS:
        out[col] = out[col].fillna(out[col].median())
    return out, flags


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalize each indicator to [0, 100], handling direction."""
    norm = df.copy()
    for col, direction in DIRECTIONS.items():
        lo, hi = norm[col].min(), norm[col].max()
        if hi == lo:
            norm[col] = 50.0
            continue
        scaled = (norm[col] - lo) / (hi - lo) * 100.0
        norm[col] = scaled if direction > 0 else 100.0 - scaled
    return norm


def pca_weights(norm: pd.DataFrame) -> dict[str, float]:
    """Derive data-driven weights from the first principal component loadings."""
    X = StandardScaler().fit_transform(norm[INDICATOR_COLS])
    pca = PCA(n_components=1)
    pca.fit(X)
    loadings = np.abs(pca.components_[0])
    weights = loadings / loadings.sum()
    return dict(zip(INDICATOR_COLS, weights.round(4)))


def aggregate(norm: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Weighted arithmetic mean of normalized indicators."""
    w = pd.Series(weights)
    w = w / w.sum()
    return (norm[INDICATOR_COLS] * w).sum(axis=1).round(2)


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run the full pipeline; return scored dataframe + metadata."""
    imputed, flags = impute(df)
    norm = normalize(imputed)

    equal_w = {c: 1 / len(INDICATOR_COLS) for c in INDICATOR_COLS}
    pca_w = pca_weights(norm)

    result = df[["country", "iso3"]].copy()
    result["whei_equal"] = aggregate(norm, equal_w)
    result["whei_pca"] = aggregate(norm, pca_w)
    result["whei_expert"] = aggregate(norm, EXPERT_WEIGHTS)
    result["n_imputed"] = flags.sum(axis=1).values

    for scheme in ("equal", "pca", "expert"):
        result[f"rank_{scheme}"] = result[f"whei_{scheme}"].rank(ascending=False).astype(int)

    # Sensitivity: rank stability across weighting schemes
    rho_ep, _ = spearmanr(result["rank_equal"], result["rank_pca"])
    rho_ee, _ = spearmanr(result["rank_equal"], result["rank_expert"])
    rho_pe, _ = spearmanr(result["rank_pca"], result["rank_expert"])

    meta = {
        "n_countries": int(len(result)),
        "pca_weights": pca_w,
        "expert_weights": EXPERT_WEIGHTS,
        "rank_correlation": {
            "equal_vs_pca": round(float(rho_ep), 3),
            "equal_vs_expert": round(float(rho_ee), 3),
            "pca_vs_expert": round(float(rho_pe), 3),
        },
    }
    return result.sort_values("whei_equal", ascending=False).reset_index(drop=True), meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the WHEI composite index.")
    parser.add_argument("--input", default="data/raw/whei_indicators_snapshot.csv")
    parser.add_argument("--outdir", default="data/processed")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    scores, meta = build(df)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(outdir / "whei_scores.csv", index=False)
    (outdir / "whei_metadata.json").write_text(json.dumps(meta, indent=2))

    print(scores[["country", "whei_equal", "rank_equal", "n_imputed"]].head(10).to_string(index=False))
    print(f"\nRank stability (Spearman rho): {meta['rank_correlation']}")
    print(f"Saved -> {outdir}/whei_scores.csv, {outdir}/whei_metadata.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
