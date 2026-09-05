"""Episode-held-out benchmark for top-player strategic action imitation.

Uses a dependency-free categorical Naive Bayes model. The purpose is not to
declare this small model production-ready; it is to establish a leakage-safe
benchmark and reveal which strategic decisions are learnable from public state.

Usage:
    python tools/benchmark_top_policy.py
    python tools/benchmark_top_policy.py --dataset ml/artifacts/top_policy.jsonl
"""
import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_LABELS = ("HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL")


def bin_num(value, cuts):
    value = float(value or 0)
    for index, cut in enumerate(cuts):
        if value < cut:
            return str(index)
    return str(len(cuts))


def total(mapping):
    return sum((mapping or {}).values())


def features(row):
    farm = row["farm"]
    opponent = row["opponent"]
    prices = row.get("market_prices") or {}
    history = row.get("history") or {}
    counts = history.get("market_counts") or {}
    quantities = history.get("market_quantities") or {}
    since = history.get("turns_since") or {}
    return {
        "agent": row.get("agent", "UNKNOWN"),
        "day": bin_num(row["day"], (2, 5, 8, 12, 16, 21, 26, 29)),
        "hour": bin_num(row["hour"], (1, 4, 8, 12, 16, 20, 23)),
        "money": bin_num(row["money"], (50, 150, 400, 800, 1500, 3000, 6000, 12000, 25000, 50000)),
        "hands": bin_num(row["hands"], (2, 5, 8, 11, 14, 18)),
        "quadrants": str(row["quadrants"]),
        "plants": bin_num(total(farm["crops"]), (5, 15, 30, 50, 70)),
        "animals": bin_num(total(farm["animals"]), (1, 4, 8, 12, 16)),
        "empty": bin_num(farm["empty"], (3, 10, 20, 40)),
        "weeds": bin_num(farm["weeds"], (1, 5, 15, 30)),
        "opp_plants": bin_num(total(opponent["crops"]), (5, 15, 30, 50, 70)),
        "opp_animals": bin_num(total(opponent["animals"]), (1, 4, 8, 12, 16)),
        "shed": bin_num(total(row.get("shed")), (1, 10, 30, 60, 90)),
        "seeds": bin_num(total(row.get("seeds")), (1, 5, 15, 30)),
        "carried": bin_num(total(row.get("carried")), (1, 5, 15, 30)),
        "wheat_price": bin_num(prices.get("WHEAT"), (15, 22, 28, 40, 60)),
        "strawberry_price": bin_num(prices.get("STRAWBERRY"), (80, 120, 160, 220, 300)),
        "milk_price": bin_num(prices.get("MILK"), (100, 160, 220, 320)),
        "wool_price": bin_num(prices.get("WOOL"), (120, 200, 300, 450)),
        "shops": bin_num(len(row.get("town_shops") or []), (1, 3, 6, 9)),
        "hires_so_far": bin_num(counts.get("HIRE"), (5, 20, 50, 100, 180, 260)),
        "land_buys_so_far": str(min(3, int(counts.get("BUY_LAND", 0)))),
        "seed_units_so_far": bin_num(quantities.get("BUY_SEED"), (10, 40, 100, 250, 500, 900)),
        "animals_so_far": bin_num(quantities.get("BUY_ANIMAL"), (1, 4, 8, 12, 18)),
        "products_bought_so_far": bin_num(quantities.get("BUY_PRODUCT"),
                                           (5, 20, 60, 150, 300)),
        "sell_units_so_far": bin_num(quantities.get("SELL"), (10, 50, 150, 400, 800)),
        "since_hire": bin_num(since.get("HIRE", 999), (1, 2, 4, 8, 16, 24, 48)),
        "since_land": bin_num(since.get("BUY_LAND", 999), (1, 6, 24, 72, 144, 288)),
        "since_seed": bin_num(since.get("BUY_SEED", 999), (1, 2, 6, 12, 24, 48)),
        "since_animal": bin_num(since.get("BUY_ANIMAL", 999), (1, 4, 12, 24, 48, 96)),
        "since_product": bin_num(since.get("BUY_PRODUCT", 999), (1, 2, 6, 12, 24, 48)),
        "since_sell": bin_num(since.get("SELL", 999), (1, 2, 4, 8, 16, 24)),
        "previous_day_money": bin_num(history.get("previous_day_money"),
                                       (50, 150, 400, 800, 1500, 3000, 6000, 12000, 25000)),
        "previous_day_plants": bin_num(history.get("previous_day_plants"),
                                        (5, 15, 30, 50, 70)),
        "previous_day_animals": bin_num(history.get("previous_day_animals"),
                                         (1, 4, 8, 12, 16)),
    }


def labels(row):
    out = set()
    for order in row["labels"]["market_orders"]:
        op = order[0]
        if op in BASE_LABELS:
            out.add(op)
            if len(order) > 1 and op in {"BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL"}:
                out.add(f"{op}:{order[1]}")
    return out


