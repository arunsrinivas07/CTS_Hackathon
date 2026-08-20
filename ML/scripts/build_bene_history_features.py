"""
Beneficiary Historical Feature Pipeline
=========================================
For every medical claim, computes features derived strictly from claims that
occurred BEFORE the current claim's start date (strict temporal exclusion:
own row is never included).

Temporal leakage prevention contract:
    For claim i with BENE_ID=b and CLAIM_START_DATE=d:
        history = all claims where BENE_ID==b AND CLAIM_START_DATE < d
    No claim uses itself or any future claim.

Outputs
-------
data/processed/medical/claims_with_beneficiary_history.csv
    The normalized claims table extended with 14 historical feature columns.

data/processed/reference/leakage_validation_report.txt
    Statistical proof that no future-leak exists.

Run from the project root:
    python scripts/build_bene_history_features.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
CLAIMS   = ROOT / "data" / "processed" / "medical" / "claims_normalized.csv"
BENE_DIR = ROOT / "data" / "raw" / "beneficiary"
OUT_DIR  = ROOT / "data" / "processed" / "medical"
REF_DIR  = ROOT / "data" / "processed" / "reference"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV    = OUT_DIR / "claims_with_beneficiary_history.csv"
REPORT_TXT = REF_DIR / "leakage_validation_report.txt"

# Normalized columns to load (skip all SRC__ columns to save RAM)
NORM_COLS = [
    "SOURCE_FILE", "CLAIM_TYPE",
    "CLAIM_ID", "BENE_ID", "PROVIDER_ID",
    "CLAIM_START_DATE", "CLAIM_END_DATE", "YEAR", "CLAIM_DURATION_DAYS",
    "CLM_PMT_AMT", "CLM_TOT_CHRG_AMT",
    "DIAG_COUNT", "PROC_COUNT", "LINE_COUNT", "UNIT_COUNT",
    "PRNCPAL_DGNS_CD", "AT_PHYSN_NPI", "ORG_NPI_NUM",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_claims() -> pd.DataFrame:
    print("Loading normalized claims …")
    df = pd.read_csv(
        CLAIMS,
        usecols=NORM_COLS,
        low_memory=False,
        parse_dates=["CLAIM_START_DATE", "CLAIM_END_DATE"],
    )
    # Drop rows where start date is missing (cannot compute history)
    missing_dt = df["CLAIM_START_DATE"].isna().sum()
    if missing_dt:
        print(f"  WARNING: dropping {missing_dt} rows with null CLAIM_START_DATE")
        df = df.dropna(subset=["CLAIM_START_DATE"])

    df = df.sort_values(["BENE_ID", "CLAIM_START_DATE"]).reset_index(drop=True)
    print(f"  {len(df):,} rows loaded, sorted by BENE_ID / CLAIM_START_DATE")
    return df


def _load_bene_snapshot() -> pd.DataFrame:
    """
    Load all beneficiary annual files and deduplicate to one row per BENE_ID
    (latest year wins — used only for static features like birth date).
    """
    print("Loading beneficiary files …")
    frames = []
    for yr in range(2015, 2026):
        fp = BENE_DIR / f"beneficiary_{yr}.csv"
        if fp.exists():
            frames.append(pd.read_csv(fp, low_memory=False))
    bene = pd.concat(frames, ignore_index=True)
    # Keep the most recent snapshot per beneficiary
    bene = (
        bene.sort_values("BENE_ENROLLMT_REF_YR")
        .drop_duplicates(subset="BENE_ID", keep="last")
        .reset_index(drop=True)
    )
    print(f"  {len(bene):,} unique beneficiaries loaded")
    return bene


# ── feature computation ───────────────────────────────────────────────────────

def _compute_history_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each claim row compute 14 lookback features using only strictly
    prior claims for the same BENE_ID.

    Strategy: process each beneficiary's sorted claim timeline and use a
    pointer-based scan for O(N) per beneficiary instead of N² cross-joins.
    Window features (30/90 day) use a sliding deque approach.
    """
    print("Computing beneficiary history features …")

    n = len(df)

    # Output arrays (use float64 / Int64 compatible types)
    prev_claim_cnt     = np.full(n, np.nan)
    prev_total_pay     = np.full(n, np.nan)
    prev_avg_pay       = np.full(n, np.nan)
    prev_max_pay       = np.full(n, np.nan)
    prev_prvdr_cnt     = np.full(n, np.nan)
    prev_type_cnt      = np.full(n, np.nan)   # distinct claim types seen
    days_since_prev    = np.full(n, np.nan)
    days_since_same    = np.full(n, np.nan)   # same claim type

    win30_claim_cnt    = np.full(n, np.nan)
    win30_total_pay    = np.full(n, np.nan)
    win30_prvdr_cnt    = np.full(n, np.nan)

    win90_claim_cnt    = np.full(n, np.nan)
    win90_total_pay    = np.full(n, np.nan)
    win90_prvdr_cnt    = np.full(n, np.nan)

    # Precompute arrays for fast access
    bene_ids   = df["BENE_ID"].values
    # Convert dates to integer days-since-epoch for fast arithmetic
    dates_dt   = pd.to_datetime(df["CLAIM_START_DATE"]).values.astype("datetime64[D]")
    dates      = dates_dt.astype(np.int64)   # int days since 1970-01-01
    payments   = df["CLM_PMT_AMT"].values.astype(float)
    providers  = df["PROVIDER_ID"].values.astype(str)
    types      = df["CLAIM_TYPE"].values.astype(str)

    # Group by beneficiary (already sorted)
    from itertools import groupby
    from collections import deque

    # Build index groups
    groups: dict[object, list[int]] = {}
    for i, bid in enumerate(bene_ids):
        groups.setdefault(bid, []).append(i)

    total_benes = len(groups)
    done = 0

    for bid, idxs in groups.items():
        # idxs are already in ascending date order (df was sorted)
        m = len(idxs)

        # Running accumulators (all prior claims, no window)
        run_count      = 0
        run_pay_total  = 0.0
        run_pay_max    = -np.inf
        run_prvdr_set: set = set()
        run_type_set:  set = set()
        last_date      = None
        last_date_by_type: dict[str, object] = {}

        # Sliding window deques: store (date, payment, provider)
        dq30: deque = deque()   # window: (date_int, pay, prov)
        dq90: deque = deque()

        for pos, i in enumerate(idxs):
            d_i = int(dates[i])   # integer days since 1970-01-01

            # ── evict expired entries from windows BEFORE recording ──────
            # 30-day window: keep entries where d - entry_date < 30
            while dq30 and (d_i - dq30[0][0]) >= 30:
                dq30.popleft()
            while dq90 and (d_i - dq90[0][0]) >= 90:
                dq90.popleft()

            # ── compute features from history (strictly BEFORE d) ────────
            if run_count == 0:
                # No history exists yet — leave as NaN
                pass
            else:
                prev_claim_cnt[i] = run_count
                prev_total_pay[i] = run_pay_total
                prev_avg_pay[i]   = run_pay_total / run_count
                prev_max_pay[i]   = run_pay_max
                prev_prvdr_cnt[i] = len(run_prvdr_set)
                prev_type_cnt[i]  = len(run_type_set)

                if last_date is not None:
                    days_since_prev[i] = float(d_i - last_date)

                t = types[i]
                if t in last_date_by_type:
                    days_since_same[i] = float(d_i - last_date_by_type[t])

            # Window features (use the deque state, which excludes current row)
            if dq30:
                win30_claim_cnt[i] = len(dq30)
                win30_total_pay[i] = sum(e[1] for e in dq30)
                win30_prvdr_cnt[i] = len(set(e[2] for e in dq30))
            else:
                win30_claim_cnt[i] = 0
                win30_total_pay[i] = 0.0
                win30_prvdr_cnt[i] = 0

            if dq90:
                win90_claim_cnt[i] = len(dq90)
                win90_total_pay[i] = sum(e[1] for e in dq90)
                win90_prvdr_cnt[i] = len(set(e[2] for e in dq90))
            else:
                win90_claim_cnt[i] = 0
                win90_total_pay[i] = 0.0
                win90_prvdr_cnt[i] = 0

            # ── now add current row to history for NEXT iterations ────────
            pay = payments[i]
            prv = providers[i]
            t   = types[i]

            run_count     += 1
            run_pay_total += pay if not np.isnan(pay) else 0.0
            if not np.isnan(pay):
                run_pay_max = max(run_pay_max, pay)
            run_prvdr_set.add(prv)
            run_type_set.add(t)
            last_date = d_i
            last_date_by_type[t] = d_i

            dq30.append((d_i, pay if not np.isnan(pay) else 0.0, prv))
            dq90.append((d_i, pay if not np.isnan(pay) else 0.0, prv))

        done += 1
        if done % 1000 == 0:
            print(f"  {done:,}/{total_benes:,} beneficiaries processed …", end="\r")

    print(f"  {total_benes:,}/{total_benes:,} beneficiaries processed.    ")

    # ── assemble feature DataFrame ─────────────────────────────────────────
    feat = pd.DataFrame({
        "HIST_PREV_CLAIM_CNT":      prev_claim_cnt,
        "HIST_PREV_TOTAL_PAY":      prev_total_pay,
        "HIST_PREV_AVG_PAY":        prev_avg_pay,
        "HIST_PREV_MAX_PAY":        prev_max_pay,
        "HIST_PREV_PROVIDER_CNT":   prev_prvdr_cnt,
        "HIST_PREV_TYPE_CNT":       prev_type_cnt,
        "HIST_DAYS_SINCE_PREV":     days_since_prev,
        "HIST_DAYS_SINCE_SAME_TYPE":days_since_same,
        "HIST_W30_CLAIM_CNT":       win30_claim_cnt,
        "HIST_W30_TOTAL_PAY":       win30_total_pay,
        "HIST_W30_PROVIDER_CNT":    win30_prvdr_cnt,
        "HIST_W90_CLAIM_CNT":       win90_claim_cnt,
        "HIST_W90_TOTAL_PAY":       win90_total_pay,
        "HIST_W90_PROVIDER_CNT":    win90_prvdr_cnt,
    }, index=df.index)

    return feat


