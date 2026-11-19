"""Run all prompts through a model hosted on Groq (OpenAI-compatible API).
One script for every Groq model: run it once per model, with a different label each time.

Usage:
  $env:GROQ_API_KEY="your-key"
  python 2_run_groq.py <model-name> <label> [--limit N] [--delay SECONDS]
Examples (copy exact model names from Groq's models page; they change):
  python 2_run_groq.py llama-3.3-70b-versatile llama
  python 2_run_groq.py gemma2-9b-it gemma      # only if Groq currently hosts a Gemma model
  python 2_run_groq.py llama-3.3-70b-versatile llama --limit 4   # quick test on the first 4 prompts

Saves responses/<label>.csv. Re-running resumes: finished rows are kept, empty/failed rows are retried.
"""
import argparse, csv, os, sys, time, datetime, json

def load_dotenv():
    for p in [".env", os.path.expanduser("~/.env")]:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
        except Exception:
            pass

load_dotenv()

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("label")
ap.add_argument("--limit", type=int, default=None, help="only run the first N prompts (for testing)")
ap.add_argument("--delay", type=float, default=2.0, help="seconds to wait between calls (free-tier rate limits)")
a = ap.parse_args()

api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not api_key:
    sys.exit("Error: GROQ_API_KEY environment variable is not set.\nSet it with: $env:GROQ_API_KEY=\"your-key\"")

MAX_TOKENS = 2000   # same cap as the other scripts
OUT = f"responses/{a.label}.csv"
os.makedirs("responses", exist_ok=True)

prompts = list(csv.DictReader(open("prompts.csv", encoding="utf-8-sig")))
if a.limit: prompts = prompts[:a.limit]
done = {}
if os.path.exists(OUT):
    done = {(r["qid"], r["variant"]): r for r in csv.DictReader(open(OUT, encoding="utf-8-sig"))}

def call_groq_api(model, prompt, key, max_tokens):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content or "", r.choices[0].finish_reason
    except ImportError:
        import urllib.request, urllib.error
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"] or "", data["choices"][0]["finish_reason"]

fields = ["qid", "variant", "prompt", "response", "model", "finish_reason", "timestamp"]
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
    for p in prompts:
        key = (p["qid"], p["variant"])
        if key in done and done[key]["response"]:
            w.writerow(done[key]); continue
        text, finish = "", "error"
        for attempt in range(6):
            try:
                text, finish = call_groq_api(a.model, p["prompt"], api_key, MAX_TOKENS)
                break
            except Exception as e:
                wait = 10 * (attempt + 1)          # backs off if you hit a rate limit
                print("retry", key, str(e)[:120], f"- waiting {wait}s"); time.sleep(wait)
        w.writerow({**p, "response": text, "model": a.model, "finish_reason": finish,
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds")})
        f.flush(); print("done", key, finish); time.sleep(a.delay)
