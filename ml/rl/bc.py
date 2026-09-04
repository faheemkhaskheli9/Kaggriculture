"""Behavior-clone unit intents from replay files into a linear softmax policy."""
from __future__ import annotations
import argparse, gzip, json
from pathlib import Path
import numpy as np
from ml.rl.encode import GLOBAL_NAMES, UNIT_NAMES, encode_policy_rows
from ml.rl.hybrid_action import N_INTENT, infer_intent

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"

def _label_for(steps, step_i, seat, unit_i, action, lookahead=12):
    """Movement inherits the task eventually executed by this unit.

    Hand order is stable within a day. We never cross a day boundary because
    hands are recreated/reordered at dawn.
    """
    if _op(action) not in MOVES:
        return infer_intent(action)
    last = min(len(steps), step_i + lookahead + 1, ((step_i // 24) + 1) * 24)
    for future_i in range(step_i + 1, last):
        state = steps[future_i][seat]
        future = state.get("action") or {}
        acts = [future.get("farmer", ["PASS"])] + list(future.get("hands", []) or [])
        if unit_i >= len(acts): break
        op = _op(acts[unit_i])
        if op in MOVES or op == "PASS": continue
        return infer_intent(acts[unit_i])
    return infer_intent(action)

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
            steps = _load(path).get("steps", [])
            for si, pair in enumerate(steps[:-1]):
                if si % max(1, every): continue
                for seat, state in enumerate(pair):
                    obs, action = state.get("observation"), state.get("action")
                    if not isinstance(obs, dict) or not isinstance(action, dict): continue
                    obs = dict(obs); obs["player"] = seat
                    try: rows = encode_policy_rows(obs)
                    except Exception: continue
                    acts = [action.get("farmer", ["PASS"])] + list(action.get("hands", []) or [])
                    for unit_i, (row, act) in enumerate(zip(rows, acts)):
                        X.append(row); y.append(_label_for(steps, si, seat, unit_i, act)); groups.append(gi)
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
    # Sqrt balancing avoids letting a handful of BUILD examples dominate every
    # gradient while still giving rare actionable intents useful weight.
    cw = np.sqrt(counts.sum() / np.maximum(1., N_INTENT * counts))
    cw = np.minimum(cw, 4.0)
    W = np.zeros((N_INTENT, X.shape[1])); b = np.zeros(N_INTENT); idx = np.flatnonzero(tr)
    mW=np.zeros_like(W); vW=np.zeros_like(W); mb=np.zeros_like(b); vb=np.zeros_like(b); tick=0
    for ep in range(epochs):
        rng.shuffle(idx)
        for start in range(0, len(idx), 2048):
            ii = idx[start:start+2048]; xb, yy = X[ii], y[ii]
            z = xb @ W.T + b; z -= z.max(1, keepdims=True)
            p = np.exp(z); p /= p.sum(1, keepdims=True); p[np.arange(len(ii)), yy] -= 1
            p *= cw[yy, None]; gW=(p.T@xb)/len(ii) + 1e-4*W; gb=p.mean(0); tick += 1
            mW=.9*mW+.1*gW; vW=.999*vW+.001*gW*gW; mb=.9*mb+.1*gb; vb=.999*vb+.001*gb*gb
            W -= lr*(mW/(1-.9**tick))/(np.sqrt(vW/(1-.999**tick))+1e-8)
            b -= lr*(mb/(1-.9**tick))/(np.sqrt(vb/(1-.999**tick))+1e-8)
        at = np.mean(np.argmax(X[tr]@W.T+b, 1) == y[tr])
        av = np.mean(np.argmax(X[va]@W.T+b, 1) == y[va]) if va.any() else 0
        pv=np.argmax(X[va]@W.T+b,1) if va.any() else np.array([],dtype=int)
        recalls=[np.mean(pv[y[va]==k]==k) for k in range(N_INTENT) if np.any(y[va]==k)]
        bal=float(np.mean(recalls)) if recalls else 0
        print(f"epoch {ep+1:02d} train={at:.3f} val={av:.3f} balanced={bal:.3f}")
    return W, b, tr, va

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--replays", default="replays")
    ap.add_argument("--out", default="intent_model.json"); ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--lr", type=float, default=.08); ap.add_argument("--every", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--confidence", type=float, default=.55)
    ap.add_argument("--seed", type=int, default=0); a = ap.parse_args()
    X,y,g = build_rows(a.replays,a.every,a.limit)
    print(f"rows={len(y)} replays={len(np.unique(g))} features={X.shape[1]} "
          f"classes={dict(enumerate(np.bincount(y,minlength=N_INTENT).tolist()))}")
    W,b,tr,va=train(X,y,g,a.epochs,a.lr,a.seed)
    data={"format":"kagri-intent-linear-v1","feature_names":list(GLOBAL_NAMES)+list(UNIT_NAMES),
          "weights":W.tolist(),"bias":b.tolist(),"confidence":a.confidence,
          "train_rows":int(tr.sum()),"validation_rows":int(va.sum())}
    Path(a.out).write_text(json.dumps(data,separators=(",",":")),encoding="utf-8"); print(f"wrote {a.out}")
if __name__ == "__main__": main()
