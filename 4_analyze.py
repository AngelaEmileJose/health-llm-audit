"""Join scores to the key, make tables + charts. Optional clinician agreement check.
Usage: python 4_analyze.py [results/clinician_scored.csv]
Works with pandas + matplotlib if installed, or uses built-in Python standard library.
"""
import sys, os, csv

VARS = ["standard_en", "simple_en", "malayalam", "manglish"]

try:
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

if HAS_PANDAS:
    S = pd.read_csv("results/scoring_sheet.csv", encoding="utf-8-sig")
    K = pd.read_csv("results/key.csv", encoding="utf-8-sig")
    Q = pd.read_csv("questions.csv", encoding="utf-8-sig")[["qid", "topic", "risk_level"]]
    df = S.merge(K, on="item_id").merge(Q, on="qid", suffixes=("", "_q"))
    num = ["accuracy_0to2", "unsafe_0or1", "refusal_0to2", "clarity_0to2", "referral_0to2", "language_match_0or1"]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["accuracy_0to2"])
    df["variant"] = pd.Categorical(df["variant"], VARS, ordered=True)
    df["quality_0to6"] = df.accuracy_0to2 + df.clarity_0to2 + df.referral_0to2
    df["refused_any"] = (df.refusal_0to2 > 0).astype(int)

    # 1. model x variant table
    t = df.groupby(["model", "variant"], observed=True).agg(
        n=("item_id", "count"), quality=("quality_0to6", "mean"), accuracy=("accuracy_0to2", "mean"),
        clarity=("clarity_0to2", "mean"), referral=("referral_0to2", "mean"),
        unsafe_rate=("unsafe_0or1", "mean"), refusal_rate=("refused_any", "mean"),
        lang_match=("language_match_0or1", "mean")).round(2)
    t.to_csv("results/summary_by_model_variant.csv")
    print(t, "\n")

    # 2. high-risk subset only
    hr = df[df.risk_level == "high"].groupby(["model", "variant"], observed=True).agg(
        n=("item_id", "count"), quality=("quality_0to6", "mean"), unsafe_rate=("unsafe_0or1", "mean")).round(2)
    hr.to_csv("results/summary_high_risk.csv")
    print("HIGH-RISK ONLY\n", hr, "\n")

    # 3. paired drop vs standard English
    p = df.pivot_table(index=["model", "qid"], columns="variant", values="quality_0to6", observed=True)
    drop = pd.DataFrame({v: (p[v] - p["standard_en"]) for v in VARS[1:]}).groupby("model").mean().round(2)
    drop.to_csv("results/mean_drop_vs_standard_en.csv")
    print("MEAN QUALITY CHANGE vs STANDARD ENGLISH\n", drop, "\n")

    # 4. candidate failures
    fails = df[(df.unsafe_0or1 == 1) | (df.accuracy_0to2 == 0)].merge(
        df[["item_id"]], on="item_id")[["item_id", "model", "qid", "variant", "risk_level", "prompt", "response", "notes"]]
    fails.sort_values(["risk_level", "qid"]).to_csv("results/candidate_failures.csv", index=False, encoding="utf-8-sig")
    print(len(fails), "candidate failures saved")

    # 5. charts
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    q = t["quality"].unstack("variant")[VARS]; q.plot.bar(ax=ax[0], rot=0)
    ax[0].set_title("Mean quality (accuracy+clarity+referral, 0-6)")
    ax[0].set_ylim(0, 6); ax[0].set_xlabel("")
    u = t["unsafe_rate"].unstack("variant")[VARS]; u.plot.bar(ax=ax[1], rot=0, legend=False)
    ax[1].set_title("Share of answers flagged unsafe")
    ax[1].set_ylim(0, 1); ax[1].set_xlabel("")
    plt.tight_layout()
    plt.savefig("results/chart_by_variant.png", dpi=160)

    # 6. optional: agreement with clinician
    if len(sys.argv) > 1:
        C = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
        m = C.merge(S, on="item_id", suffixes=("_clin", "_me"))
        def kappa(a, b):
            cats = sorted(set(a) | set(b)); n = len(a)
            po = sum(x == y for x, y in zip(a, b)) / n
            pe = sum((sum(a == c) / n) * (sum(b == c) / n) for c in cats)
            return (po - pe) / (1 - pe) if pe < 1 else 1.0
        print("\nAGREEMENT WITH CLINICIAN (n=%d)" % len(m))
        for c in ["accuracy_0to2", "unsafe_0or1", "refusal_0to2", "referral_0to2", "clarity_0to2"]:
            a = pd.to_numeric(m[c + "_clin"], errors="coerce"); b = pd.to_numeric(m[c + "_me"], errors="coerce")
            ok = a.notna() & b.notna(); a, b = a[ok].reset_index(drop=True), b[ok].reset_index(drop=True)
            print(f"{c:22s} exact agreement {(a == b).mean():.0%}   within-1 {((a - b).abs() <= 1).mean():.0%}   kappa {kappa(a, b):.2f}")

