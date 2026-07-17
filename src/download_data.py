"""
WHEI — Data acquisition module.

Downloads the latest available values for the six WHEI indicators from the
World Bank Open Data API (which mirrors WHO / UNICEF / DHS-derived series),
for a configurable list of countries.

Usage:
    python src/download_data.py                 # refresh data/raw/whei_indicators.csv
    python src/download_data.py --countries CMR NGA SEN

Note: a static snapshot (data/raw/whei_indicators_snapshot.csv) is bundled with
the repository so that the pipeline and the app work offline / reproducibly.
Running this script produces a refreshed file alongside it.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# World Bank indicator codes -> WHEI column names
INDICATORS = {
    "SH.STA.MMRT": "mmr",                      # Maternal mortality ratio (per 100,000 live births)
    "SH.STA.BRTC.ZS": "skilled_birth",         # Births attended by skilled health staff (%)
    "SH.STA.ANV4.ZS": "anc4",                  # Antenatal care, at least 4 visits (%)
    "SP.DYN.CONM.ZS": "mcpr",                  # Modern contraceptive prevalence (% married women 15-49)
    "SE.SEC.ENRR.FE": "female_secondary_enroll",  # School enrollment, secondary, female (% gross)
    "SH.ANM.ALLW.ZS": "anemia_women",          # Prevalence of anemia, women of reproductive age (%)
}

DEFAULT_COUNTRIES = [
    "CMR", "NGA", "SEN", "MLI", "NER", "TCD", "CAF", "MRT", "BFA", "GHA",
    "CIV", "GIN", "BEN", "TGO", "ETH", "KEN", "TZA", "UGA", "RWA", "MOZ",
    "MWI", "ZMB", "ZWE", "MDG", "COD", "COG", "GAB", "SLE", "LBR", "AGO",
]

API_URL = "https://api.worldbank.org/v2/country/{countries}/indicator/{indicator}"


def fetch_indicator(indicator: str, countries: list[str]) -> pd.DataFrame:
    """Fetch the most recent non-null value of one indicator for each country.

    Tries the efficient `mrnev=1` query first; some indicators (e.g. education
    series) reject it with HTTP 400, in which case we fall back to fetching
    2010-2026 and keeping the latest non-null value per country.
    """
    url = API_URL.format(countries=";".join(countries), indicator=indicator)

    params = {"format": "json", "per_page": 2000, "mrnev": 1}
    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code == 400:  # mrnev not supported -> fallback
        params = {"format": "json", "per_page": 5000, "date": "2010:2026"}
        resp = requests.get(url, params=params, timeout=30)

    resp.raise_for_status()
    payload = resp.json()
    if len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["iso3", "country", "value", "year"])

    rows = [
        {
            "iso3": item["countryiso3code"],
            "country": item["country"]["value"],
            "value": item["value"],
            "year": item["date"],
        }
        for item in payload[1]
        if item["value"] is not None
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Keep only the most recent value per country (no-op for mrnev results)
    df = df.sort_values("year").groupby("iso3", as_index=False).last()
    return df


def build_dataset(countries: list[str]) -> pd.DataFrame:
    """Assemble the wide-format WHEI input table."""
    base: pd.DataFrame | None = None
    for code, name in INDICATORS.items():
        print(f"Fetching {name} ({code}) ...")
        try:
            df = fetch_indicator(code, countries)
        except requests.RequestException as exc:
            print(f"  WARNING: {name} failed ({exc}) — column will be empty")
            df = pd.DataFrame(columns=["iso3", "country", "value", "year"])
        df = df.rename(columns={"value": name, "year": f"{name}_year"})
        if base is None:
            base = df[["iso3", "country", name, f"{name}_year"]]
        else:
            base = base.merge(
                df[["iso3", name, f"{name}_year"]], on="iso3", how="outer"
            )
        time.sleep(0.5)  # be polite to the API
    assert base is not None
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Download WHEI indicator data.")
    parser.add_argument("--countries", nargs="+", default=DEFAULT_COUNTRIES,
                        help="ISO3 country codes (default: 30 African countries)")
    parser.add_argument("--out", default="data/raw/whei_indicators.csv")
    args = parser.parse_args()

    df = build_dataset(args.countries)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nSaved {len(df)} countries x {len(INDICATORS)} indicators -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
