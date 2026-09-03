"""Behavior-clone unit intents from replay files into a linear softmax policy."""
from __future__ import annotations
import argparse, gzip, json
from pathlib import Path
import numpy as np
from ml.rl.encode import GLOBAL_NAMES, UNIT_NAMES, encode_policy_rows
from ml.rl.hybrid_action import N_INTENT, infer_intent

def _files(root):
    root = Path(root)
    yield from root.rglob("*.replay.json.gz")
    yield from root.rglob("episode-*-replay.json")

def _load(path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)

def build_rows(root, every=2, limit=0):
    X, y, groups = [], [], []
    for gi, path in enumerate(_files(root)):
        if limit and gi >= limit: break
        try:
            for si, pair in enumerate(_load(path).get("steps", [])[:-1]):
                if si % max(1, every): continue
                for seat, state in enumerate(pair):
                    obs, action = state.get("observation"), state.get("action")
                    if not isinstance(obs, dict) or not isinstance(action, dict): continue
                    obs = dict(obs); obs["player"] = seat
                    try: rows = encode_policy_rows(obs)
                    except Exception: continue
                    acts = [action.get("farmer", ["PASS"])] + list(action.get("hands", []) or [])
                    for row, act in zip(rows, acts):
                        X.append(row); y.append(infer_intent(act)); groups.append(gi)
        except Exception as exc:
            print(f"skip {path}: {exc}")
    if not X: raise SystemExit("no training rows found")
    return np.asarray(X, np.float32), np.asarray(y, np.int64), np.asarray(groups)

def train(X, y, groups, epochs=25, lr=.08, seed=0):
    rng = np.random.default_rng(seed); unique = np.unique(groups); rng.shuffle(unique)
    if len(unique) >= 2:
        vg = set(unique[:max(1, len(unique)//5)].tolist())
        va = np.asarray([g in vg for g in groups]); tr = ~va
    else:
        order = rng.permutation(len(y)); cut = max(1, int(.8*len(y)))
        tr = np.zeros(len(y), dtype=bool); tr[order[:cut]] = True; va = ~tr
    counts = np.bincount(y[tr], minlength=N_INTENT).astype(float)
    cw = counts.sum() / np.maximum(1., N_INTENT * counts)
    W = np.zeros((N_INTENT, X.shape[1])); b = np.zeros(N_INTENT); idx = np.flatnonzero(tr)
    for ep in range(epochs):
        rng.shuffle(idx)
        for start in range(0, len(idx), 2048):
            ii = idx[start:start+2048]; xb, yy = X[ii], y[ii]
            z = xb @ W.T + b; z -= z.max(1, keepdims=True)
            p = np.exp(z); p /= p.sum(1, keepdims=True); p[np.arange(len(ii)), yy] -= 1
            p *= cw[yy, None]; W -= lr*((p.T@xb)/len(ii) + 1e-4*W); b -= lr*p.mean(0)
        at = np.mean(np.argmax(X[tr]@W.T+b, 1) == y[tr])
        av = np.mean(np.argmax(X[va]@W.T+b, 1) == y[va]) if va.any() else 0
        print(f"epoch {ep+1:02d} train={at:.3f} val={av:.3f}")
    return W, b, tr, va

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--replays", default="replays")
    ap.add_argument("--out", default="intent_model.json"); ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--lr", type=float, default=.08); ap.add_argument("--every", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--confidence", type=float, default=.55)
    ap.add_argument("--seed", type=int, default=0); a = ap.parse_args()
    X,y,g = build_rows(a.replays,a.every,a.limit); print(f"rows={len(y)} replays={len(np.unique(g))} features={X.shape[1]}")
    W,b,tr,va=train(X,y,g,a.epochs,a.lr,a.seed)
    data={"format":"kagri-intent-linear-v1","feature_names":list(GLOBAL_NAMES)+list(UNIT_NAMES),
          "weights":W.tolist(),"bias":b.tolist(),"confidence":a.confidence,
          "train_rows":int(tr.sum()),"validation_rows":int(va.sum())}
    Path(a.out).write_text(json.dumps(data,separators=(",",":")),encoding="utf-8"); print(f"wrote {a.out}")
if __name__ == "__main__": main()
