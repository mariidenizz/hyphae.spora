"""
tests/test_rdkit_pipeline.py
-----------------------------
Tests for the RDKit cheminformatics pipeline.

As you implement each function in spora/rdkit_pipeline/,
add a corresponding test here. Run with: make test

A good test checks one specific thing and has a clear name that
explains what it is testing. If a test fails, the name alone should
tell you what broke.
"""

from rdkit import Chem
from spora.rdkit_pipeline.smiles_builder import build_polymer_smiles
from spora.rdkit_pipeline.descriptors import compute_descriptors


# -----------------------------------------------------------------------------
# smiles_builder tests
# -----------------------------------------------------------------------------

def test_build_polymer_smiles_returns_string():
    """build_polymer_smiles should always return a non-empty string."""
    result = build_polymer_smiles("CC(OC(=O)O)", n_repeat=10)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_polymer_smiles_is_valid_rdkit_mol():
    """The SMILES returned by build_polymer_smiles should parse into a valid RDKit molecule."""
    smiles = build_polymer_smiles("CC(OC(=O)O)", n_repeat=10)
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"RDKit could not parse SMILES: {smiles}"


def test_build_polymer_smiles_invalid_input_raises():
    """build_polymer_smiles should raise ValueError when given an invalid SMILES string."""
    import pytest
    with pytest.raises(ValueError):
        build_polymer_smiles("not_a_smiles!!!", n_repeat=5)


# -----------------------------------------------------------------------------
# descriptors tests
# -----------------------------------------------------------------------------

def test_compute_descriptors_returns_dataframe():
    """compute_descriptors should return a pandas DataFrame."""
    import pandas as pd
    mol = Chem.MolFromSmiles("CC(=O)O")  # acetic acid — simple test molecule
    df = compute_descriptors([mol], experiment_id=1, time_step=0)
    assert isinstance(df, pd.DataFrame)


def test_compute_descriptors_correct_columns():
    """compute_descriptors DataFrame should contain all expected descriptor columns."""
    mol = Chem.MolFromSmiles("CC(=O)O")
    df = compute_descriptors([mol], experiment_id=1, time_step=0)
    expected_columns = [
        "experiment_id", "time_step", "molecule_idx", "smiles",
        "mol_weight", "num_rings", "num_hbd", "num_hba",
        "logp", "tpsa", "num_rot_bonds", "num_stereo_centers", "chain_length"
    ]
    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"


def test_compute_descriptors_mol_weight_is_positive():
    """Molecular weight should always be a positive number."""
    mol = Chem.MolFromSmiles("CC(=O)O")
    df = compute_descriptors([mol], experiment_id=1, time_step=0)
    assert df["mol_weight"].iloc[0] > 0


def test_compute_descriptors_skips_none_molecules():
    """None molecules in the input list should be silently skipped."""
    mol = Chem.MolFromSmiles("CC(=O)O")
    df = compute_descriptors([mol, None, mol], experiment_id=1, time_step=0)
    assert len(df) == 2  # only the two valid molecules