class BinaryCategoricalNB:
    def __init__(self):
        self.class_counts = Counter()
        self.values = defaultdict(set)
        self.counts = {False: defaultdict(Counter), True: defaultdict(Counter)}

    def fit(self, examples, target):
        for row in examples:
            selected = target in row["_labels"]
            self.class_counts[selected] += 1
            for name, value in row["_features"].items():
                self.values[name].add(value)
                self.counts[selected][name][value] += 1

    def probability(self, values):
        total_rows = sum(self.class_counts.values())
        logp = {}
        for selected in (False, True):
            log_value = math.log((self.class_counts[selected] + 1) / (total_rows + 2))
            for name, value in values.items():
                width = len(self.values[name]) + 1
                numerator = self.counts[selected][name][value] + 1
                denominator = self.class_counts[selected] + width
                log_value += math.log(numerator / denominator)
            logp[selected] = log_value
        scale = max(logp.values())
        yes, no = math.exp(logp[True] - scale), math.exp(logp[False] - scale)
        return yes / (yes + no)


def f1(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, score


def best_threshold(model, calibration, target):
    scored = [(model.probability(row["_features"]), target in row["_labels"])
              for row in calibration]
    best = (0.0, 0.5)
    for integer in range(5, 96, 5):
        threshold = integer / 100
        tp = sum(prob >= threshold and actual for prob, actual in scored)
        fp = sum(prob >= threshold and not actual for prob, actual in scored)
        fn = sum(prob < threshold and actual for prob, actual in scored)
        score = f1(tp, fp, fn)[2]
        # Prefer the more conservative threshold when F1 ties.
        if score > best[0] or (score == best[0] and threshold > best[1]):
            best = (score, threshold)
    return best[1]


def evaluate(train, valid, target_labels):
    train_episodes = sorted({row["episode_id"] for row in train})
    calibration_ids = set(train_episodes[-max(1, len(train_episodes) // 5):])
    fit_rows = [row for row in train if row["episode_id"] not in calibration_ids]
    calibration = [row for row in train if row["episode_id"] in calibration_ids]
    models, thresholds = {}, {}
    for target in target_labels:
        calibration_model = BinaryCategoricalNB()
        calibration_model.fit(fit_rows, target)
        thresholds[target] = best_threshold(calibration_model, calibration, target)
        model = BinaryCategoricalNB()
        model.fit(train, target)
        models[target] = model

    stats = {target: Counter() for target in target_labels}
    exact = jaccard_sum = 0.0
    for row in valid:
        truth = row["_labels"] & set(target_labels)
        predicted = {target for target, model in models.items()
                     if model.probability(row["_features"]) >= thresholds[target]}
        exact += predicted == truth
        union = predicted | truth
        jaccard_sum += len(predicted & truth) / len(union) if union else 1.0
        for target in target_labels:
            actual, guess = target in truth, target in predicted
            stats[target]["tp" if actual and guess else
                          "fp" if guess else "fn" if actual else "tn"] += 1

    per_label = {}
    micro = Counter()
    for target, counts in stats.items():
        precision, recall, score = f1(counts["tp"], counts["fp"], counts["fn"])
        per_label[target] = {
            "support": counts["tp"] + counts["fn"], "precision": precision,
            "recall": recall, "f1": score, "threshold": thresholds[target],
        }
        micro.update({key: counts[key] for key in ("tp", "fp", "fn")})
    precision, recall, score = f1(micro["tp"], micro["fp"], micro["fn"])
    return {
        "rows": len(valid), "exact_set_accuracy": exact / len(valid),
        "mean_jaccard": jaccard_sum / len(valid), "micro_precision": precision,
        "micro_recall": recall, "micro_f1": score, "per_label": per_label,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="ml/artifacts/top_policy.jsonl")
    parser.add_argument("--output", default="ml/artifacts/top_policy_benchmark.json")
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--split-seed", type=int, default=20260905)
    args = parser.parse_args()

    rows = []
    with (ROOT / args.dataset).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            row["_features"] = features(row)
            row["_labels"] = labels(row)
            rows.append(row)
    episodes = sorted({row["episode_id"] for row in rows})
    rng = random.Random(args.split_seed)
    rng.shuffle(episodes)
    count = max(1, round(len(episodes) * args.validation_fraction))
    valid_episodes = set(episodes[:count])
    train = [row for row in rows if row["episode_id"] not in valid_episodes]
    valid = [row for row in rows if row["episode_id"] in valid_episodes]

    detailed = sorted({label for row in rows for label in row["_labels"]})
    report = {
        "dataset": args.dataset, "split_seed": args.split_seed,
        "train_episodes": sorted(set(episodes) - valid_episodes),
        "validation_episodes": sorted(valid_episodes),
        "train_rows": len(train), "validation_rows": len(valid),
        "family": evaluate(train, valid, list(BASE_LABELS)),
        "detailed": evaluate(train, valid, detailed),
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    concise = {
        "train_episodes": len(report["train_episodes"]),
        "validation_episodes": len(report["validation_episodes"]),
        "train_rows": len(train), "validation_rows": len(valid),
        "family": {key: report["family"][key] for key in
                   ("exact_set_accuracy", "mean_jaccard", "micro_precision",
                    "micro_recall", "micro_f1")},
        "family_per_label": report["family"]["per_label"],
        "detailed_micro_f1": report["detailed"]["micro_f1"],
        "output": args.output,
    }
    print(json.dumps(concise, indent=2))


if __name__ == "__main__":
    main()
