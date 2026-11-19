"""Usage: python 1_make_prompts.py [--high-risk] [model names to paste by hand]
Turn questions.csv into one prompt per row (30 questions x 4 variants = 120 prompts).
Outputs:
  prompts.csv                   - long format, for the API script
  responses/<model>_TEMPLATE.csv - paste-sheets for models you run by hand (ChatGPT, Gemini)
"""
import csv, os, sys
VARIANTS = ["standard_en", "simple_en", "malayalam", "manglish"]
HIGH_RISK_ONLY = "--high-risk" in sys.argv          # use only questions tagged risk_level=high
MANUAL_MODELS = [a for a in sys.argv[1:] if a != "--high-risk"]   # optional: models you will paste by hand

rows = list(csv.DictReader(open("questions.csv", encoding="utf-8-sig")))
if HIGH_RISK_ONLY:
    rows = [r for r in rows if r["risk_level"] == "high"]
prompts = [{"qid": r["qid"], "variant": v, "prompt": r[v]} for r in rows for v in VARIANTS]

with open("prompts.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["qid", "variant", "prompt"]); w.writeheader(); w.writerows(prompts)

os.makedirs("responses", exist_ok=True)
for m in MANUAL_MODELS:
    with open(f"responses/{m}_TEMPLATE.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["qid", "variant", "prompt", "response"]); w.writeheader()
        for p in prompts: w.writerow({**p, "response": ""})
print(f"{len(prompts)} prompts written." + (" Fill responses/<model>_TEMPLATE.csv and rename to <model>.csv" if MANUAL_MODELS else ""))
