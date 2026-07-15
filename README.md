# WAYPOINT — AI Powered Smart Tourism Intelligence Platform

This repository is a production-ready scaffold for WAYPOINT — an AI-powered platform that
recommends the best travel destinations considering crowding, weather, safety, budget,
sustainability and personalized preferences.

Quick start
1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Generate the synthetic dataset (500 records):

```bash
python3 dataset/generate_dataset.py
```

3. Run the Streamlit app:

```bash
streamlit run app.py
```

Project layout
- `app.py` — Streamlit application entry
- `dataset/` — dataset generator and generated CSV
- `data/` — data loading utilities
- `models/` — model prototypes and recommenders
- `services/` — external API wrappers (weather, maps, etc.)
- `utils/` — explainability and helpers

Next steps (implemented): dataset generator, basic recommender prototype, app scaffold.

The platform should solve real-world travel problems using Machine Learning, Recommendation Systems, Predictive Analytics, Explainable AI, and intelligent decision making.

CI / Testing
------------

This repo includes a GitHub Actions workflow that runs unit tests and publishes a coverage report on push/PR to `main`.

- Run tests locally:

```bash
python -m unittest discover -v
```

- Generate coverage locally:

```bash
pip install coverage
coverage run -m unittest discover -v
coverage report -m
coverage xml -i
```

- To enable automatic coverage uploads to Codecov, add a repository secret named `CODECOV_TOKEN` with your Codecov upload token. The CI step is conditional and will run only if `CODECOV_TOKEN` is present.