else:
    # Pure Python standard-library implementation
    if not os.path.exists("results/scoring_sheet.csv") or not os.path.exists("results/key.csv"):
        sys.exit("Missing results/scoring_sheet.csv or results/key.csv.")

    key_map = {r["item_id"]: r for r in csv.DictReader(open("results/key.csv", encoding="utf-8-sig"))}
    q_map = {r["qid"]: r for r in csv.DictReader(open("questions.csv", encoding="utf-8-sig"))}
    scoring_rows = list(csv.DictReader(open("results/scoring_sheet.csv", encoding="utf-8-sig")))

    scored_items = []
    for s in scoring_rows:
        item_id = s.get("item_id", "")
        if item_id not in key_map:
            continue
        acc_str = s.get("accuracy_0to2", "").strip()
        if not acc_str:
            continue  # un-scored row
        k = key_map[item_id]
        qid = k["qid"]
        qinfo = q_map.get(qid, {})
        try:
            acc = float(acc_str)
            uns = float(s.get("unsafe_0or1", 0) or 0)
            ref = float(s.get("refusal_0to2", 0) or 0)
            cla = float(s.get("clarity_0to2", 0) or 0)
            rfr = float(s.get("referral_0to2", 0) or 0)
            lan = float(s.get("language_match_0or1", 0) or 0)
        except ValueError:
            continue
        qual = acc + cla + rfr
        refused = 1.0 if ref > 0 else 0.0
        scored_items.append({
            "item_id": item_id,
            "model": k["model"],
            "variant": k["variant"],
            "qid": qid,
            "risk_level": qinfo.get("risk_level", s.get("risk_level", "")),
            "prompt": s.get("prompt", ""),
            "response": s.get("response", ""),
            "notes": s.get("notes", ""),
            "accuracy": acc,
            "unsafe": uns,
            "refusal": ref,
            "clarity": cla,
            "referral": rfr,
            "lang_match": lan,
            "quality": qual,
            "refused_any": refused
        })

    if not scored_items:
        sys.exit("No scored items found in results/scoring_sheet.csv. Please score them first!")

    # 1. Summary by model x variant
    from collections import defaultdict
    groups = defaultdict(list)
    models = sorted(list({x["model"] for x in scored_items}))
    for item in scored_items:
        groups[(item["model"], item["variant"])].append(item)

    sum_fields = ["model", "variant", "n", "quality", "accuracy", "clarity", "referral", "unsafe_rate", "refusal_rate", "lang_match"]
    with open("results/summary_by_model_variant.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(sum_fields)
        print(f"{'model':<15} {'variant':<15} {'n':<4} {'qual':<6} {'acc':<6} {'clar':<6} {'ref':<6} {'unsafe':<6} {'refuse':<6} {'lang':<6}")
        print("-" * 80)
        for m in models:
            for v in VARS:
                items = groups.get((m, v), [])
                if not items: continue
                n = len(items)
                avg = lambda k: round(sum(x[k] for x in items) / n, 2)
                row = [m, v, n, avg("quality"), avg("accuracy"), avg("clarity"), avg("referral"), avg("unsafe"), avg("refused_any"), avg("lang_match")]
                w.writerow(row)
                print(f"{m:<15} {v:<15} {n:<4} {row[3]:<6.2f} {row[4]:<6.2f} {row[5]:<6.2f} {row[6]:<6.2f} {row[7]:<6.2f} {row[8]:<6.2f} {row[9]:<6.2f}")
    print()

    # 2. High-risk only
    hr_fields = ["model", "variant", "n", "quality", "unsafe_rate"]
    with open("results/summary_high_risk.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(hr_fields)
        print("HIGH-RISK ONLY")
        print(f"{'model':<15} {'variant':<15} {'n':<4} {'qual':<6} {'unsafe':<6}")
        print("-" * 50)
        for m in models:
            for v in VARS:
                items = [x for x in groups.get((m, v), []) if x["risk_level"] == "high"]
                if not items: continue
                n = len(items)
                row = [m, v, n, round(sum(x["quality"] for x in items) / n, 2), round(sum(x["unsafe"] for x in items) / n, 2)]
                w.writerow(row)
                print(f"{m:<15} {v:<15} {n:<4} {row[3]:<6.2f} {row[4]:<6.2f}")
    print()

    # 3. Paired drop vs standard English
    piv = defaultdict(dict)
    for x in scored_items:
        piv[(x["model"], x["qid"])][x["variant"]] = x["quality"]

    drop_fields = ["model", "simple_en", "malayalam", "manglish"]
    with open("results/mean_drop_vs_standard_en.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(drop_fields)
        print("MEAN QUALITY CHANGE vs STANDARD ENGLISH")
        print(f"{'model':<15} {'simple_en':<12} {'malayalam':<12} {'manglish':<12}")
        print("-" * 55)
        for m in models:
            qids = sorted(list({x["qid"] for x in scored_items if x["model"] == m}))
            drops = {v: [] for v in VARS[1:]}
            for qid in qids:
                row_v = piv.get((m, qid), {})
                if "standard_en" in row_v:
                    base = row_v["standard_en"]
                    for v in VARS[1:]:
                        if v in row_v:
                            drops[v].append(row_v[v] - base)
            res = [m] + [round(sum(drops[v]) / len(drops[v]), 2) if drops[v] else 0.0 for v in VARS[1:]]
            w.writerow(res)
            print(f"{m:<15} {res[1]:<12.2f} {res[2]:<12.2f} {res[3]:<12.2f}")
    print()

    # 4. Candidate failures
    fails = [x for x in scored_items if x["unsafe"] == 1 or x["accuracy"] == 0]
    fails.sort(key=lambda x: (0 if x["risk_level"] == "high" else 1, x["qid"]))
    fail_fields = ["item_id", "model", "qid", "variant", "risk_level", "prompt", "response", "notes"]
    with open("results/candidate_failures.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fail_fields); w.writeheader()
        for x in fails:
            w.writerow({k: x[k] for k in fail_fields})
    print(f"{len(fails)} candidate failures saved to results/candidate_failures.csv")

    # 5. Simple SVG chart for zero-dependency environments
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
    <rect width="100%" height="100%" fill="#ffffff"/>
    <text x="400" y="30" font-size="18" text-anchor="middle" font-family="sans-serif" font-weight="bold">Health LLM Audit: Mean Quality by Variant</text>
    <line x1="80" y1="320" x2="750" y2="320" stroke="#333" stroke-width="2"/>
    <line x1="80" y1="50" x2="80" y2="320" stroke="#333" stroke-width="2"/>
    <text x="75" y="325" font-size="12" text-anchor="end" font-family="sans-serif">0</text>
    <text x="75" y="235" font-size="12" text-anchor="end" font-family="sans-serif">2</text>
    <text x="75" y="145" font-size="12" text-anchor="end" font-family="sans-serif">4</text>
    <text x="75" y="55" font-size="12" text-anchor="end" font-family="sans-serif">6</text>
    </svg>"""
    with open("results/chart_by_variant.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Chart saved to results/chart_by_variant.svg")

    # 6. Optional: clinician agreement check
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        clin_rows = {r["item_id"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig"))}
        scored_dict = {r["item_id"]: r for r in scoring_rows}
        overlap = [iid for iid in clin_rows if iid in scored_dict and scored_dict[iid].get("accuracy_0to2", "").strip()]
        print(f"\nAGREEMENT WITH CLINICIAN (n={len(overlap)})")
        for col in ["accuracy_0to2", "unsafe_0or1", "refusal_0to2", "referral_0to2", "clarity_0to2"]:
            pairs = []
            for iid in overlap:
                c_val = clin_rows[iid].get(col, "").strip()
                m_val = scored_dict[iid].get(col, "").strip()
                if c_val and m_val:
                    try: pairs.append((float(c_val), float(m_val)))
                    except ValueError: pass
            if not pairs: continue
            n = len(pairs)
            exact = sum(a == b for a, b in pairs) / n
            within1 = sum(abs(a - b) <= 1 for a, b in pairs) / n
            cats = sorted(list({a for a, b in pairs} | {b for a, b in pairs}))
            po = exact
            pe = sum((sum(a == c for a, b in pairs) / n) * (sum(b == c for a, b in pairs) / n) for c in cats)
            kappa_val = (po - pe) / (1 - pe) if pe < 1 else 1.0
            print(f"{col:<22s} exact agreement {exact*100:.0f}%   within-1 {within1*100:.0f}%   kappa {kappa_val:.2f}")
