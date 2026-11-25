"""Builds site/index.html from the JSON files the notebooks write. No number in the page is typed by hand."""
import html, json, os, re
e = html.escape

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,125,400;0,125,600;0,125,800;1,125,400;1,125,700&display=swap');
@font-face{font-family:"Helios Extended";font-display:swap;
  src:local("Helios Extended"),local("HeliosExtended"),local("Helios-Extended"),
      url("fonts/HeliosExtended.woff2") format("woff2"),url("fonts/HeliosExtended.woff") format("woff");}
:root{--bg:#fff;--ink:#14101c;--mut:#5f5873;--hair:#e4def2;--tint:#f4f0fc;--p1:#3b1d73;--p2:#6d3fc4;--p3:#b9a2e8;--p4:#e1d5f8;
  --pad:max(48px,calc((100% - 1200px)/2));--f:"Helios Extended","Archivo","Helvetica Neue",Arial,sans-serif}
*{box-sizing:border-box}
html{font-size:17px}
body{margin:0;background:var(--bg);color:var(--ink);font:400 1rem/1.7 var(--f);font-stretch:125%;-webkit-font-smoothing:antialiased}
a{color:var(--p2);text-underline-offset:3px}a:hover{color:var(--p1)}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px var(--pad);border-bottom:1.5px solid var(--ink);font-size:.76rem;letter-spacing:.08em;text-transform:uppercase}
.top .who{font-weight:800}.top .what{color:var(--mut)}
nav{display:flex;flex-wrap:wrap;gap:12px;padding:30px var(--pad) 0}
nav a{padding:7px 20px;border:1.5px solid var(--p3);border-radius:999px;text-decoration:none;color:var(--p1);font-size:.8rem;letter-spacing:.05em;background:#fff}
nav a:hover{background:var(--p4);border-color:var(--p2)}
nav a.on{background:var(--ink);border-color:var(--ink);color:#fff;font-weight:800}
main{padding:52px var(--pad) 48px}
.panel{max-width:1040px}.panel.wide{max-width:1200px}
h1{font-weight:800;font-size:clamp(2.1rem,3.8vw,3.2rem);line-height:1.08;letter-spacing:-.015em;margin:0 0 .35em}
h1 .hl{font-style:italic;font-weight:700;background:var(--p4);padding:0 .14em;box-decoration-break:clone;-webkit-box-decoration-break:clone}
h2{font-weight:800;font-size:1.75rem;line-height:1.2;letter-spacing:-.01em;margin:2.2em 0 .6em}
h2:first-child{margin-top:0}
.tag{display:inline-block;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase;color:var(--p2);font-weight:800;margin:0 0 .4em}
p{margin:0 0 1.1em;max-width:70ch}ul{padding-left:1.2em;max-width:70ch}li{margin-bottom:.6em}
.subt{font-style:italic;font-size:1.35rem;margin:0 0 1.1em;color:var(--p1)}
.meta,figcaption,.small{color:var(--mut);font-size:.84rem;letter-spacing:.02em}
.lead{font-size:1.1rem;line-height:1.65;max-width:58ch;margin:0 0 1.4em}
.hero{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(300px,.9fr);gap:64px;align-items:start;margin-bottom:2.6em}
.btn{display:inline-block;background:var(--ink);color:#fff;text-decoration:none;font-size:.78rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:15px 30px;margin:0 12px 10px 0;border:1.5px solid var(--ink)}
.btn:hover{background:var(--p2);border-color:var(--p2);color:#fff}
.btn.ghost{background:#fff;color:var(--ink)}.btn.ghost:hover{background:var(--p4);border-color:var(--ink);color:var(--ink)}
.win{border:1.5px solid var(--ink);background:#fff;margin:2em 0;max-width:780px}
.win .bar{display:flex;align-items:center;gap:7px;padding:8px 14px;background:var(--p4);border-bottom:1.5px solid var(--ink);font-size:.74rem;letter-spacing:.05em}
.win .bar i{width:10px;height:10px;border-radius:50%;border:1.5px solid var(--ink);background:#fff;display:block}
.win .bar i:first-child{background:var(--p2)}.win .bar span{margin-left:8px}
.win .body{padding:16px 20px}.win img{display:block;max-width:100%;height:auto}
.win figcaption{padding:10px 16px 14px;border-top:1px solid var(--hair);margin:0}
figure.win{margin-left:0}.panel figure.win:nth-of-type(even){margin-left:64px}
.nums{margin:0}.nums div{display:flex;justify-content:space-between;align-items:baseline;gap:20px;padding:13px 0;border-bottom:1px solid var(--hair)}
.nums div:last-child{border-bottom:0}.nums dt{font-size:.84rem;letter-spacing:.02em;color:var(--mut)}
.nums dd{margin:0;font-weight:800;font-size:1.7rem;color:var(--p2);font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:.92rem;margin:1.3em 0;font-variant-numeric:tabular-nums}
th{font-size:.72rem;letter-spacing:.07em;text-transform:uppercase;font-weight:600;color:var(--p1);text-align:right;padding:8px 12px;border-bottom:1.5px solid var(--ink)}
td{padding:9px 12px;border-bottom:1px solid var(--hair);text-align:right}th:first-child,td:first-child{text-align:left;padding-left:0}
.wrap{overflow-x:auto}code{font-size:.9em;background:var(--tint);padding:1px 6px}
footer{padding:0 var(--pad) 56px;color:var(--mut);font-size:.82rem;letter-spacing:.03em}
.term{border-bottom:1.5px dotted var(--p2);cursor:help}.term:hover,.term:focus,.term.open{background:var(--p4);outline:none}
.tip{position:fixed;z-index:60;max-width:370px;background:#fff;border:1.5px solid var(--ink);box-shadow:5px 5px 0 var(--p4);padding:14px 18px 12px;font-size:.86rem;line-height:1.55}
.tip[hidden]{display:none}.tip .tl{display:block;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--p2);font-weight:800}
.tip strong{display:block;font-size:1.05rem;margin:2px 0 6px}.tip p{margin:0;max-width:none}
.tip .here{border-top:1px solid var(--hair);margin-top:9px;padding-top:8px;color:var(--p1)}.tip .here b{font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--p2);display:block}
.hint{padding:14px var(--pad) 0;margin:0;max-width:none;color:var(--mut);font-size:.8rem}.hint .term{cursor:default}
.gloss dt{font-weight:800;margin-top:1.1em}.gloss dd{margin:.25em 0 0;max-width:70ch}
.panel[hidden]{display:none}
@media (max-width:900px){.hero{grid-template-columns:1fr;gap:32px}.panel figure.win:nth-of-type(even){margin-left:0}}
@media (max-width:700px){html{font-size:16px}:root{--pad:16px}.top{flex-direction:column;align-items:flex-start;gap:2px}nav{gap:8px;padding-top:20px}main{padding-top:30px}}
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

(function(){
  var G=__GLOSS__, tip=document.createElement('div'), hideT=null, cur=null;
  tip.className='tip'; tip.id='tip'; tip.setAttribute('role','tooltip'); tip.hidden=true; document.body.appendChild(tip);
  function fill(g){
    tip.textContent='';
    function el(t,c,x){var n=document.createElement(t); if(c) n.className=c; n.textContent=x; return n;}
    tip.appendChild(el('span','tl','What it means')); tip.appendChild(el('strong','',g.t)); tip.appendChild(el('p','',g.d));
    var h=document.createElement('p'); h.className='here'; h.appendChild(el('b','','In this paper')); h.appendChild(document.createTextNode(g.h)); tip.appendChild(h);
  }
  function place(el){
    var r=el.getBoundingClientRect(), w=tip.offsetWidth, h=tip.offsetHeight;
    var left=Math.min(Math.max(8,r.left+r.width/2-w/2),window.innerWidth-w-8), top=r.top-h-12;
    if(top<8) top=r.bottom+12; tip.style.left=left+'px'; tip.style.top=top+'px';
  }
  function open(el){var g=G[el.getAttribute('data-k')]; if(!g) return; clearTimeout(hideT); if(cur) cur.classList.remove('open');
    fill(g); tip.hidden=false; place(el); cur=el; el.classList.add('open'); el.setAttribute('aria-describedby','tip');}
  function close(){tip.hidden=true; if(cur){cur.classList.remove('open'); cur.removeAttribute('aria-describedby'); cur=null;}}
  function later(){clearTimeout(hideT); hideT=setTimeout(close,180);}
  document.addEventListener('mouseover',function(e){var t=e.target.closest&&e.target.closest('.term'); if(t) open(t); else if(e.target.closest&&e.target.closest('#tip')) clearTimeout(hideT);});
  document.addEventListener('mouseout',function(e){if(e.target.closest&&(e.target.closest('.term')||e.target.closest('#tip'))) later();});
  document.addEventListener('focusin',function(e){var t=e.target.closest&&e.target.closest('.term'); if(t) open(t);});
  document.addEventListener('focusout',function(e){if(e.target.closest&&e.target.closest('.term')) later();});
  document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('.term'); if(t){ if(cur===t&&!tip.hidden) close(); else open(t);} else if(!e.target.closest('#tip')) close();});
  document.addEventListener('keydown',function(e){if(e.key==='Escape') close();});
  window.addEventListener('scroll',close,true); window.addEventListener('hashchange',close);
})();
"""


# term key -> (title, what it means, how it is used in this paper, [regex alternatives that should trigger the pop-up])
GLOSSARY = {
 "macro-f1": ("Macro F1", "A score from 0 to 1 for a classifier. For each outcome it balances precision (how often a prediction is right) and recall (how many real cases are found), then averages the outcomes with equal weight.", "The paper’s main score. Every outcome counts equally, so a rare one like Recovery matters as much as a common one.", [r"macro F1"]),
 "f1": ("F1", "A score from 0 to 1 that combines precision and recall for one outcome.", "Shown for each outcome separately: Growth, Recovery, Stable and Decline.", [r"F1"]),
 "gsc": ("GSC (Google Search Console)", "Google’s free tool that reports how a site shows up in Google Search: how often it appeared, how often it was clicked, and where it ranked.", "The source of the daily search numbers. Days when GSC data was missing are skipped, never counted as zero.", [r"Google Search Console", r"Search Console", r"GSC"]),
 "ga4": ("GA4 (Google Analytics 4)", "Google’s analytics tool that records what visitors do on a site, such as sessions and engagement.", "Used for extra engagement signals. It is missing for many pages, so gaps are left blank, not filled with zeros.", [r"GA4"]),
 "ctr": ("CTR (click-through rate)", "Clicks divided by impressions: of everyone who saw the page in search results, the share who clicked it.", "One of the signals, together with how much it changed since the previous window.", [r"CTR", r"click-through rate"]),
 "impressions": ("Impressions", "How many times a page appeared in search results, whether or not anyone clicked.", "The paper’s measure of visibility. Labels come from the change in impressions per day.", [r"impressions?"]),
 "baseline": ("Baseline", "A simple method used as a yardstick. A model is only useful if it beats a fair baseline.", "Several baselines are compared, from always guessing the most common outcome to a small two-signal tree.", [r"baselines?"]),
 "sealed": ("Sealed test", "Data kept out of sight and used for one final check, after every choice is frozen, so the score is not flattered by tuning.", "The final month was sealed and scored once.", [r"sealed"]),
 "leakage": ("Leakage", "When information from the future sneaks into a model’s inputs, making it look better than it would in real use.", "Checked by deleting every later row and rebuilding the signals. They came out identical.", [r"leakage"]),
 "time-split": ("Time-aware split", "Training on earlier dates and testing on later ones, the way the model would really be used.", "Training cutoffs are spaced 28 days apart, so no outcome window overlaps the next split.", [r"time-aware"]),
 "random-split": ("Random split", "Shuffling rows into training and test sets without looking at dates. The same page can land on both sides, which flatters the score.", "Shown only to measure how much a careless test would overstate the result.", [r"random (?:row )?split"]),
 "cutoff": ("Cutoff", "The date a prediction is made. Only data up to that day is used as input.", "Each page is scored at several cutoffs, 28 days apart.", [r"cutoffs?"]),
 "window": ("Window", "A fixed stretch of days used to build signals or outcomes.", "A and B are 28 days of history. C is the next 28 days, whose result becomes the label.", [r"windows?"]),
 "label": ("Label", "The correct answer a model learns to predict.", "Growth, Recovery, Stable or Decline, worked out from the change in impressions over the next 28 days.", [r"labels?"]),
 "features": ("Features", "The input signals a model looks at for each page.", "Signals such as the last-7-day trend, CTR, position and how jumpy the traffic is.", [r"features?"]),
 "recent-slope": ("Recent-slope rule", "A tiny decision tree that uses one signal only: the page’s last-7-day trend compared with its 28-day average.", "A demanding baseline. It shows how much of the model’s skill is just recent momentum.", [r"recent[- ]slope"]),
 "momentum-tree": ("Momentum tree", "A small decision tree using two signals: the last-7-day trend and the change from the previous 28 days.", "The strongest simple baseline in this study.", [r"momentum tree"]),
 "decision-tree": ("Decision tree", "A model that predicts by answering a short chain of yes/no questions about the inputs.", "The simple baselines are small trees that can be read in full.", [r"decision trees?"]),
 "boosting": ("Gradient boosting", "A method that builds many small decision trees one after another, each fixing the mistakes of the ones before.", "The main model. “Histogram” means it groups values into bins first, which makes it fast.", [r"(?:histogram )?gradient boosting"]),
 "interval": ("95% interval", "A range that would contain the true difference about 95 times out of 100 if the study were repeated. If it includes zero, the difference is not reliable.", "Worked out by resampling whole clients.", [r"95% interval"]),
 "resampling": ("Resampling", "Re-drawing random samples from the data many times to see how much a result would wobble.", "Whole clients are redrawn together, because pages on one site are not independent.", [r"resampling"]),
 "lift": ("Lift", "How many times more often something happens in a chosen group than overall.", "A lift of 1.3× means flagged pages declined 1.3 times as often as pages overall.", [r"lift"]),
 "psi": ("Population stability index (PSI)", "A measure of how much a signal’s distribution has shifted between two periods. About 0.1 is small and above 0.25 is large.", "A re-fit trigger: if a key signal passes 0.25, the model should be re-checked.", [r"population stability index", r"PSI"]),
 "rttm": ("Regression to the mean", "Pages with unusually high or low traffic tend to drift back toward average next time, even if nothing is done.", "Part of the signal may be this, because window B sits in both the inputs and the label.", [r"regression to the mean"]),
 "directional": ("Directional", "Shows which way things tend to move, without proving why or by exactly how much.", "How this paper frames its findings.", [r"directional"]),
 "causal": ("Causal", "One thing making another happen. This study only sees patterns, so it cannot show causes.", "The paper makes no causal claims.", [r"causal"]),
 "decision-support": ("Decision-support", "A tool that helps a person decide, rather than deciding for them.", "The ranked list is a starting point for human review, not an automatic action.", [r"decision[- ]support"]),
 "perm": ("Permutation importance", "Shuffle one signal and see how much the score drops. A bigger drop means the model leans on that signal more.", "Shows association, not proof of cause.", [r"permutation importance"]),
 "unseen": ("Unseen clients", "Test pages from sites that were completely absent from training.", "A check that the model does not just memorise particular sites.", [r"unseen clients"]),
 "client": ("Client", "One website (brand) in the dataset.", "Names are hidden. Only coded IDs exist.", [r"clients?"]),
 "hashed": ("Hashed", "Replaced by a one-way code, so the original name cannot be recovered.", "Client and page identifiers are hashed.", [r"pre-hashed", r"hashed"]),
 "seed": ("Seed", "A starting number for random choices, so the same run gives the same result.", "Fixed, so the experiments can be repeated.", [r"seed"]),
 "reason-codes": ("Reason codes", "Short plain labels, like falling_impressions, that say why a page was flagged.", "Worked out from each page’s own recent signals so a person can check them.", [r"reason codes?"]),
 "review": ("review_decline_risk", "A queue slice: pages with the highest predicted chance of declining, weighted by how much traffic they carry.", "The top 5% of pages by that score.", [r"review_decline_risk"]),
 "watch": ("watch_recovery", "A queue slice: pages predicted to bounce back after a fall.", "Look, but do not rewrite a page that is already recovering.", [r"watch_recovery"]),
 "support": ("support_growth", "A queue slice: pages predicted to keep growing.", "Candidates to protect and support.", [r"support_growth"]),
 "recovery": ("Recovery", "An outcome class: a page that fell in the previous window and then rose by at least 25%.", "The rarest and hardest class to predict.", [r"Recovery"]),
 "accuracy": ("Accuracy", "The share of all predictions that were exactly right.", "Secondary, because one outcome is far more common than the others.", [r"accuracy"]),
 "volatility": ("Volatility", "How much a page’s daily traffic jumps around.", "One of the signals.", [r"volatility"]),
 "avg-position": ("Average position", "Where a page typically ranks in search results. 1 is the top.", "Used as a signal, with its change from the previous window.", [r"average position"]),
 "held-out": ("Held-out", "Kept out of training and used only for testing.", "The pages scored in the final test month.", [r"held-out"]),
}

_SKIP = {"script", "style", "code", "a", "h1", "h2", "th", "button"}
_PAT = sorted([(p, k) for k, v in GLOSSARY.items() for p in v[3]], key=lambda x: -len(x[0]))
_RX = re.compile(r"(?<!\w)(?:" + "|".join(f"(?P<g{i}>{p})" for i, (p, _) in enumerate(_PAT)) + r")(?!\w)", re.I)

def add_terms(html_str):
    """Wrap the first occurrence of each glossary term (per tab) in a hoverable span. Text nodes only."""
    seen, depth, out = set(), 0, []
    for tok in re.split(r"(<[^>]+>)", html_str):
        if tok.startswith("<"):
            m = re.match(r"<\s*(/?)\s*([a-zA-Z0-9]+)", tok)
            if m and m.group(2).lower() in _SKIP:
                depth += -1 if m.group(1) else 1
            out.append(tok); continue
        if depth > 0 or not tok.strip():
            out.append(tok); continue
        def rep(m):
            key = _PAT[int(m.lastgroup[1:])][1]
            if key in seen: return m.group(0)
            seen.add(key)
            return f'<span class="term" tabindex="0" data-k="{key}">{m.group(0)}</span>'
        out.append(_RX.sub(rep, tok))
    return "".join(out)

def glossary_html():
    items = sorted(GLOSSARY.values(), key=lambda v: v[0].lower())
    rows = "".join(f"<dt>{e(t)}</dt><dd>{e(d)} <span class=\"small\">In this paper: {e(h)}</span></dd>" for t, d, h, _ in items)
    return f'<h2>9 · Glossary</h2><p class="small">Every dotted word in the paper has a pop-up. They are all collected here too.</p><dl class="gloss">{rows}</dl>'

def nice(name):
    return {"hist_gradient_boosting": "histogram gradient boosting", "logistic_regression": "logistic regression"}.get(name, name.replace("_", " "))

def pct(x): return f"{100*x:.1f}%"
def f3(x): return f"{x:.3f}"

def table(head, rows):
    h = "".join(f"<th>{e(str(c))}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table><tr>{h}</tr>{b}</table></div>'

FILES = {"compare": "macro-f1.png", "confusion": "confusion.png", "importance": "signals.png", "lift": "queue-lift.png"}

def fig(figs, key, cap):
    if key not in figs:
        return ""
    return (f'<figure class="win"><div class="bar"><i></i><i></i><i></i><span>{e(FILES.get(key, key + ".png"))}</span></div>'
            f'<div class="body"><img alt="{e(cap)}" src="data:image/png;base64,{figs[key]}"></div><figcaption>{e(cap)}</figcaption></figure>')

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
    NAME = "Mary Joanna Cathaline S. Dulay"
    nums = [("Model macro F1", f3(m["macro_f1"])),
            ("Best simple baseline · " + final["best_baseline"].replace("_", " "), f3(b["macro_f1"])),
            (f"Difference · 95% interval {lo:+.3f} to {hi:+.3f}", f"{d:+.3f}"),
            ("Held-out pages", f"{final['n_test']:,}")]
    nums_html = '<dl class="nums">' + "".join(f"<div><dt>{e(t)}</dt><dd>{e(v)}</dd></div>" for t, v in nums) + "</dl>"

    overview = f"""<div class="hero"><div>
<h1>Which pages need attention <em class="hl">first?</em></h1>
<p class="subt">Predicting search-visibility momentum from historical signals</p>
<p class="meta">{e(NAME)} · Built on the FlyRank ML Internship dataset</p>
<span class="tag">Abstract</span><p class="lead">{e(abstract)}</p>
<p><a class="btn" href="#results">Read the results</a><a class="btn ghost" href="{e(repo_url)}" target="_blank" rel="noopener">See the code</a></p>
</div>
<div class="win"><div class="bar"><i></i><i></i><i></i><span>sealed-june-test.png</span></div><div class="body">{nums_html}</div></div></div>
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
{fig(figs,'lift','Share of flagged pages that actually declined in the next 28 days (purple = model queue; dashed line = all pages)')}
<p><b>Human review before acting:</b> check for a known cause (seasonality, migration, tracking change); never auto-rewrite, merge or delete a page from this list. <b>Stale triggers:</b> re-evaluate when macro F1 on the newest labelled cutoff drops below the best baseline, or any key feature’s population stability index exceeds 0.25 (current largest: {e(queue['drift_top_feature'])} at {queue['drift_top_psi']:.2f}).</p>"""

    repro = f"""<h2>7 · Reproducibility</h2>
<p>All code is in <a href="{e(repo_url)}" target="_blank" rel="noopener">the project repository</a>: notebooks <code>w04_signal_audit</code>, <code>w05_model</code>, <code>w06_validation_audit</code>, <code>w07_action_playbook</code> and <code>capstone</code> under <code>work/notebooks/</code>, shared code in <code>work/src/</code>. Fixed seed {cfg['seed']}. Rebuilding the page-level tables can reorder rows, so a re-run may differ from the reported scores in the third decimal place.</p>
<h2>8 · Acknowledgments and data credit</h2>
<p>Built on the FlyRank ML Internship dataset — <a href="https://flyrank.ai" target="_blank" rel="noopener">flyrank.ai</a>.</p>"""

    tabs = [("overview", "Overview", overview), ("data", "Data", data), ("method", "Method", method), ("results", "Results", results),
            ("limits", "Limits", limits), ("playbook", "Playbook", playbook), ("repro", "Repro + credit", repro)]
    nav = "".join(f'<a href="#{i}">{e(l)}</a>' for i, l, _ in tabs)
    panels = "".join(f'<section class="panel{" wide" if i == "overview" else ""}" id="{i}" aria-label="{e(l)}">{add_terms(h)}{glossary_html() if i == "repro" else ""}</section>' for i, l, h in tabs)
    gloss_json = json.dumps({k: {"t": v[0], "d": v[1], "h": v[2]} for k, v in GLOSSARY.items()}, ensure_ascii=False).replace("</", "<\\/")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="author" content="{e(NAME)}">
<title>Which pages need attention first? · {e(NAME)}</title><style>{CSS}</style></head><body>
<div class="top"><span class="who">{e(NAME)}</span><span class="what">Research paper · search-visibility momentum</span></div>
<nav>{nav}</nav>
<p class="hint">Words with a <span class="term">dotted underline</span> have a pop-up: hover, tap, or tab to one to see what it means.</p>
<main>{panels}</main>
<footer>Built on the FlyRank ML Internship dataset · <a href="https://flyrank.ai" target="_blank" rel="noopener">flyrank.ai</a></footer>
<script>{JS.replace('__GLOSS__', gloss_json)}</script></body></html>"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    return out_path
