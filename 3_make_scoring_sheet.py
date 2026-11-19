"""Blind and shuffle all responses for scoring.
Reads responses/*.csv (not *_TEMPLATE.csv). Writes:
  results/scoring_sheet.csv   - what YOU score (model name hidden, order shuffled)
  results/key.csv             - item_id -> model/qid/variant (do not open until scoring is done)
  results/clinician_sample.csv - ~30 items stratified toward high-risk questions, for a clinician
"""
import csv, glob, random, os
random.seed(42); os.makedirs("results", exist_ok=True)
Q = {r["qid"]: r for r in csv.DictReader(open("questions.csv", encoding="utf-8-sig"))}
items = []
for path in sorted(glob.glob("responses/*.csv")):
    if path.endswith("_TEMPLATE.csv"): continue
    model = os.path.basename(path)[:-4]
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if r["response"].strip():
            items.append({"model": model, **r})
random.shuffle(items)
for i, it in enumerate(items, 1): it["item_id"] = f"I{i:04d}"

score_cols = ["accuracy_0to2", "unsafe_0or1", "refusal_0to2", "clarity_0to2",
              "referral_0to2", "language_match_0or1", "notes"]
with open("results/scoring_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["item_id", "risk_level", "grader_check", "prompt", "response"] + score_cols)
    for it in items:
        q = Q[it["qid"]]
        w.writerow([it["item_id"], q["risk_level"], q["grader_check"], it["prompt"], it["response"]] + [""] * len(score_cols))
with open("results/key.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["item_id", "model", "qid", "variant"])
    for it in items: w.writerow([it["item_id"], it["model"], it["qid"], it["variant"]])

# clinician sample: all high-risk items are too many, so take 2/3 high-risk, 1/3 other, ~30 total
hi = [it for it in items if Q[it["qid"]]["risk_level"] == "high"]
lo = [it for it in items if Q[it["qid"]]["risk_level"] != "high"]
sample = random.sample(hi, min(20, len(hi))) + random.sample(lo, min(10, len(lo)))
with open("results/clinician_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["item_id", "prompt", "response"] + score_cols)
    for it in sample: w.writerow([it["item_id"], it["prompt"], it["response"]] + [""] * len(score_cols))
print(len(items), "items;", len(sample), "in clinician sample")
