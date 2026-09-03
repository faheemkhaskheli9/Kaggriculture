"""Quasi-random search over the unit cube -- a cheap Phase-1 baseline and a
sanity check that CMA-ES is actually earning its keep.

Uses a Sobol sequence when SciPy is present, else plain uniform sampling.
"""
from __future__ import annotations

import numpy as np

try:
    from scipy.stats.qmc import Sobol
    _HAVE_SOBOL = True
except Exception:  # pragma: no cover
    _HAVE_SOBOL = False


class RandomSearch:
    def __init__(self, dim, popsize=16, seed=0, maxiter=20, include_center=True):
        self.dim = int(dim)
        self.lam = int(popsize)
        self.maxiter = int(maxiter)
        self.iter = 0
        self.rng = np.random.default_rng(seed)
        self._sobol = Sobol(d=self.dim, scramble=True, seed=seed) if _HAVE_SOBOL else None
        self._center_pending = include_center
        self.best = (np.full(self.dim, 0.5), np.inf)

    def ask(self):
        if self._sobol is not None:
            pts = self._sobol.random(self.lam)
        else:
            pts = self.rng.random((self.lam, self.dim))
        pts = list(pts)
        if self._center_pending:
            pts[0] = np.full(self.dim, 0.5)
            self._center_pending = False
        return [np.clip(p, 0.0, 1.0) for p in pts]

    def tell(self, xs, fs):
        for x, f in zip(xs, fs):
            if f < self.best[1]:
                self.best = (np.asarray(x, float).copy(), float(f))
        self.iter += 1

    def stop(self):
        return self.iter >= self.maxiter

    def state(self):
        return {"iter": self.iter, "best_x": self.best[0].tolist(), "best_f": self.best[1]}

    def load(self, s):
        self.iter = int(s["iter"])
        self.best = (np.asarray(s["best_x"], float), float(s["best_f"]))
