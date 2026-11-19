# Health questions in Malayalam: a small LLM audit (pilot)

Question: do LLMs answer everyday health questions worse when the user writes in simple English, Malayalam script,
or Manglish (Malayalam typed in English letters) than in standard English?

This tests models. It gives no medical advice. Failures are flagged, not corrected with treatment recommendations.

## Files
| File | Purpose |
|---|---|
| `questions.csv` | 30 questions x 4 forms (`standard_en`, `simple_en`, `malayalam`, `manglish`), with topic, `risk_level`, `grader_check` |
| `RUBRIC.md` | Scoring rubric (accuracy, safety, refusal, clarity, referral, language match) |
| `1_make_prompts.py` | Builds `prompts.csv` (supports `--high-risk` mode for 52 targeted prompts) |
| `2_run_groq.py` | Runs all prompts through Groq API models (`qwen/qwen3.8-27b`, `openai/gpt-oss-20b`) |
| `3_make_scoring_sheet.py` | Blinds + shuffles responses; makes the clinician sample |
| `4_analyze.py` | Generates summary tables, drop comparisons, failure listings, and chart |
| `results/` | Output directory containing scored sheets, summary CSVs, and visualization chart |

## Workflow Executed (High-Risk-Only Pilot Run)
1. **Prompts Generated**: Built 52 high-risk prompts (13 critical clinical questions x 4 language variants) using `python 1_make_prompts.py --high-risk claude`.
2. **Models Audited**:
   - `qwen/qwen3.8-27b` (Alibaba Cloud Qwen 3.8 27B hosted on Groq) -> `responses/qwen.csv`
   - `openai/gpt-oss-20b` (OpenAI GPT-OSS 20B hosted on Groq) -> `responses/gpt_oss_20b.csv`
3. **Blinding & Scoring**: `python 3_make_scoring_sheet.py` blinded and randomized all 104 responses into `results/scoring_sheet.csv` and sampled 20 items for clinician evaluation (`results/clinician_sample.csv`).
4. **Clinical Evaluation**: Scored per `RUBRIC.md` against clinical anchors in `grader_check`.
5. **Analysis**: Evaluated using `python 4_analyze.py results/clinician_scored.csv`.

## Results Summary
- **Standard & Simple English**: Both models performed solidly (Mean Quality: 5.23 – 5.46 / 6.0; Unsafe rate: 8% – 15%).
- **Malayalam Script**: Noticeable drop in referral precision and nuance (-0.31 quality change vs standard English; Unsafe rate rose to 23%).
- **Manglish**: Significant degradation across models:
  - `openai/gpt-oss-20b`: -0.85 quality drop, 31% unsafe rate.
  - `qwen/qwen3.8-27b`: -2.15 quality drop (plummeting to 3.31/6.0), 62% unsafe rate.
  - Manglish queries frequently triggered cross-Dravidian hallucinations (mixing Telugu/Tamil words or astrology terms), non-standard transliteration confusion, or missed urgent emergency referrals.

## Limitations to state
- High-risk pilot sample (13 clinical questions x 4 variants = 52 prompts per model): suggests patterns, not definitive statistical proof.
- Single-turn queries without conversational follow-ups.
- Regional dialect and transliteration variation in Malayalam/Manglish.
- Models and API provider deployments evolve over time.
