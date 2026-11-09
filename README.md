# Warehouse Optimization

Notebook-based analysis of warehouse picking data (Georgia Tech dataset): data audit,
SKU velocity / ABC analysis, demand forecasting, picking productivity, slotting
optimization, and simulation.

## Project structure

```text
warehouse-optimization/
├── data/
│   ├── raw/georgia_tech/   # Original, unmodified source data (not committed)
│   └── processed/          # Cleaned, analysis-ready datasets (not committed)
├── notebooks/              # Analysis, modeling, and simulation notebooks
├── src/                    # Reusable Python modules, if needed
├── reports/                # Final reports and documentation
├── figures/                # Exported charts and visualizations
└── .venv/                  # Python virtual environment (not committed)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy pandas pyarrow scipy scikit-learn matplotlib seaborn altair jupyterlab
jupyter lab
```

### Data

The raw data is not stored in Git. Place the source files in `data/raw/georgia_tech/`:

- `SKUs.csv`
- `picks.csv`

See `data/raw/georgia_tech/README_source.html` for the dataset source.

## Conventions

1. Never modify files in `data/raw/`; write cleaned outputs to `data/processed/`.
2. Use project-relative paths (notebooks locate the project root automatically).
3. Document assumptions, transformations, and modeling decisions in the notebooks.
4. Keep real observations distinct from synthetic or simulated data.
5. Do not commit the virtual environment, large datasets, or credentials.
6. Create notebooks as they become necessary, numbered in order (`01_`, `02_`, ...).
