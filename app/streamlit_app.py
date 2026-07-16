"""
WHEI — Interactive dashboard (Streamlit).

Run locally:   streamlit run app/streamlit_app.py
Deployed on:   Hugging Face Spaces
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_index import INDICATOR_COLS, build  # noqa: E402

st.set_page_config(page_title="Women's Health Equity Index", page_icon="🌍", layout="wide")

INDICATOR_LABELS = {
    "mmr": "Maternal mortality ratio (per 100k)",
    "skilled_birth": "Skilled birth attendance (%)",
    "anc4": "Antenatal care 4+ visits (%)",
    "mcpr": "Modern contraceptive prevalence (%)",
    "female_secondary_enroll": "Female secondary enrollment (%)",
    "anemia_women": "Anemia, women 15-49 (%)",
}


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    raw = pd.read_csv(ROOT / "data" / "raw" / "whei_indicators_snapshot.csv")
    scores, meta = build(raw)
    return raw, scores, meta


raw, scores, meta = load_data()

st.title("🌍 Women's Health Equity Index (WHEI)")
st.markdown(
    "A composite index measuring **equity in women's health** across 30 African "
    "countries, built from six WHO / World Bank / DHS-derived indicators. "
    "Methodology follows the OECD/JRC Handbook on Composite Indicators."
)

# ---- Sidebar controls -------------------------------------------------------
st.sidebar.header("Settings")
scheme = st.sidebar.radio(
    "Weighting scheme",
    ["equal", "pca", "expert"],
    format_func=lambda s: {"equal": "Equal weights (baseline)",
                           "pca": "PCA-derived weights",
                           "expert": "Expert weights (outcome-focused)"}[s],
)
score_col, rank_col = f"whei_{scheme}", f"rank_{scheme}"

st.sidebar.markdown("---")
st.sidebar.caption(
    "Rank stability across schemes (Spearman ρ): "
    f"equal↔PCA {meta['rank_correlation']['equal_vs_pca']}, "
    f"equal↔expert {meta['rank_correlation']['equal_vs_expert']}"
)

# ---- Layout -----------------------------------------------------------------
tab_map, tab_rank, tab_profile, tab_method = st.tabs(
    ["🗺️ Map", "📊 Ranking", "🔎 Country profile", "📖 Methodology"]
)

with tab_map:
    fig = px.choropleth(
        scores,
        locations="iso3",
        color=score_col,
        hover_name="country",
        hover_data={rank_col: True, "n_imputed": True, "iso3": False},
        color_continuous_scale="RdYlGn",
        range_color=(0, 100),
        scope="africa",
        labels={score_col: "WHEI score", rank_col: "Rank", "n_imputed": "Imputed values"},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=560)
    st.plotly_chart(fig, use_container_width=True)

with tab_rank:
    fig = px.bar(
        scores.sort_values(score_col),
        x=score_col, y="country", orientation="h",
        color=score_col, color_continuous_scale="RdYlGn", range_color=(0, 100),
        labels={score_col: "WHEI score", "country": ""},
    )
    fig.update_layout(height=700, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_profile:
    country = st.selectbox("Country", scores["country"].tolist())
    row_score = scores.loc[scores["country"] == country].iloc[0]
    row_raw = raw.loc[raw["country"] == country].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("WHEI score", f"{row_score[score_col]:.1f} / 100")
    c2.metric("Rank", f"{int(row_score[rank_col])} / {len(scores)}")
    c3.metric("Imputed indicators", int(row_score["n_imputed"]))

    prof = pd.DataFrame({
        "Indicator": [INDICATOR_LABELS[c] for c in INDICATOR_COLS],
        "Value": [row_raw[c] for c in INDICATOR_COLS],
        "Regional median": [raw[c].median() for c in INDICATOR_COLS],
    })
    st.dataframe(prof, use_container_width=True, hide_index=True)

with tab_method:
    st.markdown(
        """
### How the index is built
1. **Indicators** — six openly available series covering outcomes (maternal
   mortality, anemia), service coverage (skilled birth attendance, ANC4+,
   modern contraception) and social determinants (female secondary enrollment).
2. **Imputation** — median imputation; the number of imputed values per country
   is reported transparently (`n_imputed`).
3. **Normalization** — min-max rescaling to 0–100; "higher is worse" indicators
   (MMR, anemia) are inverted so 100 always means better equity.
4. **Weighting** — equal weights as baseline, with PCA-derived and
   expert-defined schemes as sensitivity variants.
5. **Aggregation** — weighted arithmetic mean.

### Limitations
- Indicators come from different survey years (latest available value per country).
- National averages mask sub-national and wealth-quintile inequities — a
  sub-national extension (DHS regional data) is the natural next step.
- Min-max normalization makes scores relative to the country sample, not
  absolute benchmarks.
        """
    )

st.caption("Data: WHO GHO / World Bank Open Data / DHS-derived series (snapshot). "
           "Code: github.com/sanyamsin/whei")
