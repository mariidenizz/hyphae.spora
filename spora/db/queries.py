"""
spora/db/queries.py
-------------------
All database read/write functions for SPORA experiments.
Use these functions rather than writing raw SQL in pipeline code —
they handle connection management and error cases consistently.

Available functions:
    get_polymer(name)               → fetch a polymer record by name
    get_mechanism(code)             → fetch a degradation mechanism by code
    insert_experiment(meta)         → create a new experiment row
    insert_descriptors_batch(df)    → bulk-insert descriptor rows (fast)
    get_run_summary(label)          → aggregated stats for a run
    compare_runs(label_a, label_b)  → descriptor delta between two runs
    get_latest_runs(n)              → most recently completed experiments
"""

import io
import pandas as pd
from spora.db.connection import get_conn


def get_polymer(name: str) -> dict:
    """
    Fetch a polymer record by its short name (e.g. 'PLA', 'PETG').
    Returns a dict with all columns, or raises ValueError if not found.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM polymers WHERE name = %s", (name,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Polymer '{name}' not found in database. Check polymers table.")
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))


def get_mechanism(code: str) -> dict:
    """
    Fetch a degradation mechanism record by its short code (e.g. 'hydrolysis').
    Returns a dict with all columns, or raises ValueError if not found.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM degradation_mechanisms WHERE code = %s", (code,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Mechanism '{code}' not found in database. Check degradation_mechanisms table.")
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))


def insert_experiment(meta: dict) -> int:
    """
    Create a new experiment row and return its auto-generated id.

    meta must include:
        label, polymer_id, mechanism_id, temperature_c, time_steps,
        rdkit_version, git_sha, run_by
    Optional:
        masterbatch_pct, chain_length_n, notes
    """
    conn = get_conn()
    sql = """
        INSERT INTO experiments
            (label, polymer_id, mechanism_id, temperature_c, time_steps,
             masterbatch_pct, chain_length_n, rdkit_version, git_sha, run_by, notes)
        VALUES
            (%(label)s, %(polymer_id)s, %(mechanism_id)s, %(temperature_c)s,
             %(time_steps)s, %(masterbatch_pct)s, %(chain_length_n)s,
             %(rdkit_version)s, %(git_sha)s, %(run_by)s, %(notes)s)
        RETURNING id
    """
    with conn.cursor() as cur:
        cur.execute(sql, meta)
        experiment_id = cur.fetchone()[0]
    conn.commit()
    return experiment_id


def insert_descriptors_batch(df: pd.DataFrame) -> None:
    """
    Bulk-insert a DataFrame of descriptor rows using PostgreSQL COPY.
    This is ~100x faster than inserting rows one at a time.

    df must have columns matching the descriptors table:
        experiment_id, time_step, molecule_idx, smiles, mol_weight,
        num_rings, num_hbd, num_hba, logp, tpsa, num_rot_bonds,
        num_stereo_centers, chain_length
    """
    conn = get_conn()
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    with conn.cursor() as cur:
        cur.copy_expert(
            """COPY descriptors (experiment_id, time_step, molecule_idx, smiles,
               mol_weight, num_rings, num_hbd, num_hba, logp, tpsa,
               num_rot_bonds, num_stereo_centers, chain_length)
               FROM STDIN WITH CSV""",
            buffer,
        )
    conn.commit()


def _query_to_df(sql: str, params: tuple) -> pd.DataFrame:
    """
    Execute a SELECT query using psycopg2 and return results as a DataFrame.
    Avoids pd.read_sql() which pulls in sqlite3 and conflicts with Conda environments.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=cols)


def get_run_summary(label: str) -> pd.DataFrame:
    """
    Return aggregated molecular descriptor statistics for a completed run.
    Useful for quickly checking whether an experiment produced sensible results.
    """
    sql = """
        SELECT
            d.time_step,
            COUNT(*)                    AS fragment_count,
            AVG(d.mol_weight)           AS avg_mol_weight,
            AVG(d.chain_length)         AS avg_chain_length,
            AVG(d.logp)                 AS avg_logp,
            AVG(d.tpsa)                 AS avg_tpsa
        FROM descriptors d
        JOIN experiments e ON e.id = d.experiment_id
        WHERE e.label = %s
        GROUP BY d.time_step
        ORDER BY d.time_step
    """
    return _query_to_df(sql, (label,))


def compare_runs(label_a: str, label_b: str) -> pd.DataFrame:
    """
    Return a side-by-side descriptor comparison between two experiment runs.
    Useful for seeing whether the masterbatch additive changed degradation behaviour.
    """
    summary_a = get_run_summary(label_a).add_suffix(f"_{label_a}")
    summary_b = get_run_summary(label_b).add_suffix(f"_{label_b}")
    return summary_a.join(summary_b, how="outer")


def get_latest_runs(n: int = 10) -> pd.DataFrame:
    """Return the n most recently completed experiments as a DataFrame."""
    sql = """
        SELECT e.label, p.name AS polymer, dm.code AS mechanism,
               e.temperature_c, e.masterbatch_pct, e.status, e.finished_at
        FROM experiments e
        JOIN polymers p ON p.id = e.polymer_id
        JOIN degradation_mechanisms dm ON dm.id = e.mechanism_id
        WHERE e.status = 'completed'
        ORDER BY e.finished_at DESC
        LIMIT %s
    """
    return _query_to_df(sql, (n,))