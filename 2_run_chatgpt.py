"""Run all prompts through an OpenAI model via the API (no system prompt, one prompt per call).
Usage: OPENAI_API_KEY=... python 2_run_chatgpt.py <model-name>
Copy the exact model name from OpenAI's models page; names change over time.
Saves responses/chatgpt.csv. Re-running resumes and skips finished rows.
"""
import csv, os, sys, time, datetime
from openai import OpenAI

if len(sys.argv) < 2:
    sys.exit("Give the model name, e.g. python 2_run_chatgpt.py <model-name>")
MODEL = sys.argv[1]
MAX_TOKENS = 2000   # same cap in all three scripts; leaves room for models that "think" first
OUT = "responses/chatgpt.csv"

prompts = list(csv.DictReader(open("prompts.csv", encoding="utf-8-sig")))
done = {}
if os.path.exists(OUT):
    done = {(r["qid"], r["variant"]): r for r in csv.DictReader(open(OUT, encoding="utf-8-sig"))}

client = OpenAI()
fields = ["qid", "variant", "prompt", "response", "model", "finish_reason", "timestamp"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    for p in prompts:
        key = (p["qid"], p["variant"])
        if key in done and done[key]["response"]:
            w.writerow(done[key]); continue
        text, finish = "", "error"
        for attempt in range(3):
            try:
                r = client.chat.completions.create(
                    model=MODEL, max_completion_tokens=MAX_TOKENS,
                    messages=[{"role": "user", "content": p["prompt"]}])
                text = r.choices[0].message.content or ""
                finish = r.choices[0].finish_reason
                break
            except Exception as e:
                print("retry", key, e); time.sleep(5)
        w.writerow({**p, "response": text, "model": MODEL, "finish_reason": finish,
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds")})
        f.flush(); print("done", key, finish)
