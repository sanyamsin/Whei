# 🌍 Women's Health Equity Index (WHEI)

**A composite index measuring equity in women's health across 30 African countries**  built from six WHO / World Bank / DHS-derived indicators, following the OECD/JRC Handbook on Constructing Composite Indicators.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B.svg)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**🔗 Live demo:** [whei.streamlit.app](https://whei.streamlit.app) *(update link after deployment)*

![WHEI dashboard preview](docs/preview.png)

---

## Why this project

Ministries of health and their partners need a single, decomposable signal to **prioritize investments in women's health** but averages hide inequities, and composite indices are only as credible as their methodology. This project demonstrates a fully transparent, tested, reproducible index pipeline:

- **Health outcomes**: maternal mortality, anemia (women 15–49)
- **Service coverage**: skilled birth attendance, ANC 4+ visits, modern contraceptive prevalence
- **Social determinants**: female secondary school enrollment

## Key features

| Feature | Where |
|---|---|
| Data refresh from World Bank Open Data API (WHO/DHS-derived series) | [`src/download_data.py`](src/download_data.py) |
| Full pipeline: imputation → normalization → weighting → aggregation | [`src/build_index.py`](src/build_index.py) |
| **Three weighting schemes** (equal, PCA-derived, expert) + rank-stability sensitivity analysis (Spearman ρ > 0.98) | [`src/build_index.py`](src/build_index.py) |
| Documented methodology with limitations & next steps | [`notebooks/01_methodology.ipynb`](notebooks/01_methodology.ipynb) |
| Interactive dashboard: choropleth map, rankings, country profiles | [`app/streamlit_app.py`](app/streamlit_app.py) |
| Unit tests on normalization bounds, direction inversion, rank completeness | [`tests/`](tests/) |

## Quickstart

```bash
git clone https://github.com/sanyamsin/whei.git
cd whei
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the pipeline (uses the bundled data snapshot)
python src/build_index.py

# Launch the dashboard
streamlit run app/streamlit_app.py

# Run tests
python -m pytest tests/ -v

# Optional: refresh data from the World Bank API
python src/download_data.py
```

## Methodology in one paragraph

Each indicator is median-imputed (with per-country transparency flags), min-max normalized to 0–100 with direction handling (so 100 always means better equity), then aggregated by weighted arithmetic mean under three weighting schemes. Rank stability across schemes is verified with Spearman correlations  the standard robustness check for composite indices. Full details, correlation structure, and limitations in the [methodology notebook](notebooks/01_methodology.ipynb). 
**Data note:** the bundled snapshot contains real values fetched from the World Bank Open Data API (WHO/DHS-derived series), with per-indicator reference years included for transparency. Reference years vary by country and indicator (survey-based series like ANC4+ are less frequent than modelled series like MMR) a documented limitation of latest-available-value indices. Run `python src/download_data.py` to refresh.

## Project structure

```
whei/
├── app/streamlit_app.py         # Interactive dashboard
├── src/
│   ├── download_data.py         # World Bank API data acquisition
│   └── build_index.py           # Index construction pipeline
├── notebooks/01_methodology.ipynb
├── data/
│   ├── raw/whei_indicators_snapshot.csv   # Bundled reproducible snapshot
│   └── processed/               # Pipeline outputs (generated)
├── tests/test_index.py
└── requirements.txt
```

## Roadmap

- [ ] Sub-national WHEI for Cameroon using DHS regional estimates
- [ ] Wealth-quintile equity decomposition (concentration index)
- [ ] Goalpost normalization (fixed benchmarks, HDI-style)
- [ ] Monte Carlo uncertainty intervals on ranks

## Author

**Serge-Alain Nyamsin**  Data Scientist with 12+ years of humanitarian & development field experience in West and Central Africa (EU, ECHO, AFD, UNICEF-funded programs).
[GitHub](https://github.com/sanyamsin) · [Hugging Face](https://huggingface.co/Lokozu)

## License

MIT see [LICENSE](LICENSE). Data sources retain their original licenses (WHO GHO, World Bank Open Data CC-BY 4.0).
