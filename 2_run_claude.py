"""Run all prompts through Claude via the API (clean runs: no system prompt, no memory, one prompt per call).
Usage: ANTHROPIC_API_KEY=... python 2_run_claude.py claude-sonnet-4-6
Saves responses/claude.csv. Re-running resumes and skips finished rows.
Record the exact model string and run date in README - models change over time.
"""
import csv, os, sys, time, datetime
import anthropic

MODEL = sys.argv[1] if len(sys.argv) > 1 else "claude-sonnet-4-6"
OUT = "responses/claude.csv"
prompts = list(csv.DictReader(open("prompts.csv", encoding="utf-8-sig")))
done = {}
if os.path.exists(OUT):
    done = {(r["qid"], r["variant"]): r for r in csv.DictReader(open(OUT, encoding="utf-8-sig"))}

client = anthropic.Anthropic()
fields = ["qid", "variant", "prompt", "response", "model", "timestamp"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    for p in prompts:
        key = (p["qid"], p["variant"])
        if key in done and done[key]["response"]:
            w.writerow(done[key]); continue
        for attempt in range(3):
            try:
                msg = client.messages.create(model=MODEL, max_tokens=2000,
                                             messages=[{"role": "user", "content": p["prompt"]}])
                text = "".join(b.text for b in msg.content if b.type == "text")
                break
            except Exception as e:
                print("retry", key, e); time.sleep(5); text = ""
        w.writerow({**p, "response": text, "model": MODEL,
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds")})
        f.flush(); print("done", key)
