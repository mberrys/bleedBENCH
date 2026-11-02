import numpy as np

from bleedbench.harness import stats as ST


def test_cp_matches_spec_numbers():
    assert abs(ST.cp_upper(0, 48) - 0.0605) < 0.001        # v1: 0 severe in 48 pages ~6.1%
    assert abs(ST.cp_upper(0, 11) - 0.238) < 0.001         # v1 sealed test: 23.8%
    assert ST.cp_upper(0, 299) <= 0.01 < ST.cp_upper(0, 298)
    assert abs(ST.cp_de_upper(0, 703, 2.35) - ST.cp_upper(0, 703 / 2.35)) < 1e-12


def test_icc_recovers_known_value():
    rng = np.random.default_rng(0)
    g = np.repeat(np.arange(400), 10)
    v = rng.normal(0, np.sqrt(0.3), 400)[g] + rng.normal(0, np.sqrt(0.7), g.size)
    icc, m = ST.icc_oneway(v, g)
    assert abs(icc - 0.3) < 0.05 and m == 10
    assert abs(ST.design_effect(0.05, 3.25) - 1.1125) < 1e-9


def test_bootstrap_paired_draws_and_few_cluster():
    v = np.arange(20.0)
    c = np.repeat(np.arange(10), 2)
    a = ST.cluster_bootstrap(v, c, seed=1)
    b = ST.cluster_bootstrap(v + 1, c, seed=1)
    assert abs((b["ci95"][0] - a["ci95"][0]) - 1) < 1e-9     # same draws -> paired
    assert a["few_cluster"] and a["n_families"] == 10
