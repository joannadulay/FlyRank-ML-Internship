"""Shared helpers for the capstone: page-level growth / momentum prediction.

Used by w04_signal_audit, w05_model, w06_validation_audit, w07_action_playbook and capstone.
Rules baked in:
  * every feature is computed from rows with report_date <= cutoff (verified in w06)
  * the label uses only the 28 days AFTER the cutoff
  * cutoffs are spaced 28 days apart, so no training label window reaches into a later split
  * the sealed month (test) is only touched by get_final()
  * caches live in CACHE_DIR (outside git); only small metrics JSONs go in work/outputs/
"""
import os, re, json, glob, datetime as dt
import numpy as np
import pandas as pd
import duckdb

REPO_ID = "FlyRank/internship-warehouse"
TABLE_PREFIX = "fact_content_daily_performance"
CACHE_DIR = os.environ.get("CAPSTONE_CACHE", "/content/capstone_cache")
OUT_DIR = "work/outputs"

CFG = dict(
    window_days=28,       # length of each of the three windows A, B, C
    min_avail_days=14,    # GSC-available days required inside A, B and C
    min_impr_B=100,       # impressions needed in B so a % change means something
    change_thr=0.25,      # +/-25% change in impressions per available day
    dev_end="2026-05-31", # last day development may look at
    test_end="2026-06-30",# end of the sealed outcome month
    n_train_cutoffs=4,
    seed=42,
)
CLASSES = ["Growth", "Recovery", "Stable", "Decline"]
FEATURES = [
    "log_rate_B", "d_impr", "r7", "ctr_B", "d_ctr", "pos_B", "d_pos",
    "cv_B", "active_share_B", "avail_share_B", "ga4_cov_B", "eng_per_day_B", "org_per_day_B",
]

# ---------------------------------------------------------------- access / files
def get_access():
    """(hf_token, local_dir). Colab secret HF_TOKEN, else env HF_TOKEN. CAPSTONE_LOCAL points at local parquet (tests)."""
    token = None
    try:
        from google.colab import userdata
        token = userdata.get("HF_TOKEN")
    except Exception:
        token = os.environ.get("HF_TOKEN")
    return token, os.environ.get("CAPSTONE_LOCAL")


def find_month_files(token=None, local_dir=None):
    """{'2026-03': [path, ...]} for the daily-performance table. Prefers the full table over a _sample table."""
    if local_dir:
        files = glob.glob(os.path.join(local_dir, "**", "*.parquet"), recursive=True)
    else:
        from huggingface_hub import HfApi
        files = [f for f in HfApi().list_repo_files(REPO_ID, repo_type="dataset", token=token) if f.endswith(".parquet")]
    out = {}
    for f in files:
        m = re.search(r"month=(\d{4}-\d{2})", f)
        if m and TABLE_PREFIX in f:
            out.setdefault(m.group(1), []).append(f)
    for m, fs in out.items():
        full = [f for f in fs if "_sample" not in f]
        out[m] = full or fs
    return dict(sorted(out.items()))


def fetch_paths(files_by_month, months, token=None, local_dir=None):
    paths = []
    for m in months:
        for f in files_by_month[m]:
            if local_dir:
                paths.append(f)
            else:
                from huggingface_hub import hf_hub_download
                paths.append(hf_hub_download(REPO_ID, f, repo_type="dataset", token=token))
    return paths


def open_panel(paths, max_date=None):
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    plist = ",".join("'%s'" % p for p in paths)
    con.execute(f"""
        CREATE VIEW daily AS SELECT
            client_hash_id AS client, content_hash_id AS content,
            CAST(report_date AS DATE) AS d,
            COALESCE(gsc_data_available, FALSE) AS gsc_ok,
            COALESCE(ga4_data_available, FALSE) AS ga4_ok,
            gsc_impressions AS impr, gsc_clicks AS clk, gsc_sum_position AS sumpos,
            ga4_engaged_sessions AS eng, sessions_organic AS org
        FROM read_parquet([{plist}], union_by_name=true)""" + (f" WHERE CAST(report_date AS DATE) <= DATE '{max_date}'" if max_date else ""))
    return con


def panel_dates(con):
    lo, hi = con.execute("SELECT MIN(d), MAX(d) FROM daily").fetchone()
    return pd.Timestamp(lo).date(), pd.Timestamp(hi).date()