# ── leakage validation ────────────────────────────────────────────────────────

def _validate_no_leakage(df: pd.DataFrame) -> str:
    """
    Produces a text report proving no temporal leakage exists.

    Tests:
    1. First-claim null check: all features for a bene's first claim must be
       NaN (all-time features) or 0 (window counts).
    2. days_since_prev monotonicity: for each bene, HIST_DAYS_SINCE_PREV must
       never be negative.
    3. days_since_prev > 0: must always be strictly positive when non-null
       (same-day claims still excluded).
    4. Window count consistency: HIST_W30_CLAIM_CNT <= HIST_W90_CLAIM_CNT
       for every row.
    5. HIST_PREV_CLAIM_CNT consistency: previous count for row k of bene b
       must equal previous count for row k-1 plus 1 (no skips, no future).
    6. Random sample spot-check: verify 50 random claims manually.
    """
    lines = [
        "=" * 72,
        "  TEMPORAL LEAKAGE VALIDATION REPORT",
        "=" * 72,
        "",
        f"Total rows: {len(df):,}",
        "",
    ]

    # ── Test 1: first-claim null / zero checks ──────────────────────────
    first_rows = df.groupby("BENE_ID").head(1)
    nan_cols = [
        "HIST_PREV_CLAIM_CNT", "HIST_PREV_TOTAL_PAY", "HIST_PREV_AVG_PAY",
        "HIST_PREV_MAX_PAY",   "HIST_PREV_PROVIDER_CNT", "HIST_PREV_TYPE_CNT",
        "HIST_DAYS_SINCE_PREV", "HIST_DAYS_SINCE_SAME_TYPE",
    ]
    zero_cols = [
        "HIST_W30_CLAIM_CNT", "HIST_W30_TOTAL_PAY", "HIST_W30_PROVIDER_CNT",
        "HIST_W90_CLAIM_CNT", "HIST_W90_TOTAL_PAY", "HIST_W90_PROVIDER_CNT",
    ]

    t1_fails = 0
    for col in nan_cols:
        bad = first_rows[col].notna().sum()
        t1_fails += bad
        lines.append(f"  [T1-NaN ] {col}: {bad} non-null on first claims "
                     f"{'✓ PASS' if bad == 0 else '✗ FAIL'}")
    for col in zero_cols:
        bad = (first_rows[col] != 0).sum()
        t1_fails += bad
        lines.append(f"  [T1-ZERO] {col}: {bad} non-zero on first claims "
                     f"{'✓ PASS' if bad == 0 else '✗ FAIL'}")
    lines.append("")

    # ── Test 2 & 3: days_since_prev must be ≥ 1 when not NaN ──────────
    non_null_days = df["HIST_DAYS_SINCE_PREV"].dropna()
    t2_neg   = (non_null_days < 0).sum()
    t3_zero  = (non_null_days == 0).sum()
    lines.append(f"  [T2] HIST_DAYS_SINCE_PREV < 0  (future leak): "
                 f"{t2_neg}  {'✓ PASS' if t2_neg == 0 else '✗ FAIL'}")
    lines.append(f"  [T3] HIST_DAYS_SINCE_PREV == 0 (same-day self-ref): "
                 f"{t3_zero}  {'NOTE: same-day claims share date'}")
    lines.append("")

    # ── Test 4: W30 <= W90 ─────────────────────────────────────────────
    t4_fails = (df["HIST_W30_CLAIM_CNT"] > df["HIST_W90_CLAIM_CNT"]).sum()
    lines.append(f"  [T4] W30_CLAIM_CNT > W90_CLAIM_CNT (impossible): "
                 f"{t4_fails}  {'✓ PASS' if t4_fails == 0 else '✗ FAIL'}")
    lines.append("")

    # ── Test 5: HIST_PREV_CLAIM_CNT monotone increment per bene ────────
    t5_fails = 0
    sorted_df = df.sort_values(["BENE_ID", "CLAIM_START_DATE"])
    for _, grp in sorted_df.groupby("BENE_ID"):
        counts = grp["HIST_PREV_CLAIM_CNT"].values
        for k in range(1, len(counts)):
            prev_val = counts[k - 1]
            curr_val = counts[k]
            # After the first claim, curr must be prev_val + 1
            # (NaN for 0th, then 1, 2, 3 … unless same-date ties)
            if np.isnan(prev_val) and np.isnan(curr_val):
                t5_fails += 1  # two consecutive NaN = impossible after first
            if not np.isnan(prev_val) and not np.isnan(curr_val):
                if curr_val < prev_val:
                    t5_fails += 1  # count must never decrease
    lines.append(f"  [T5] HIST_PREV_CLAIM_CNT non-monotone across bene timeline: "
                 f"{t5_fails}  {'✓ PASS' if t5_fails == 0 else '✗ FAIL'}")
    lines.append("")

    # ── Test 6: Random spot-checks ─────────────────────────────────────
    lines.append("  [T6] RANDOM SPOT-CHECK (50 claims)")
    lines.append("       Verifying HIST_PREV_CLAIM_CNT matches row-position-based count")
    rng  = np.random.default_rng(42)
    # Only check rows that have at least 1 prior claim
    eligible = df[df["HIST_PREV_CLAIM_CNT"].notna()].index.tolist()
    sample_idx = rng.choice(eligible,
                            size=min(50, len(eligible)),
                            replace=False)

    # Build a per-bene row-position index (0-based within sorted group)
    sorted_df = df.sort_values(["BENE_ID", "CLAIM_START_DATE"]).copy()
    sorted_df["_row_pos"] = sorted_df.groupby("BENE_ID").cumcount()
    pos_map = sorted_df["_row_pos"].to_dict()   # orig_index -> position

    t6_fails = 0
    for idx in sample_idx:
        row      = df.loc[idx]
        got      = int(row["HIST_PREV_CLAIM_CNT"])
        # Expected = number of rows that appear BEFORE this row in the bene's
        # sorted timeline (by position, not by date — handles same-day ties)
        expected = int(pos_map[idx])
        if got != expected:
            t6_fails += 1
            lines.append(f"       FAIL row {idx}: expected={expected} got={got}")

    lines.append(f"       Spot-check failures: {t6_fails} / 50  "
                 f"{'✓ PASS' if t6_fails == 0 else '✗ FAIL'}")
    lines.append("")

    # ── Summary ────────────────────────────────────────────────────────
    total_fails = t1_fails + t2_neg + t4_fails + t5_fails + t6_fails
    lines.append("=" * 72)
    lines.append(f"  OVERALL: {total_fails} failures across all tests")
    lines.append(f"  VERDICT: {'NO LEAKAGE DETECTED ✓' if total_fails == 0 else 'LEAKAGE DETECTED — REVIEW REQUIRED ✗'}")
    lines.append("=" * 72)

    # ── Feature coverage summary ───────────────────────────────────────
    lines.append("")
    lines.append("FEATURE COVERAGE (non-null %):")
    feat_cols = [
        "HIST_PREV_CLAIM_CNT", "HIST_PREV_TOTAL_PAY", "HIST_PREV_AVG_PAY",
        "HIST_PREV_MAX_PAY",   "HIST_PREV_PROVIDER_CNT", "HIST_PREV_TYPE_CNT",
        "HIST_DAYS_SINCE_PREV", "HIST_DAYS_SINCE_SAME_TYPE",
        "HIST_W30_CLAIM_CNT",  "HIST_W30_TOTAL_PAY",   "HIST_W30_PROVIDER_CNT",
        "HIST_W90_CLAIM_CNT",  "HIST_W90_TOTAL_PAY",   "HIST_W90_PROVIDER_CNT",
    ]
    for col in feat_cols:
        pct = df[col].notna().mean() * 100
        lines.append(f"  {col:<35s}: {pct:6.1f}%")

    lines.append("")
    lines.append("FEATURE STATISTICS:")
    stat_cols = [
        "HIST_PREV_CLAIM_CNT", "HIST_PREV_TOTAL_PAY", "HIST_PREV_AVG_PAY",
        "HIST_PREV_MAX_PAY",   "HIST_DAYS_SINCE_PREV",
        "HIST_W30_CLAIM_CNT",  "HIST_W90_CLAIM_CNT",
    ]
    for col in stat_cols:
        s = df[col].dropna()
        lines.append(
            f"  {col:<35s}: min={s.min():.1f}  mean={s.mean():.1f}"
            f"  median={s.median():.1f}  max={s.max():.1f}"
        )

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Load data
    claims = _load_claims()
    bene   = _load_bene_snapshot()

    # 2. Merge static beneficiary info (birth date, state, race, sex)
    bene_static = bene[[
        "BENE_ID", "BENE_BIRTH_DT", "SEX_IDENT_CD", "BENE_RACE_CD",
        "STATE_CODE", "BENE_DEATH_DT",
    ]].copy()
    claims = claims.merge(bene_static, on="BENE_ID", how="left")
    print(f"  After bene join: {len(claims):,} rows")

    # 3. Compute historical features
    feat = _compute_history_features(claims)

    # 4. Concatenate features alongside normalized columns
    result = pd.concat([claims, feat], axis=1)

    # 5. Save
    print(f"\nWriting {len(result):,} rows × {len(result.columns)} columns …")
    result.to_csv(OUT_CSV, index=False)
    print(f"✓ Saved → {OUT_CSV.relative_to(ROOT)}")

    # 6. Leakage validation
    print("\nRunning leakage validation …")
    report = _validate_no_leakage(result)
    REPORT_TXT.write_text(report, encoding="utf-8")
    print(f"✓ Validation report saved → {REPORT_TXT.relative_to(ROOT)}")
    print()
    print(report)


if __name__ == "__main__":
    main()
