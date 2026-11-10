"""Builds site/index.html from the JSON files the notebooks write. No number in the page is typed by hand."""
import html, json, os
e = html.escape

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a64;--line:#e2e0d8;--acc:#1f5f8b;--card:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16171a;--fg:#ecebe6;--mut:#a3a29b;--line:#2d2f34;--acc:#7fb6dd;--card:#1e2024}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 Georgia,'Times New Roman',serif}
main{max-width:760px;margin:0 auto;padding:48px 20px 80px}h1{font-size:2rem;line-height:1.25;margin:.2em 0}
h2{font-size:1.35rem;margin:2.2em 0 .4em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.meta,figcaption,.small{color:var(--mut);font-size:.9rem}table{border-collapse:collapse;width:100%;font:.9rem system-ui,sans-serif;margin:1em 0}
th,td{border-bottom:1px solid var(--line);padding:.4em .6em;text-align:right}th:first-child,td:first-child{text-align:left}
.wrap{overflow-x:auto}figure{margin:1.5em 0}img{max-width:100%;height:auto;background:#fff;border-radius:6px}
.abs{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:1em 1.2em}a{color:var(--acc)}code{font-size:.88em}
"""

def pct(x): return f"{100*x:.1f}%"
def f3(x): return f"{x:.3f}"

def table(head, rows):
    h = "".join(f"<th>{e(str(c))}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table><tr>{h}</tr>{b}</table></div>'

def fig(figs, key, cap):
    return f'<figure><img alt="{e(cap)}" src="data:image/png;base64,{figs[key]}"><figcaption>{e(cap)}</figcaption></figure>' if key in figs else ""

def build(out_path, final, dev, audit, queue, figs, funnel, plan, cfg, repo_url):
    m, b = final["model_scores"], final["baselines"][final["best_baseline"]]
    lo, hi = final["diff_ci95"]; d = final["diff_vs_best_baseline"]
    if lo > 0: verdict = f"higher than the best simple baseline ({final['best_baseline'].replace('_',' ')}) by {d:.3f} macro F1 (95% interval {lo:.3f} to {hi:.3f})"
    elif hi < 0: verdict = f"lower than the best simple baseline ({final['best_baseline'].replace('_',' ')}) by {abs(d):.3f} macro F1 (95% interval {lo:.3f} to {hi:.3f})"
    else: verdict = f"not reliably different from the best simple baseline ({final['best_baseline'].replace('_',' ')}): difference {d:+.3f} macro F1, 95% interval {lo:.3f} to {hi:.3f}"
    w = cfg["window_days"]; thr = int(cfg["change_thr"] * 100)
    q = queue["evidence"]
    abstract = (
        f"Content teams cannot review every page, so which pages deserve attention first? "
        f"We observe daily search-impression data for pages across many sites (FlyRank ML Internship dataset) and label each page-window as Growth, Recovery, Stable or Decline from the change in impressions per available day over the next {w} days (threshold {thr}%). "
        f"A {final['model'].replace('_',' ')} classifier uses only the preceding {2*w} days of search and engagement signals, and is trained on earlier cutoffs and tested on a later, sealed month. "
        f"On {final['n_test']:,} held-out pages the model's macro F1 is {f3(m['macro_f1'])}, {verdict}. "
        f"The ranked list is decision-support only: it is directional, not causal, and says nothing about how Google ranks pages.")
    ev_rows = [[r["name"], f"{r['n']:,}", pct(r["share_declined"]), f"{r['lift']:.2f}x"] for r in q["precision_at_k"]]
    cm = table(["Method", "Macro F1", "Accuracy"], [
        ["Model (" + final["model"].replace("_", " ") + ")", f3(m["macro_f1"]), f3(m["accuracy"])]] +
        [[k.replace("_", " ") + " rule", f3(v["macro_f1"]), f3(v["accuracy"])] for k, v in final["baselines"].items()])
    pc = table(["Class", "Share of test pages", "Model F1", "Best-baseline F1"], [
        [c, pct(final["class_share_test"].get(c, 0)), f3(m["per_class_f1"][c]), f3(b["per_class_f1"][c])] for c in m["per_class_f1"]])
    fn = funnel
    data_rows = [["Pages with any GSC row in the 3 windows", f"{fn['pages_seen']:,}"],
                 [f"≥{cfg['min_avail_days']} GSC-available days in window B", f"{fn['gsc_ok_in_B']:,}"],
                 ["… and in window A", f"{fn['and_in_A']:,}"], [f"… and ≥{cfg['min_impr_B']} impressions in B", f"{fn['and_enough_impr']:,}"],
                 ["… and ≥14 available days in the outcome window C (final set)", f"{fn['and_in_C_final']:,}"]]
    aud = audit
    audit_rows = [["Random row split (pages leak across cutoffs)", f3(aud["random_split"]["macro_f1"])],
                  ["Time-aware split (train earlier → validate later)", f3(aud["time_split"]["macro_f1"])],
                  ["Time-aware + unseen clients", f3(aud["time_and_client_split"]["macro_f1"])]]
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Which pages need attention first? Predicting search-visibility momentum</title><style>{CSS}</style></head><body><main>
<p class="meta">Research paper · Joanna Dulay · Built on the FlyRank ML Internship dataset</p>
<h1>Which pages need attention first? Predicting search-visibility momentum from historical signals</h1>
<h2>Abstract</h2><div class="abs">{e(abstract)}</div>
<h2>1. Introduction</h2>
<p>A site can hold thousands of pages and a content team has hours, not weeks. The decision this work supports is <em>which pages to review first</em>. Reviewing a page that would have been fine anyway wastes time; missing a page that was sliding costs visibility. The output is therefore a ranked queue with plain-language reason codes for a person to check, not an automatic action.</p>
<h2>2. Data</h2>
<p>Source: the FlyRank ML Internship warehouse, table <code>fact_content_daily_performance</code> (one row per page per day, with Google Search Console and GA4 fields, identifiers pre-hashed). Development used cutoffs up to {e(cfg['dev_end'])}; the month ending {e(cfg['test_end'])} was kept sealed and used once for the final test. A zero is treated as a real zero only on days flagged as GSC-available; unavailable days are excluded rather than filled. Page counts at the final test cutoff ({e(str(plan['test']))}):</p>
{table(["Step", "Pages"], data_rows)}
<p class="small">No client names, domains, URLs, queries, credentials or raw exports are published.</p>
<h2>3. Methodology</h2>
<p><b>Windows.</b> For each cutoff date T: window A = days T−{2*w-1} to T−{w}, window B = T−{w-1} to T (history, used for features), window C = T+1 to T+{w} (outcome, used only for the label). <b>Label.</b> Using impressions per GSC-available day: Growth if C is at least {thr}% above B; Decline if at least {thr}% below; Recovery is Growth where B was itself at least {thr}% below A; otherwise Stable. <b>Features</b> ({len(dev['features'])}): impression level and change, last-7-day slope, CTR and its change, average position and change, volatility, share of active days, data availability, and GA4 coverage/engagement (left missing, not zero-filled, when GA4 was not reporting). <b>Baselines:</b> always-the-majority-class, “last window’s direction continues”, and “last window’s move reverses”. <b>Validation:</b> time-aware. Training cutoffs are spaced {w} days apart, so no training label window overlaps the next split; the test cutoff comes from the sealed final month. Primary metric: macro F1 (every class counts equally); accuracy is secondary. Uncertainty comes from resampling whole clients.</p>
<p><b>Leakage checks.</b> (1) Features recomputed after physically deleting all rows after the cutoff were identical (max absolute difference {aud['leakage']['max_abs_diff']:.2g}). (2) No single feature alone reached macro F1 above {aud['leakage']['single_feature_max']:.3f}. (3) Client and page identifiers are never model inputs.</p>
<h2>4. Results</h2>
{cm}{pc}
{fig(figs,'compare','Macro F1 on the sealed test cutoff: model vs simple baselines')}
{fig(figs,'confusion','Where the model is right and wrong (rows = observed class, share of that class)')}
<p>The model’s macro F1 is {verdict}. {e(dev['reading'])}</p>
<p><b>Why the split matters.</b> The same model scored differently depending on how it was validated:</p>
{table(["Validation design", "Macro F1"], audit_rows)}
{fig(figs,'importance','Which signals the model leans on (permutation importance, validation set; association, not cause)')}
<h2>5. Limitations and honest framing</h2>
<ul><li>These are <b>observed, directional</b> associations in one panel of sites; they are not causal and do not show how Google ranks or refreshes pages.</li>
<li>Labels measure change in impressions, which also moves with seasonality, demand and algorithm updates outside the page’s control.</li>
<li>Window B appears in both the features and the label’s denominator, so part of the signal is regression to the mean.</li>
<li>Coverage is uneven: only pages with enough GSC-available days enter ({fn['and_in_C_final']:,} of {fn['pages_seen']:,}), and GA4 is missing for many page-days.</li>
<li>One sealed outcome month: results may differ in other months and other sites.</li>
<li>Class balance is uneven ({', '.join(f'{k} {pct(v)}' for k, v in final['class_share_test'].items())}), so per-class scores matter more than accuracy.</li></ul>
<h2>6. Ranked recommendations (action playbook)</h2>
<p>Queue logic: <b>review_decline_risk</b> = the top {int(q['decline_top_share']*100)}% of pages by (predicted decline probability × observed impressions); <b>watch_recovery</b> and <b>support_growth</b> = highest predicted Recovery / Growth probability. Each row carries reason codes derived from the page’s own recent signals. Checked on the sealed month:</p>
{table(["Queue slice", "Pages", "Actually declined", "Lift vs all pages"], ev_rows)}
<p class="small">Base rate of Decline across all test pages: {pct(q['base_decline'])}.</p>
{fig(figs,'lift','Share of flagged pages that actually declined in the next 28 days vs the base rate')}
<p><b>Human review before acting:</b> check for a known cause (seasonality, migration, tracking change); never auto-rewrite, merge or delete a page from this list. <b>Stale triggers:</b> re-evaluate when macro F1 on the newest labelled cutoff drops below the best baseline, or any key feature’s population stability index exceeds 0.25 (current largest: {e(queue['drift_top_feature'])} at {queue['drift_top_psi']:.2f}).</p>
<h2>7. Reproducibility</h2>
<p>All code is in <a href="{e(repo_url)}" target="_blank" rel="noopener">the project repository</a>: notebooks <code>w04_signal_audit</code>, <code>w05_model</code>, <code>w06_validation_audit</code>, <code>w07_action_playbook</code> and <code>capstone</code> under <code>work/notebooks/</code>, shared code in <code>work/src/</code>. Fixed seed {cfg['seed']}.</p>
<h2>8. Acknowledgments and data credit</h2>
<p>Built on the FlyRank ML Internship dataset — <a href="https://flyrank.ai" target="_blank" rel="noopener">flyrank.ai</a>.</p>
</main></body></html>"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    return out_path