# ---------------------------------------------------------------- cutoff plan
def plan_cutoffs(min_date, max_date, cfg=CFG):
    """Spaced-by-window cutoffs: train (several), val (dev_end-based), test (sealed month)."""
    w = dt.timedelta(days=cfg["window_days"])
    dev_end = min(pd.Timestamp(cfg["dev_end"]).date(), max_date)
    test_end = min(pd.Timestamp(cfg["test_end"]).date(), max_date)
    t_val = dev_end - w
    t_test = test_end - w
    train = [t_val - w * k for k in range(1, cfg["n_train_cutoffs"] + 1)]
    train = [t for t in train if t - 2 * w + dt.timedelta(days=1) >= min_date]
    if not train:
        raise ValueError("Not enough history for even one training cutoff.")
    assert t_test >= t_val + w, "test cutoff must not be inside the validation label window"
    return dict(train=sorted(train), val=t_val, test=t_test, window_days=cfg["window_days"])


def months_needed(plan):
    w = dt.timedelta(days=plan["window_days"])
    start = min(plan["train"]) - 2 * w + dt.timedelta(days=1)
    end = plan["test"] + w
    return sorted({d.strftime("%Y-%m") for d in pd.date_range(start, end)})

# ---------------------------------------------------------------- feature + label frame
def build_cutoff_frame(con, T, cfg=CFG, with_label=True):
    w = cfg["window_days"]; m = cfg["min_avail_days"]
    T = pd.Timestamp(T).date()
    a0, b0, c1, t7 = T - dt.timedelta(days=2 * w), T - dt.timedelta(days=w), T + dt.timedelta(days=w), T - dt.timedelta(days=7)
    A = f"d > DATE '{a0}' AND d <= DATE '{b0}'"
    B = f"d > DATE '{b0}' AND d <= DATE '{T}'"
    B7 = f"d > DATE '{t7}' AND d <= DATE '{T}'"
    C = f"d > DATE '{T}' AND d <= DATE '{c1}'"
    last = c1 if with_label else T
    q = f"""
    SELECT client, content,
      COUNT(*) FILTER (WHERE gsc_ok AND {A}) AS nA, SUM(impr) FILTER (WHERE gsc_ok AND {A}) AS iA,
      SUM(clk) FILTER (WHERE gsc_ok AND {A}) AS cA, SUM(sumpos) FILTER (WHERE gsc_ok AND {A}) AS pA,
      COUNT(*) FILTER (WHERE gsc_ok AND {B}) AS nB, SUM(impr) FILTER (WHERE gsc_ok AND {B}) AS iB,
      SUM(clk) FILTER (WHERE gsc_ok AND {B}) AS cB, SUM(sumpos) FILTER (WHERE gsc_ok AND {B}) AS pB,
      COUNT(*) FILTER (WHERE gsc_ok AND {B7}) AS nB7, SUM(impr) FILTER (WHERE gsc_ok AND {B7}) AS iB7,
      STDDEV_SAMP(impr) FILTER (WHERE gsc_ok AND {B}) AS sdB,
      COUNT(*) FILTER (WHERE gsc_ok AND {B} AND impr > 0) AS nzB,
      COUNT(*) FILTER (WHERE ga4_ok AND {B}) AS g4nB,
      SUM(eng) FILTER (WHERE ga4_ok AND {B}) AS engB, SUM(org) FILTER (WHERE ga4_ok AND {B}) AS orgB,
      COUNT(*) FILTER (WHERE gsc_ok AND {C}) AS nC, SUM(impr) FILTER (WHERE gsc_ok AND {C}) AS iC
    FROM daily WHERE d > DATE '{a0}' AND d <= DATE '{last}'
    GROUP BY client, content"""
    f = con.execute(q).df()
    num = [c for c in f.columns if c not in ("client", "content")]
    f[num] = f[num].astype(float)
    f = f[(f.nA >= m) & (f.nB >= m) & (f.iB >= cfg["min_impr_B"])].copy()
    f["rate_A"] = f.iA / f.nA
    f["rate_B"] = f.iB / f.nB
    f["log_rate_B"] = np.log1p(f.rate_B)
    f["d_impr"] = np.log1p(f.rate_B) - np.log1p(f.rate_A)
    f["r7"] = np.where(f.nB7 >= 3, np.log1p(f.iB7 / f.nB7.where(f.nB7 > 0)) - np.log1p(f.rate_B), np.nan)
    f["ctr_B"] = f.cB / f.iB
    f["d_ctr"] = f.ctr_B - np.where(f.iA > 0, f.cA / f.iA.where(f.iA > 0), np.nan)
    f["pos_B"] = f.pB / f.iB
    f["d_pos"] = f.pos_B - np.where(f.iA > 0, f.pA / f.iA.where(f.iA > 0), np.nan)
    f["cv_B"] = f.sdB / (f.iB / f.nB)
    f["active_share_B"] = f.nzB / f.nB
    f["avail_share_B"] = f.nB / w
    f["ga4_cov_B"] = f.g4nB / w
    ok4 = f.g4nB >= 7
    f["eng_per_day_B"] = np.where(ok4, f.engB / f.g4nB.where(f.g4nB > 0), np.nan)
    f["org_per_day_B"] = np.where(ok4, f.orgB / f.g4nB.where(f.g4nB > 0), np.nan)
    f["cutoff"] = pd.Timestamp(T)
    if with_label:
        f = f[f.nC >= m].copy()
        f["rate_C"] = f.iC / f.nC
        f["r_next"] = f.rate_C / f.rate_B - 1
        f["r_prev"] = f.rate_B / f.rate_A.where(f.rate_A > 0) - 1
        f["r_prev"] = f["r_prev"].fillna(np.inf)   # rate_A == 0 -> any B > 0 is an infinite rise
        thr = cfg["change_thr"]
        f["y"] = np.select(
            [(f.r_next >= thr) & (f.r_prev <= -thr), f.r_next >= thr, f.r_next <= -thr],
            ["Recovery", "Growth", "Decline"], default="Stable")
    keep = ["client", "content", "cutoff", "rate_A", "rate_B", "iB"] + FEATURES + (["r_prev", "r_next", "rate_C", "y"] if with_label else [])
    return f[keep].reset_index(drop=True)


