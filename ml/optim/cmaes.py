"""Minimal CMA-ES (pure NumPy), enough for ~10-50 dim black-box tuning.

Standard (mu/mu_w, lambda)-CMA-ES with rank-mu + rank-one covariance update and
cumulative step-size adaptation (Hansen 2016 tutorial notation). Works in the
unit cube [0,1]^d; the caller maps genes <-> engine params (see ml/spec.py).
Bound handling is a simple reflect-into-box on ``ask``.

If you have the real thing installed (``pip install cma``) prefer it; this is a
dependency-free fallback so the pipeline runs out of the box.

    opt = CMAES(dim=14, x0=0.5, sigma0=0.25, seed=0)
    while not opt.stop():
        xs = opt.ask()
        fs = [objective(x) for x in xs]      # MINIMISED
        opt.tell(xs, fs)
    x_best, f_best = opt.best
"""
from __future__ import annotations

import numpy as np


def _reflect(x: np.ndarray) -> np.ndarray:
    """Fold x back into [0,1] by reflection (handles multi-wrap)."""
    y = np.mod(x, 2.0)
    return np.where(y > 1.0, 2.0 - y, y)


class CMAES:
    def __init__(self, dim, x0=0.5, sigma0=0.25, popsize=None, seed=0,
                 maxiter=60):
        self.dim = int(dim)
        self.rng = np.random.default_rng(seed)
        self.mean = np.full(self.dim, float(x0)) if np.isscalar(x0) else np.asarray(x0, float).copy()
        self.sigma = float(sigma0)
        self.lam = int(popsize or (4 + int(3 * np.log(self.dim))))
        self.mu = self.lam // 2
        w = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.w = w / w.sum()
        self.mueff = 1.0 / np.sum(self.w ** 2)
        n = self.dim
        self.cc = (4 + self.mueff / n) / (n + 4 + 2 * self.mueff / n)
        self.cs = (self.mueff + 2) / (n + self.mueff + 5)
        self.c1 = 2 / ((n + 1.3) ** 2 + self.mueff)
        self.cmu = min(1 - self.c1,
                       2 * (self.mueff - 2 + 1 / self.mueff) / ((n + 2) ** 2 + self.mueff))
        self.damps = 1 + 2 * max(0, np.sqrt((self.mueff - 1) / (n + 1)) - 1) + self.cs
        self.pc = np.zeros(n)
        self.ps = np.zeros(n)
        self.C = np.eye(n)
        self.chiN = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))
        self.iter = 0
        self.maxiter = int(maxiter)
        self.best = (self.mean.copy(), np.inf)
        self._raw = None

    def ask(self) -> list[np.ndarray]:
        d, B = np.linalg.eigh(self.C)
        d = np.sqrt(np.clip(d, 1e-14, None))
        self._BD = B * d
        z = self.rng.standard_normal((self.lam, self.dim))
        y = z @ self._BD.T
        raw = self.mean[None, :] + self.sigma * y
        self._raw = raw
        return [_reflect(r) for r in raw]

    def tell(self, xs, fs):
        fs = np.asarray(fs, float)
        raw = self._raw if self._raw is not None else np.asarray(xs, float)
        idx = np.argsort(fs)
        if fs[idx[0]] < self.best[1]:
            self.best = (_reflect(raw[idx[0]]).copy(), float(fs[idx[0]]))
        sel = raw[idx[:self.mu]]
        old_mean = self.mean.copy()
        self.mean = self.w @ sel
        y_w = (self.mean - old_mean) / self.sigma
        Cinv_sqrt = self._C_invsqrt()
        self.ps = ((1 - self.cs) * self.ps
                   + np.sqrt(self.cs * (2 - self.cs) * self.mueff) * (Cinv_sqrt @ y_w))
        hsig = (np.linalg.norm(self.ps)
                / np.sqrt(1 - (1 - self.cs) ** (2 * (self.iter + 1)))
                / self.chiN) < (1.4 + 2 / (self.dim + 1))
        self.pc = ((1 - self.cc) * self.pc
                   + (1.0 if hsig else 0.0) * np.sqrt(self.cc * (2 - self.cc) * self.mueff) * y_w)
        ys = (sel - old_mean) / self.sigma
        rank_mu = (ys * self.w[:, None]).T @ ys
        self.C = ((1 - self.c1 - self.cmu) * self.C
                  + self.c1 * (np.outer(self.pc, self.pc)
                               + (0.0 if hsig else self.cc * (2 - self.cc)) * self.C)
                  + self.cmu * rank_mu)
        self.sigma *= np.exp((self.cs / self.damps) * (np.linalg.norm(self.ps) / self.chiN - 1))
        self.sigma = float(np.clip(self.sigma, 1e-6, 1e3))
        self.iter += 1

    def _C_invsqrt(self):
        d, B = np.linalg.eigh(self.C)
        d = np.clip(d, 1e-14, None)
        return B @ np.diag(1.0 / np.sqrt(d)) @ B.T

    def stop(self) -> bool:
        return self.iter >= self.maxiter or self.sigma < 1e-5

    # --- convenience for checkpointing ---
    def state(self):
        return {
            "mean": self.mean.tolist(), "sigma": self.sigma,
            "pc": self.pc.tolist(), "ps": self.ps.tolist(),
            "C": self.C.tolist(), "iter": self.iter,
            "best_x": self.best[0].tolist(), "best_f": self.best[1],
        }

    def load(self, s):
        self.mean = np.asarray(s["mean"], float)
        self.sigma = float(s["sigma"])
        self.pc = np.asarray(s["pc"], float)
        self.ps = np.asarray(s["ps"], float)
        self.C = np.asarray(s["C"], float)
        self.iter = int(s["iter"])
        self.best = (np.asarray(s["best_x"], float), float(s["best_f"]))
