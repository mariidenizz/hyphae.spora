# SPORA

**Spora-Polymer Observation & Recovery Analysis**  
*Computational polymer degradation pipeline — Hyphae Composites*

---

SPORA is Hyphae's foundational research pipeline for understanding how mixed plastics degrade, interact, and recover in the presence of Hyphae's proprietary masterbatch additive. It uses **RDKit** for polymer cheminformatics and **OVITO** for molecular-scale visualization, and stores all experimental results in a shared **Supabase (PostgreSQL)** database.

> This is a forward-looking scientific tool — not tied to the kiosk. Outputs from SPORA will support future industrial partnerships and the summer showcase poster.

---

## Table of Contents

- [Supported Polymers](#supported-polymers)
- [Repository Structure](#repository-structure)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [Database](#database)
- [Contributing](#contributing)

---

## Supported Polymers

| Polymer | Class | Degradation Mechanisms |
|---------|-------|------------------------|
| PLA | Polyester | Hydrolysis, thermal |
| PETG | Polyester | Hydrolysis, glycolysis |
| ABS | ABS blend | Thermal, UV scission, thermo-oxidative |
| PP | Polyolefin | Thermal, thermo-oxidative |
| HDPE | Polyolefin | Thermo-oxidative |

---

## Repository Structure

```
hyphae.spora/
├── .env.example              ← copy to .env and fill in credentials
├── requirements.txt          ← pinned Python dependencies
├── Makefile                  ← common dev tasks
│
├── spora/                    ← main Python package
│   ├── config.py
│   ├── models/
│   │   ├── polymer.py
│   │   └── experiment.py
│   ├── rdkit_pipeline/
│   │   ├── smiles_builder.py
│   │   ├── degradation.py
│   │   └── descriptors.py
│   ├── ovito_pipeline/
│   │   ├── loader.py
│   │   └── renderer.py
│   └── db/
│       ├── schema.sql        ← apply once to Supabase to create all tables
│       ├── connection.py
│       └── queries.py
│
├── scripts/                  ← thin CLI wrappers
│   ├── ingest_polymer.py
│   ├── run_degradation.py
│   └── export_results.py
│
├── notebooks/                ← Jupyter exploration
├── tests/                    ← pytest suite
├── visualizations/           ← OVITO renders (git-ignored)
└── docs/                     ← extended docs and poster assets
```

---

## Setup

### 1. Prerequisites

- Python 3.11 or 3.12 (not 3.13 — OVITO bindings not yet compatible)
- Git 2.40+
- Conda or Mamba (for OVITO install)
- A psql client — `brew install libpq` on macOS

### 2. Clone the repo

```bash
git clone https://github.com/HyphaeComposites/hyphae.spora.git
cd hyphae.spora
```

### 3. Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ Never run `pip install <package>` directly. Add it to `requirements.txt` first, then reinstall — this keeps everyone's environment identical.

### 5. Install OVITO (via Conda)

```bash
conda create -n spora-ovito python=3.11
conda activate spora-ovito
conda install --channel conda-forge ovito
pip install -r requirements.txt
```

### 6. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials — ask Mariana for the Supabase keys.

```
SUPABASE_URL=https://whqsqxqmaksdptgevqos.supabase.co
SUPABASE_KEY=your-anon-key-here
DATABASE_URL=your-supabase-database-uri-here
OVITO_LICENSE_KEY=your-key-here
SPORA_DATA_DIR=/absolute/path/to/your/data/folder
LOG_LEVEL=DEBUG
```

> 🔒 `.env` is git-ignored. Never commit it. Never share it in Slack or email — use 1Password or ask Mariana directly.

### 7. Test your database connection

```bash
python -c "from spora.db.connection import get_conn; print(get_conn().status)"
# Expected: STATUS_READY
```

---

## Running the Pipeline

Use `make` for all common tasks:

| Command | What it does |
|---------|--------------|
| `make run-degradation` | Run the full RDKit degradation pipeline |
| `make run-ovito` | Execute the OVITO visualization pipeline |
| `make test` | Run the full pytest suite |
| `make lint` | Lint with ruff |
| `make format` | Format with black |
| `make export` | Export results to `data/exports/` as CSV + Parquet |
| `make notebook` | Launch Jupyter Lab |
| `make db-reset` | ⚠️ Drop and recreate all Supabase tables — coordinate with Mariana first |

### Example — run a degradation experiment

```bash
python scripts/run_degradation.py \
  --polymer PLA \
  --mechanism hydrolysis \
  --temperature 60 \
  --time-steps 10 \
  --masterbatch-concentration 0.02 \
  --output-label "pla_hydro_60c_2pct"
```

Results are written to the shared Supabase database and to `data/processed/pla_hydro_60c_2pct/`.

### Example — render a visualization

```bash
python scripts/run_ovito.py \
  --run-label "pla_hydro_60c_2pct" \
  --mode comparison \
  --output-dir visualizations/pla_hydro_60c_2pct/
```

| Mode | Output |
|------|--------|
| `single` | One frame of the final degraded state |
| `comparison` | Side-by-side: pristine vs degraded vs masterbatch-recovered |
| `timelapse` | Animated MP4 across all time steps |

---

## Database

SPORA uses a shared **Supabase (PostgreSQL 15)** database. All team members connect to the same project — no local Postgres needed.

### Tables

| Table | Purpose |
|-------|---------|
| `polymers` | Master registry of supported polymer families (pre-seeded) |
| `degradation_mechanisms` | Lookup table for reaction types (pre-seeded) |
| `experiments` | One row per pipeline run |
| `descriptors` | RDKit molecular descriptors per fragment per time step |
| `visualizations` | OVITO render metadata, linked to experiments |

### Applying the schema (first time only)

The schema is already applied to the Hyphae Supabase project. You only need to run this if setting up a brand new project:

```bash
psql "$DATABASE_URL" -f spora/db/schema.sql
```

### Browsing data

The fastest way to explore results is the **Supabase Table Editor** at [app.supabase.com](https://app.supabase.com) — no SQL needed. For custom queries, use the **SQL Editor** tab.

---

## Contributing

SPORA follows a branch-per-feature workflow.

```bash
# 1. Always start from a fresh main
git checkout main && git pull

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Commit in small logical units
git commit -m "feat: describe what this does"

# 4. Push and open a PR — assign to Mariana for review
git push -u origin feature/your-feature-name
```

Commit message prefixes: `feat:` `fix:` `docs:` `refactor:` `test:`

Run `make lint && make format` before every commit.

---

## Contact

| Question about… | Who to ask |
|-----------------|------------|
| RDKit logic, OVITO, science | Mariana |
| Bugs or missing features | Open a GitHub Issue |
| Setup or credentials | Mariana |

---

*Hyphae Composites — Internal Research Tool — Confidential*