def load_or_build(plan, token=None, local_dir=None, cfg=CFG, force=False):
    """Return {'train','val','test'} frames. Cached under CACHE_DIR (never in git)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    tag = f"{plan['train'][0]}_{plan['val']}_{plan['test']}_{cfg['window_days']}_{cfg['change_thr']}"
    cache = {k: os.path.join(CACHE_DIR, f"frame_{k}_{tag}.parquet") for k in ("train", "val", "test")}
    if not force and all(os.path.exists(p) for p in cache.values()):
        return {k: pd.read_parquet(p) for k, p in cache.items()}
    fbm = find_month_files(token, local_dir)
    need = months_needed(plan)
    missing = [x for x in need if x not in fbm]
    if missing:
        raise FileNotFoundError(f"Months not found in the release: {missing}. Found: {list(fbm)}")
    con = open_panel(fetch_paths(fbm, need, token, local_dir))
    frames = {
        "train": pd.concat([build_cutoff_frame(con, T, cfg) for T in plan["train"]], ignore_index=True),
        "val": build_cutoff_frame(con, plan["val"], cfg),
        "test": build_cutoff_frame(con, plan["test"], cfg),
    }
    for k, p in cache.items():
        frames[k].to_parquet(p)
    return frames


def start(cfg=CFG):
    """One-call setup used by notebooks: returns (plan, frames, token, local_dir)."""
    token, local = get_access()
    fbm = find_month_files(token, local)
    first = pd.Timestamp(min(fbm) + "-01").date()
    last = (pd.Timestamp(max(fbm) + "-01") + pd.offsets.MonthEnd(0)).date()
    plan = plan_cutoffs(first, last, cfg)
    return plan, load_or_build(plan, token, local, cfg), token, local

# ---------------------------------------------------------------- models, baselines, metrics
def make_models(seed=CFG["seed"]):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    return {
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=6, learning_rate=0.08, max_iter=200, class_weight="balanced", random_state=seed),
        "logistic_regression": make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(max_iter=300, class_weight="balanced")),
    }


def baseline_majority(train_y):
    top = pd.Series(train_y).value_counts().idxmax()
    return lambda df: np.full(len(df), top, dtype=object)


def _rule(df, thr, up, down):
    return np.where(df.r_prev >= thr, up, np.where(df.r_prev <= -thr, down, "Stable")).astype(object)


def baseline_persistence(thr=CFG["change_thr"]):
    """Last window's direction continues. Never predicts Recovery (by design)."""
    return lambda df: _rule(df, thr, "Growth", "Decline")


