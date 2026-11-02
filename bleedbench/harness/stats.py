"""Statistics (SPEC §10): exact one-sided bounds, design effects, family-cluster bootstrap."""
from __future__ import annotations

import numpy as np
from scipy.stats import beta

FEW_CLUSTERS = 30


def cp_upper(x: float, n: float, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound; x, n may be design-effect-scaled (CP-DE)."""
    if n <= 0:
        return 1.0
    if x >= n:
        return 1.0
    return float(beta.ppf(conf, x + 1, n - x))


def cp_de_upper(x: int, n: int, de: float, conf: float = 0.95) -> float:
    return cp_upper(x / de, n / de, conf)


def icc_oneway(values: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    """ANOVA ICC(1) and mean cluster size. Returns (icc, m_bar)."""
    values = np.asarray(values, float)
    uniq, inv = np.unique(groups, return_inverse=True)
    k = len(uniq)
    n = len(values)
    if k < 2 or n <= k:
        return float("nan"), float(n / max(k, 1))
    sizes = np.bincount(inv)
    means = np.bincount(inv, weights=values) / sizes
    grand = values.mean()
    ssb = (sizes * (means - grand) ** 2).sum()
    ssw = ((values - means[inv]) ** 2).sum()
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - (sizes ** 2).sum() / n) / (k - 1)
    icc = (msb - msw) / (msb + (n0 - 1) * msw) if (msb + (n0 - 1) * msw) > 0 else 0.0
    return float(max(0.0, icc)), float(sizes.mean())


def design_effect(icc: float, m_bar: float) -> float:
    return 1 + (m_bar - 1) * icc


def cluster_bootstrap(values: np.ndarray, clusters: np.ndarray, n_boot: int = 2000, seed: int = 0,
                      weights: np.ndarray | None = None) -> dict:
    """Mean with a cluster (family) percentile bootstrap 95% CI. Same seed => same draws, so
    two methods evaluated on the same units get paired resamples."""
    values = np.asarray(values, float)
    w = np.ones_like(values) if weights is None else np.asarray(weights, float)
    uniq, inv = np.unique(clusters, return_inverse=True)
    k = len(uniq)
    sw = np.bincount(inv, weights=w * values, minlength=k)
    ww = np.bincount(inv, weights=w, minlength=k)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, k, (n_boot, k))
    bs = sw[draws].sum(1) / ww[draws].sum(1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"mean": float(sw.sum() / ww.sum()), "ci95": [float(lo), float(hi)], "n_families": int(k),
            "few_cluster": bool(k < FEW_CLUSTERS)}
