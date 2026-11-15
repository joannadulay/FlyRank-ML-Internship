"""Builds site/index.html from the JSON files the notebooks write. No number in the page is typed by hand."""
import html, json, os
e = html.escape

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@125,400;125,600;125,800&display=swap');
@font-face{font-family:"Helios Extended";font-display:swap;
  src:local("Helios Extended"),local("HeliosExtended"),local("Helios-Extended"),
      url("fonts/HeliosExtended.woff2") format("woff2"),url("fonts/HeliosExtended.woff") format("woff");}
:root{--bg:#f4f3ef;--ink:#111;--mut:#6f6e68;--line:#111;--hair:#cfcdc4;--acc:#ff4f00;
  --f:"Helios Extended","Archivo","Helvetica Neue",Arial,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:auto}
body{margin:0;background:var(--bg);color:var(--ink);font:400 14px/1.65 var(--f);font-stretch:125%;-webkit-font-smoothing:antialiased}
a{color:var(--ink);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:var(--acc)}
.shell{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:100vh}
aside{position:sticky;top:0;height:100vh;padding:28px 24px;border-right:1px solid var(--line);display:flex;flex-direction:column;justify-content:space-between}
.brand{font-weight:800;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;line-height:1.4}
nav{margin-top:36px;display:flex;flex-direction:column}
nav a{display:flex;gap:14px;padding:9px 0;border-top:1px solid var(--hair);text-decoration:none;font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}
nav a b{font-weight:600;min-width:1.6em}nav a:last-child{border-bottom:1px solid var(--hair)}
nav a:hover{color:var(--ink)}nav a.on{color:var(--ink);font-weight:800}nav a.on b{color:var(--acc)}
.credit{font-size:.66rem;line-height:1.5;color:var(--mut);letter-spacing:.03em}
main{padding:56px 64px 120px 56px}
.panel{max-width:920px}
h1{font-weight:800;font-size:clamp(1.9rem,4vw,3.4rem);line-height:1.04;letter-spacing:-.015em;text-transform:uppercase;margin:.15em 0 .5em}
h2{font-weight:800;font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;border-top:2px solid var(--line);padding-top:10px;margin:2.6em 0 .9em}
h2:first-of-type{margin-top:0}
p{margin:0 0 1em;max-width:68ch}ul{padding-left:1.1em;max-width:68ch}li{margin-bottom:.5em}
.meta,figcaption,.small{color:var(--mut);font-size:.74rem;letter-spacing:.02em}
.lead{font-size:1.05rem;line-height:1.55;max-width:60ch;border-left:4px solid var(--acc);padding-left:18px;margin:1.4em 0 2em}
.kf{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-top:2px solid var(--line);border-bottom:1px solid var(--line);margin:2em 0}
.kf div{padding:16px 16px 16px 0}.kf div+div{padding-left:16px;border-left:1px solid var(--hair)}
.kf strong{display:block;font-weight:800;font-size:clamp(1.4rem,2.6vw,2.2rem);letter-spacing:-.02em;line-height:1.1}
.kf span{font-size:.68rem;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);display:block;margin-top:6px}
table{border-collapse:collapse;width:100%;font-size:.78rem;margin:1.2em 0;font-variant-numeric:tabular-nums}
th{font-size:.64rem;letter-spacing:.07em;text-transform:uppercase;font-weight:600;color:var(--mut);text-align:right;padding:6px 10px;border-bottom:1px solid var(--line)}
td{padding:7px 10px;border-bottom:1px solid var(--hair);text-align:right}th:first-child,td:first-child{text-align:left;padding-left:0}
.wrap{overflow-x:auto}figure{margin:1.8em 0;max-width:760px}img{max-width:100%;height:auto;display:block}
figcaption{margin-top:8px}code{font-size:.9em;background:#e9e7df;padding:1px 5px}
.tag{display:inline-block;background:var(--ink);color:var(--bg);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;padding:2px 8px;margin-right:8px}
.panel[hidden]{display:none}
@media (max-width:900px){
 .shell{grid-template-columns:1fr}
 aside{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:16px 18px}
 nav{flex-direction:row;overflow-x:auto;margin-top:12px;gap:18px}
 nav a{border:0!important;white-space:nowrap;padding:6px 0}nav a b{display:none}
 .credit{display:none}main{padding:28px 18px 80px}.kf{grid-template-columns:1fr 1fr}.kf div:nth-child(3){border-left:0;padding-left:0}
}
"""

JS = """
(function(){
  var links=[].slice.call(document.querySelectorAll('nav a')), panels=[].slice.call(document.querySelectorAll('.panel'));
  function show(){
    var id=(location.hash||'').slice(1); if(!document.getElementById(id)) id='overview';
    panels.forEach(function(p){p.hidden=(p.id!==id)});
    links.forEach(function(a){var on=a.getAttribute('href')==='#'+id; a.classList.toggle('on',on); a.setAttribute('aria-current',on?'page':'false')});
    window.scrollTo(0,0);
  }
  window.addEventListener('hashchange',show); show();
})();
"""

def nice(name):
    return {"hist_gradient_boosting": "histogram gradient boosting", "logistic_regression": "logistic regression"}.get(name, name.replace("_", " "))

def pct(x): return f"{100*x:.1f}%"
def f3(x): return f"{x:.3f}"

def table(head, rows):
    h = "".join(f"<th>{e(str(c))}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table><tr>{h}</tr>{b}</table></div>'

def fig(figs, key, cap):
    return f'<figure><img alt="{e(cap)}" src="data:image/png;base64,{figs[key]}"><figcaption>{e(cap)}</figcaption></figure>' if key in figs else ""

def build(out_path, final, dev, audit, queue, figs, funnel, plan, cfg, repo_url, extra=None):
    extra = extra or {}
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
        f"A {nice(final['model'])} classifier uses only the preceding {2*w} days of search and engagement signals, and is trained on earlier cutoffs and tested on a later, sealed month. "
        f"On {final['n_test']:,} held-out pages the model's macro F1 is {f3(m['macro_f1'])}, {verdict}. "
        f"The ranked list is decision-support only: it is directional, not causal, and says nothing about how Google ranks pages.")
    ev_rows = [[r["name"], f"{r['n']:,}", pct(r["share_declined"]), f"{r['lift']:.2f}x"] for r in q["precision_at_k"]]
    cm = table(["Method", "Macro F1", "Accuracy"], [
        ["Model (" + nice(final["model"]) + ")", f3(m["macro_f1"]), f3(m["accuracy"])]] +
        [[k.replace("_", " ") + " rule", f3(v["macro_f1"]), f3(v["accuracy"])] for k, v in final["baselines"].items()])
    pc = table(["Class", "Share of test pages", "Model F1", "Best-baseline F1"], [
        [c, pct(final["class_share_test"].get(c, 0)), f3(m["per_class_f1"][c]), f3(b["per_class_f1"][c])] for c in m["per_class_f1"]])
    rec_note = ""
    rows_q = {r["name"]: r for r in q["precision_at_k"]}
    mq = rows_q.get("review_decline_risk (top 5%)")
    sq = next((r for k, r in rows_q.items() if "last-week trend" in k), None)
    if mq and sq:
        if sq["share_declined"] > mq["share_declined"]:
            rec_note += (f"<p><b>Reading the table honestly.</b> Ranking pages by the weakest last-week trend alone found a higher share of true decliners "
                         f"({pct(sq['share_declined'])}) than the model-based queue ({pct(mq['share_declined'])}). For decline risk alone, the simple rule was the better choice on this month.</p>")
        else:
            rec_note += (f"<p><b>Reading the table honestly.</b> The model-based queue ({pct(mq['share_declined'])} declined) ranked at least as well as the simple last-week-trend rule ({pct(sq['share_declined'])}) on this month.</p>")
    oth = q.get("other")
    if oth:
        rec_note += (f"<p>The model’s distinct contribution is the other two slices: pages in <b>watch_recovery</b> actually recovered {pct(oth['watch_recovery_share_recovery'])} of the time (all pages: {pct(oth['base_recovery'])}), "
                     f"and pages in <b>support_growth</b> actually grew {pct(oth['support_growth_share_growth'])} of the time (all pages: {pct(oth['base_growth'])}).</p>")
    fn = funnel
    data_rows = [["Pages with any GSC row in the 3 windows", f"{fn['pages_seen']:,}"],
                 [f"≥{cfg['min_avail_days']} GSC-available days in window B", f"{fn['gsc_ok_in_B']:,}"],
                 ["… and in window A", f"{fn['and_in_A']:,}"], [f"… and ≥{cfg['min_impr_B']} impressions in B", f"{fn['and_enough_impr']:,}"],
                 ["… and ≥14 available days in the outcome window C (final set)", f"{fn['and_in_C_final']:,}"]]
    aud = audit
    audit_rows = [["Random row split (pages leak across cutoffs)", f3(aud["random_split"]["macro_f1"])],
                  ["Time-aware split (train earlier → validate later)", f3(aud["time_split"]["macro_f1"])],
                  ["Time-aware + unseen clients", f3(aud["time_and_client_split"]["macro_f1"])]]
    bt_html = ""
    if extra.get("backtest"):
        bt = extra["backtest"]
        rows_bt = [[r["test_month"], f"{r['n']:,}", f3(r["model"]), f3(r["persistence"]), f3(r.get("recent_slope", float("nan"))), f3(r.get("momentum_tree", float("nan"))), f3(r["majority"])] for r in bt]
        wins = sum(r["model"] > max(r["persistence"], r.get("recent_slope", 0), r.get("momentum_tree", 0), r["majority"]) for r in bt)
        bt_html = (f"<p><b>Stability across months.</b> Re-fitting on only earlier cutoffs each time, the model beat the strongest simple baseline in {wins} of {len(rows_bt)} test months (macro F1, development data):</p>"
                   + table(["Test month (cutoff)", "Pages", "Model", "Persistence", "Recent-slope rule", "Momentum tree", "Majority"], rows_bt))
    regime_html, extra_lim = "", ""
    if extra.get("regime"):
        reg = extra["regime"]
        regime_html = ("<p>Share of page-windows in each outcome class, by cutoff:</p>"
                       + table(["Cutoff", "Decline", "Growth", "Recovery", "Stable"],
                               [[c, *[pct(v.get(k, 0)) for k in ("Decline", "Growth", "Recovery", "Stable")]] for c, v in reg.items()]))
        dec = [v.get("Decline", 0) for v in reg.values()]
        if max(dec) - min(dec) >= 0.10:
            extra_lim += f"<li>The outcome mix shifts sharply between cutoffs (Decline from {pct(min(dec))} to {pct(max(dec))} of pages), so a result from one month may not carry to another.</li>"
        else:
            extra_lim += f"<li>The Decline share moved only between {pct(min(dec))} and {pct(max(dec))} across cutoffs, but other months and sites may behave differently.</li>"
    if extra.get("top2_client_share") is not None and extra["top2_client_share"] >= 0.30:
        extra_lim += f"<li>A few clients dominate: the two largest hold {pct(extra['top2_client_share'])} of page-windows across {extra['n_clients']} clients, so uncertainty is wide and results may not generalise to other sites.</li>"
    kf = [(f3(m["macro_f1"]), "Model macro F1 · sealed June test"),
          (f3(b["macro_f1"]), "Best simple baseline · " + final["best_baseline"].replace("_", " ")),
          (f"{d:+.3f}", f"Difference · 95% interval {lo:+.3f} to {hi:+.3f}"),
          (f"{final['n_test']:,}", "Held-out pages")]
    kf_html = '<div class="kf">' + "".join(f"<div><strong>{e(v)}</strong><span>{e(t)}</span></div>" for v, t in kf) + "</div>"

    overview = f"""<h1>Which pages need attention first?</h1>
<p class="meta">Predicting search-visibility momentum from historical signals · Joanna Dulay · Built on the FlyRank ML Internship dataset</p>
<h2>Abstract</h2><p class="lead">{e(abstract)}</p>{kf_html}
<h2>1 · Introduction</h2>
<p>A site can hold thousands of pages and a content team has hours, not weeks. The decision this work supports is <em>which pages to review first</em>. Reviewing a page that would have been fine anyway wastes time; missing a page that was sliding costs visibility. The output is therefore a ranked queue with plain-language reason codes for a person to check, not an automatic action.</p>"""

    data = f"""<h2>2 · Data</h2>
<p>Source: the FlyRank ML Internship warehouse, table <code>fact_content_daily_performance</code> (one row per page per day, with Google Search Console and GA4 fields, identifiers pre-hashed). Development used cutoffs up to {e(cfg['dev_end'])}; the month ending {e(cfg['test_end'])} was kept sealed and used once for the final test. A zero is treated as a real zero only on days flagged as GSC-available; unavailable days are excluded rather than filled. Page counts at the final test cutoff ({e(str(plan['test']))}):</p>
{table(["Step", "Pages"], data_rows)}
{regime_html}
<p class="small">No client names, domains, URLs, queries, credentials or raw exports are published.</p>"""

    method = f"""<h2>3 · Methodology</h2>
<p><b>Windows.</b> For each cutoff date T: window A = days T−{2*w-1} to T−{w}, window B = T−{w-1} to T (history, used for features), window C = T+1 to T+{w} (outcome, used only for the label).</p>
<p><b>Label.</b> Using impressions per GSC-available day: Growth if C is at least {thr}% above B; Decline if at least {thr}% below; Recovery is Growth where B was itself at least {thr}% below A; otherwise Stable.</p>
<p><b>Features</b> ({len(dev['features'])}): impression level and change, last-7-day slope, CTR and its change, average position and change, volatility, share of active days, data availability, and GA4 coverage and engagement (left missing, not zero-filled, when GA4 was not reporting).</p>
<p><b>Baselines:</b> always the majority class; “last window’s direction continues”; “last window’s move reverses”; a one-feature “recent slope” rule (a small decision tree using only the last-7-day trend); and a two-feature “momentum tree” (last-7-day trend and change versus the previous window). The last two are the demanding ones: they show how much of the model’s signal is simply recent momentum. The trees’ depth and class weighting were fixed on validation data only.</p>
<p><b>Validation:</b> time-aware. Training cutoffs are spaced {w} days apart, so no training label window overlaps the next split; the test cutoff comes from the sealed final month. Primary metric: macro F1 (every class counts equally); accuracy is secondary. Uncertainty comes from resampling whole clients.</p>
<p><b>Leakage checks.</b> (1) Features recomputed after physically deleting all rows after the cutoff were identical (max absolute difference {aud['leakage']['max_abs_diff']:.2g}). (2) No single feature alone reached macro F1 above {aud['leakage']['single_feature_max']:.3f}. (3) Client and page identifiers are never model inputs.</p>"""

    results = f"""<h2>4 · Results</h2>
{cm}{pc}
{fig(figs,'compare','Macro F1 on the sealed test cutoff: model vs simple baselines')}
<p>The model’s macro F1 is {verdict}. {e(dev['reading'])}</p>
{fig(figs,'confusion','Where the model is right and wrong (rows = observed class, share of that class)')}
<p><b>Why the split matters.</b> The same model scored differently depending on how it was validated:</p>
{table(["Validation design", "Macro F1"], audit_rows)}
{bt_html}
{fig(figs,'importance','Which signals the model leans on (permutation importance, validation set; association, not cause)')}"""

    limits = f"""<h2>5 · Limitations and honest framing</h2>
<ul><li>These are <b>observed, directional</b> associations in one panel of sites; they are not causal and do not show how Google ranks or refreshes pages.</li>
<li>Labels measure change in impressions, which also moves with seasonality, demand and algorithm updates outside the page’s control.</li>
<li>Window B appears in both the features and the label’s denominator, so part of the signal is regression to the mean.</li>
<li>Coverage is uneven: only pages with enough GSC-available days enter ({fn['and_in_C_final']:,} of {fn['pages_seen']:,}), and GA4 is missing for many page-days.</li>
{extra_lim}<li>One sealed outcome month: results may differ in other months and other sites.</li>
<li>Class balance is uneven ({', '.join(f'{k} {pct(v)}' for k, v in final['class_share_test'].items())}), so per-class scores matter more than accuracy.</li></ul>"""

    playbook = f"""<h2>6 · Ranked recommendations (action playbook)</h2>
<p>Queue logic: <b>review_decline_risk</b> = the top {int(q['decline_top_share']*100)}% of pages by (predicted decline probability × observed impressions); <b>watch_recovery</b> and <b>support_growth</b> = highest predicted Recovery / Growth probability. Each row carries reason codes derived from the page’s own recent signals. Checked on the sealed month:</p>
{table(["Queue slice", "Pages", "Actually declined", "Lift vs all pages"], ev_rows)}
<p class="small">Base rate of Decline across all test pages: {pct(q['base_decline'])}.</p>
{rec_note}
{fig(figs,'lift','Share of flagged pages that actually declined in the next 28 days (orange = model queue; line = all pages)')}
<p><b>Human review before acting:</b> check for a known cause (seasonality, migration, tracking change); never auto-rewrite, merge or delete a page from this list. <b>Stale triggers:</b> re-evaluate when macro F1 on the newest labelled cutoff drops below the best baseline, or any key feature’s population stability index exceeds 0.25 (current largest: {e(queue['drift_top_feature'])} at {queue['drift_top_psi']:.2f}).</p>"""

    repro = f"""<h2>7 · Reproducibility</h2>
<p>All code is in <a href="{e(repo_url)}" target="_blank" rel="noopener">the project repository</a>: notebooks <code>w04_signal_audit</code>, <code>w05_model</code>, <code>w06_validation_audit</code>, <code>w07_action_playbook</code> and <code>capstone</code> under <code>work/notebooks/</code>, shared code in <code>work/src/</code>. Fixed seed {cfg['seed']}. Rebuilding the page-level tables can reorder rows, so a re-run may differ from the reported scores in the third decimal place.</p>
<h2>8 · Acknowledgments and data credit</h2>
<p>Built on the FlyRank ML Internship dataset — <a href="https://flyrank.ai" target="_blank" rel="noopener">flyrank.ai</a>.</p>"""

    tabs = [("overview", "Overview", overview), ("data", "Data", data), ("method", "Method", method), ("results", "Results", results),
            ("limits", "Limits", limits), ("playbook", "Playbook", playbook), ("repro", "Repro + credit", repro)]
    nav = "".join(f'<a href="#{i}"><b>{n:02d}</b>{e(l)}</a>' for n, (i, l, _) in enumerate(tabs, 1))
    panels = "".join(f'<section class="panel" id="{i}" aria-label="{e(l)}">{h}</section>' for i, l, h in tabs)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Which pages need attention first? Predicting search-visibility momentum</title><style>{CSS}</style></head><body>
<div class="shell"><aside><div><div class="brand">Search visibility<br>momentum</div><nav>{nav}</nav></div>
<div class="credit">Built on the FlyRank ML Internship dataset<br><a href="https://flyrank.ai" target="_blank" rel="noopener">flyrank.ai</a></div></aside>
<main>{panels}</main></div><script>{JS}</script></body></html>"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    return out_path