def baseline_mean_reversion(thr=CFG["change_thr"]):
    """Last window's move reverses: a fall -> Recovery, a rise -> Decline."""
    return lambda df: _rule(df, thr, "Decline", "Recovery")


def baseline_recent_slope(train):
    """Strongest simple rule: a depth-3 tree using ONLY r7 (last-7-day level vs the 28-day average). Fit on training data."""
    from sklearn.tree import DecisionTreeClassifier
    tree = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=CFG["seed"])
    tree.fit(train[["r7"]].fillna(-1e9), train["y"])
    return lambda df: tree.predict(df[["r7"]].fillna(-1e9)).astype(object)


def conf_matrix(y, p):
    yi = pd.Categorical(y, categories=CLASSES).codes
    pi = pd.Categorical(p, categories=CLASSES).codes
    C = np.zeros((4, 4), dtype=np.int64)
    np.add.at(C, (yi, pi), 1)
    return C


def macro_f1_from_conf(C):
    tp = np.diag(C).astype(float); fp = C.sum(0) - tp; fn = C.sum(1) - tp
    den = 2 * tp + fp + fn
    f1 = np.divide(2 * tp, den, out=np.zeros_like(tp), where=den > 0)
    return f1.mean(), f1


def score(y, p):
    C = conf_matrix(y, p)
    mf1, per = macro_f1_from_conf(C)
    return dict(macro_f1=float(mf1), accuracy=float(np.trace(C) / C.sum()),
                per_class_f1={c: float(v) for c, v in zip(CLASSES, per)}, confusion=C.tolist(), n=int(C.sum()))


def cluster_bootstrap_diff(y, p_a, p_b, groups, n_boot=300, seed=0):
    """95% interval for macro-F1(a) - macro-F1(b), resampling whole clients (pages in a client are not independent)."""
    g = pd.Categorical(groups).codes
    G = g.max() + 1
    yi = pd.Categorical(y, categories=CLASSES).codes
    def per_group(p):
        pi = pd.Categorical(p, categories=CLASSES).codes
        arr = np.zeros((G, 4, 4), dtype=np.int64)
        np.add.at(arr, (g, yi, pi), 1)
        return arr
    ca, cb = per_group(p_a), per_group(p_b)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, G, G)
        diffs.append(macro_f1_from_conf(ca[idx].sum(0))[0] - macro_f1_from_conf(cb[idx].sum(0))[0])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi)


def fit_predict(model, train, test):
    m = model.fit(train[FEATURES], train["y"])
    return m, m.predict(test[FEATURES])

# ---------------------------------------------------------------- signal-audit helpers
def bucket_table(df, col, target, q=4):
    b = pd.qcut(df[col], q=q, duplicates="drop")
    return df.groupby(b, observed=True).agg(n=(target, "size"), rate=(target, "mean")).round(4)


def auto_verdict(table, expect):
    """expect = 'up' or 'down': the direction the hypothesis says the rate should move across buckets."""
    r = table["rate"].values
    if len(r) < 3 or r.max() - r.min() < 0.01:
        return "FALSE"
    d = np.diff(r)
    if (d >= 0).all() or (d <= 0).all():
        return "CONFIRMED" if (("up" if r[-1] > r[0] else "down") == expect) else "OPPOSITE"
    return "MIXED"

