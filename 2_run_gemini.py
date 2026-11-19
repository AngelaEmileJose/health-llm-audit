"""Run all prompts through a Gemini/Gemma model via the Google AI Studio API (no system prompt, one prompt per call).
Usage:
  $env:GEMINI_API_KEY="your-key"
  python 2_run_gemini.py <model-name> [label]
Label defaults to "gemini"; use e.g. "gemma" if running a Gemma model through Google AI Studio.
Get a key from Google AI Studio; copy the exact model name from Google's models page.
Saves responses/<label>.csv. Re-running resumes and skips finished rows.
"""
import csv, os, sys, time, datetime, json

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

if len(sys.argv) < 2:
    sys.exit("Give the model name, e.g. python 2_run_gemini.py <model-name> [label]")
MODEL = sys.argv[1]
MAX_TOKENS = 2000
LABEL = sys.argv[2] if len(sys.argv) > 2 else "gemini"
OUT = f"responses/{LABEL}.csv"

api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if not api_key:
    sys.exit("Error: GEMINI_API_KEY environment variable is not set.\nSet it with: $env:GEMINI_API_KEY=\"your-key\"")

os.makedirs("responses", exist_ok=True)
prompts = list(csv.DictReader(open("prompts.csv", encoding="utf-8-sig")))
done = {}
if os.path.exists(OUT):
    done = {(r["qid"], r["variant"]): r for r in csv.DictReader(open(OUT, encoding="utf-8-sig"))}

def call_gemini_api(model, prompt, key, max_tokens):
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        r = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=max_tokens))
        text = r.text or ""
        finish = str(r.candidates[0].finish_reason) if r.candidates else "no_candidate"
        return text, finish
    except ImportError:
        import urllib.request, urllib.error
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                finish = candidates[0].get("finishReason", "STOP")
                return text, finish
            return "", "no_candidate"

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
                text, finish = call_gemini_api(MODEL, p["prompt"], api_key, MAX_TOKENS)
                break
            except Exception as e:
                print("retry", key, e); time.sleep(5)
        w.writerow({**p, "response": text, "model": MODEL, "finish_reason": finish,
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds")})
        f.flush(); print("done", key, finish)