# ---------------------------------------------------------------- final (sealed) test, run once
def get_final(plan, frames, choice):
    """Fit the frozen choice on train+val, score the sealed test cutoff once, cache predictions + metrics."""
    os.makedirs(CACHE_DIR, exist_ok=True); os.makedirs(OUT_DIR, exist_ok=True)
    pred_path = os.path.join(CACHE_DIR, "test_predictions.parquet")
    metrics_path = os.path.join(OUT_DIR, "final_metrics.json")
    if os.path.exists(pred_path) and os.path.exists(metrics_path):
        cached = json.load(open(metrics_path))
        if cached.get("choice") == choice and cached.get("test_cutoff") == str(plan["test"]):
            return pd.read_parquet(pred_path), cached
    trainval = pd.concat([frames["train"], frames["val"]], ignore_index=True)
    test = frames["test"].copy()
    model = make_models()[choice["model"]]
    model.fit(trainval[FEATURES], trainval["y"])
    test["pred_model"] = model.predict(test[FEATURES])
    proba = model.predict_proba(test[FEATURES])
    for c in CLASSES:
        test[f"p_{c}"] = 0.0
    for i, c in enumerate(model.classes_):
        test[f"p_{c}"] = proba[:, i]
    base_fns = {"majority": baseline_majority(trainval["y"]), "persistence": baseline_persistence(),
                "mean_reversion": baseline_mean_reversion(), "recent_slope": baseline_recent_slope(trainval)}
    for k, fn in base_fns.items():
        test[f"pred_{k}"] = fn(test)
    res = {"choice": choice, "model": choice["model"], "n_test": int(len(test)), "n_clients_test": int(test.client.nunique()),
           "test_cutoff": str(plan["test"]), "class_share_test": test.y.value_counts(normalize=True).round(4).to_dict(),
           "model_scores": score(test.y, test.pred_model), "baselines": {}}
    for k in base_fns:
        res["baselines"][k] = score(test.y, test[f"pred_{k}"])
    best = choice["baseline"]
    res["best_baseline"] = best
    res["diff_vs_best_baseline"] = res["model_scores"]["macro_f1"] - res["baselines"][best]["macro_f1"]
    res["diff_ci95"] = cluster_bootstrap_diff(test.y.values, test.pred_model.values, test[f"pred_{best}"].values, test.client.values)
    test.to_parquet(pred_path)
    json.dump(res, open(metrics_path, "w"), indent=1)
    return test, res


# ---------------------------------------------------------------- audits used by w06 / capstone
def verify_no_future(paths, T, cfg=CFG):
    """Leakage test: features at cutoff T must be identical when every row after T is physically removed."""
    full = build_cutoff_frame(open_panel(paths), T, cfg, with_label=False)
    cut = build_cutoff_frame(open_panel(paths, max_date=T), T, cfg, with_label=False)
    mrg = full.merge(cut, on=["client", "content"], suffixes=("_full", "_cut"))
    diffs = {f: float(np.nanmax(np.abs(mrg[f + "_full"] - mrg[f + "_cut"]))) if len(mrg) else 0.0 for f in FEATURES}
    return dict(n_full=len(full), n_cut=len(cut), n_both=len(mrg), max_abs_diff=max(diffs.values()), per_feature=diffs)


def funnel(con, T, cfg=CFG):
    """How many pages survive each exclusion at cutoff T (counts only, public-safe)."""
    w = cfg["window_days"]; m = cfg["min_avail_days"]
    T = pd.Timestamp(T).date()
    b0, a0, c1 = T - dt.timedelta(days=w), T - dt.timedelta(days=2 * w), T + dt.timedelta(days=w)
    q = f"""
    WITH p AS (SELECT client, content,
      COUNT(*) FILTER (WHERE gsc_ok AND d > DATE '{a0}' AND d <= DATE '{b0}') AS nA,
      COUNT(*) FILTER (WHERE gsc_ok AND d > DATE '{b0}' AND d <= DATE '{T}') AS nB,
      SUM(impr) FILTER (WHERE gsc_ok AND d > DATE '{b0}' AND d <= DATE '{T}') AS iB,
      COUNT(*) FILTER (WHERE gsc_ok AND d > DATE '{T}' AND d <= DATE '{c1}') AS nC
      FROM daily WHERE d > DATE '{a0}' AND d <= DATE '{c1}' GROUP BY client, content)
    SELECT COUNT(*) AS pages_seen,
      COUNT(*) FILTER (WHERE nB >= {m}) AS gsc_ok_in_B,
      COUNT(*) FILTER (WHERE nB >= {m} AND nA >= {m}) AS and_in_A,
      COUNT(*) FILTER (WHERE nB >= {m} AND nA >= {m} AND iB >= {cfg['min_impr_B']}) AS and_enough_impr,
      COUNT(*) FILTER (WHERE nB >= {m} AND nA >= {m} AND iB >= {cfg['min_impr_B']} AND nC >= {m}) AS and_in_C_final
    FROM p"""
    return con.execute(q).df().iloc[0].astype(int).to_dict()


def psi(expected, actual, bins=10):
    """Population stability index of one feature between two samples (0.1 small, 0.25 large shift: rule of thumb)."""
    e, a = pd.Series(expected).dropna(), pd.Series(actual).dropna()
    edges = np.unique(np.quantile(e, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    pe = np.histogram(e, edges)[0] / len(e) + 1e-6
    pa = np.histogram(a, edges)[0] / len(a) + 1e-6
    return float(np.sum((pa - pe) * np.log(pa / pe)))
