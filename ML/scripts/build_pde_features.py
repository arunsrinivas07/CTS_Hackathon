"""
PDE Feature Engineering Pipeline
==================================
Reads data/raw/pde/pde.csv (read-only) and produces a transaction-level
feature table at data/processed/pde/pde_features.csv.

PDE data is kept completely separate from the seven medical claim types.

Features produced
-----------------
Pass-through transaction fields:
    QTY_DSPNSD_NUM, DAYS_SUPLY_NUM, FILL_NUM, TOT_RX_CST_AMT,
    PTNT_PAY_AMT, CVRD_D_PLAN_PD_AMT, NCVRD_PLAN_PD_AMT,
    GDC_BLW_OOPT_AMT, GDC_ABV_OOPT_AMT, OTHR_TROOP_AMT,
    LICS_AMT, PLRO_AMT

Derived transaction features:
    COST_PER_UNIT           = TOT_RX_CST_AMT / QTY_DSPNSD_NUM
    COST_PER_DAY            = TOT_RX_CST_AMT / DAYS_SUPLY_NUM
    PATIENT_PAYMENT_RATIO   = PTNT_PAY_AMT   / TOT_RX_CST_AMT
    PLAN_PAYMENT_RATIO      = CVRD_D_PLAN_PD_AMT / TOT_RX_CST_AMT
    QUANTITY_PER_DAY        = QTY_DSPNSD_NUM / DAYS_SUPLY_NUM
    DAYS_SUPPLY             = DAYS_SUPLY_NUM  (alias for clarity)
    REFILL_FREQUENCY        = FILL_NUM (refill number; 0=initial)

Beneficiary historical prescription features (strictly prior rows only):
    BENE_PREV_RX_COUNT      cumulative prior Rx count
    BENE_PREV_RX_COST       cumulative prior total cost
    BENE_PREV_AVG_RX_COST   cumulative prior average cost
    BENE_PREV_MAX_RX_COST   cumulative prior max cost
    BENE_RX_30D             Rx count in the 30 days before this fill
    BENE_RX_COST_30D        total cost in the 30-day window
    BENE_RX_90D             Rx count in the 90-day window
    BENE_RX_COST_90D        total cost in the 90-day window

Prescriber historical features (strictly prior rows only):
    PRESCRIBER_RX_COUNT             cumulative prior Rx count
    PRESCRIBER_AVG_RX_COST          cumulative prior average cost
    PRESCRIBER_MAX_RX_COST          cumulative prior max cost
    PRESCRIBER_UNIQUE_BENEFICIARIES cumulative prior unique patients

Temporal leakage prevention:
    For row i with SRVC_DT = d and BENE_ID = b:
        history = all rows where BENE_ID == b AND SRVC_DT < d (row-position order)
    Same logic applied for prescriber features.
    A row never uses itself or any later row.

Run from project root:
    python scripts/build_pde_features.py
"""

import warnings
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
PDE_CSV = ROOT / "data" / "raw" / "pde" / "pde.csv"
OUT_DIR = ROOT / "data" / "processed" / "pde"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "pde_features.csv"

# Feature columns to pass through directly
PASSTHROUGH_COLS = [
    "QTY_DSPNSD_NUM", "DAYS_SUPLY_NUM", "FILL_NUM",
    "TOT_RX_CST_AMT", "PTNT_PAY_AMT", "CVRD_D_PLAN_PD_AMT",
    "NCVRD_PLAN_PD_AMT", "GDC_BLW_OOPT_AMT", "GDC_ABV_OOPT_AMT",
    "OTHR_TROOP_AMT", "LICS_AMT", "PLRO_AMT",
]

# Source identifiers kept for downstream joining / validation
ID_COLS = ["PDE_ID", "BENE_ID", "PRSCRBR_ID", "SRVC_DT", "PROD_SRVC_ID",
           "BRND_GNRC_CD", "CMPND_CD", "DAW_PROD_SLCTN_CD",
           "DRUG_CVRG_STUS_CD", "PHRMCY_SRVC_TYPE_CD", "PTNT_RSDNC_CD"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, np.nan)


def _compute_bene_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute cumulative and windowed beneficiary history features.
    Uses pointer-based O(N) scan per beneficiary (sorted by SRVC_DATE_INT).
    Current row is added to history AFTER features are read out.
    """
    n = len(df)
    print("  Computing beneficiary history features …")

    bene_ids  = df["BENE_ID"].values
    dates_int = df["SRVC_DATE_INT"].values          # integer days since epoch
    costs     = df["TOT_RX_CST_AMT"].values.astype(float)

    # Output arrays
    prev_cnt     = np.full(n, np.nan)
    prev_cost    = np.full(n, np.nan)
    prev_avg     = np.full(n, np.nan)
    prev_max     = np.full(n, np.nan)
    w30_cnt      = np.zeros(n, dtype=float)
    w30_cost     = np.zeros(n, dtype=float)
    w90_cnt      = np.zeros(n, dtype=float)
    w90_cost     = np.zeros(n, dtype=float)

    # Build index groups (already sorted by bene + date in caller)
    groups: dict = {}
    for i, bid in enumerate(bene_ids):
        groups.setdefault(bid, []).append(i)

    n_benes = len(groups)
    done = 0

    for bid, idxs in groups.items():
        run_count  = 0
        run_cost   = 0.0
        run_max    = -np.inf
        dq30: deque = deque()   # (date_int, cost)
        dq90: deque = deque()

        for pos, i in enumerate(idxs):
            d_i  = int(dates_int[i])
            cost = costs[i]

            # Evict expired window entries BEFORE reading features
            while dq30 and (d_i - dq30[0][0]) >= 30:
                dq30.popleft()
            while dq90 and (d_i - dq90[0][0]) >= 90:
                dq90.popleft()

            # Write features from history accumulated so far
            if run_count > 0:
                prev_cnt[i]  = run_count
                prev_cost[i] = run_cost
                prev_avg[i]  = run_cost / run_count
                prev_max[i]  = run_max

            w30_cnt[i]  = len(dq30)
            w30_cost[i] = sum(e[1] for e in dq30)
            w90_cnt[i]  = len(dq90)
            w90_cost[i] = sum(e[1] for e in dq90)

            # Add current row to history
            c = cost if not np.isnan(cost) else 0.0
            run_count  += 1
            run_cost   += c
            if not np.isnan(cost):
                run_max = max(run_max, cost)
            dq30.append((d_i, c))
            dq90.append((d_i, c))

        done += 1
        if done % 1000 == 0:
            print(f"    {done:,}/{n_benes:,} benes …", end="\r")

    print(f"    {n_benes:,}/{n_benes:,} benes done.    ")

    return pd.DataFrame({
        "BENE_PREV_RX_COUNT":    prev_cnt,
        "BENE_PREV_RX_COST":     prev_cost,
        "BENE_PREV_AVG_RX_COST": prev_avg,
        "BENE_PREV_MAX_RX_COST": prev_max,
        "BENE_RX_30D":           w30_cnt,
        "BENE_RX_COST_30D":      w30_cost,
        "BENE_RX_90D":           w90_cnt,
        "BENE_RX_COST_90D":      w90_cost,
    }, index=df.index)


def _compute_prescriber_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute prescriber-level cumulative features using only prior rows.
    Sorted by PRSCRBR_ID + SRVC_DATE_INT.
    """
    n = len(df)
    print("  Computing prescriber history features …")

    prscrbr_ids = df["PRSCRBR_ID"].values
    dates_int   = df["SRVC_DATE_INT"].values
    costs       = df["TOT_RX_CST_AMT"].values.astype(float)
    bene_ids    = df["BENE_ID"].values

    rx_cnt       = np.full(n, np.nan)
    avg_cost     = np.full(n, np.nan)
    max_cost     = np.full(n, np.nan)
    uniq_benes   = np.full(n, np.nan)

    groups: dict = {}
    for i, pid in enumerate(prscrbr_ids):
        groups.setdefault(pid, []).append(i)

    n_prscr = len(groups)
    done = 0

    for pid, idxs in groups.items():
        # Sort by date within prescriber
        idxs_sorted = sorted(idxs, key=lambda i: dates_int[i])

        run_count   = 0
        run_cost    = 0.0
        run_max     = -np.inf
        run_benes: set = set()

        for i in idxs_sorted:
            if run_count > 0:
                rx_cnt[i]     = run_count
                avg_cost[i]   = run_cost / run_count
                max_cost[i]   = run_max
                uniq_benes[i] = len(run_benes)

            # Add current row
            c = costs[i] if not np.isnan(costs[i]) else 0.0
            run_count += 1
            run_cost  += c
            if not np.isnan(costs[i]):
                run_max = max(run_max, costs[i])
            run_benes.add(bene_ids[i])

        done += 1
        if done % 500 == 0:
            print(f"    {done:,}/{n_prscr:,} prescribers …", end="\r")

    print(f"    {n_prscr:,}/{n_prscr:,} prescribers done.    ")

    return pd.DataFrame({
        "PRESCRIBER_RX_COUNT":             rx_cnt,
        "PRESCRIBER_AVG_RX_COST":          avg_cost,
        "PRESCRIBER_MAX_RX_COST":          max_cost,
        "PRESCRIBER_UNIQUE_BENEFICIARIES": uniq_benes,
    }, index=df.index)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Load raw PDE ───────────────────────────────────────────────────
    print("Loading raw PDE …")
    df = pd.read_csv(PDE_CSV, low_memory=False)
    print(f"  {len(df):,} rows × {len(df.columns)} columns")

    # ── 2. Parse service date ─────────────────────────────────────────────
    df["SRVC_DATE"] = pd.to_datetime(
        df["SRVC_DT"], format="%d-%b-%Y", errors="coerce"
    )
    null_dates = df["SRVC_DATE"].isna().sum()
    if null_dates > 0:
        print(f"  WARNING: {null_dates} null service dates — dropping")
        df = df.dropna(subset=["SRVC_DATE"]).reset_index(drop=True)

    df["SRVC_DATE_INT"] = df["SRVC_DATE"].values.astype("datetime64[D]").astype(np.int64)
    df["YEAR"] = df["SRVC_DATE"].dt.year
    print(f"  Date range: {df['SRVC_DATE'].min().date()} → {df['SRVC_DATE'].max().date()}")
    print(f"  Year distribution:")
    for yr, cnt in df["YEAR"].value_counts().sort_index().items():
        print(f"    {yr}: {cnt:>7,}")

    # ── 3. Sort by BENE_ID + SRVC_DATE_INT for history computation ────────
    print("\nSorting by BENE_ID + SRVC_DATE_INT …")
    df = df.sort_values(["BENE_ID", "SRVC_DATE_INT"]).reset_index(drop=True)

    # ── 4. Numeric cast for all amount/quantity cols ───────────────────────
    for col in PASSTHROUGH_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 5. Derived transaction features ───────────────────────────────────
    print("Computing derived transaction features …")
    qty  = df["QTY_DSPNSD_NUM"]
    days = df["DAYS_SUPLY_NUM"]
    cost = df["TOT_RX_CST_AMT"]
    pmt  = df["PTNT_PAY_AMT"]
    plan = df["CVRD_D_PLAN_PD_AMT"]

    df["COST_PER_UNIT"]         = _safe_div(cost, qty)
    df["COST_PER_DAY"]          = _safe_div(cost, days)
    df["PATIENT_PAYMENT_RATIO"] = _safe_div(pmt,  cost)
    df["PLAN_PAYMENT_RATIO"]    = _safe_div(plan, cost)
    df["QUANTITY_PER_DAY"]      = _safe_div(qty,  days)
    df["DAYS_SUPPLY"]           = days.astype(float)   # explicit alias
    df["REFILL_FREQUENCY"]      = df["FILL_NUM"].astype(float)

    # ── 6. Beneficiary history features ───────────────────────────────────
    print("\nBeneficiary history:")
    bene_hist = _compute_bene_history(df)

    # ── 7. Prescriber history features ────────────────────────────────────
    print("Prescriber history:")
    prscr_hist = _compute_prescriber_history(df)

    # ── 8. Assemble output ────────────────────────────────────────────────
    print("\nAssembling final feature table …")
    derived_cols = [
        "COST_PER_UNIT", "COST_PER_DAY",
        "PATIENT_PAYMENT_RATIO", "PLAN_PAYMENT_RATIO",
        "QUANTITY_PER_DAY", "DAYS_SUPPLY", "REFILL_FREQUENCY",
    ]

    # Keep identifiers + year/date for validation and downstream use
    keep_meta = [c for c in ID_COLS if c in df.columns] + ["SRVC_DATE", "YEAR"]

    result = pd.concat([
        df[keep_meta].copy(),
        df[PASSTHROUGH_COLS].copy(),
        df[derived_cols].copy(),
        bene_hist,
        prscr_hist,
    ], axis=1)

    # ── 9. Validation checks ──────────────────────────────────────────────
    print("\nValidation:")

    # V1: No NaN in passthrough fields that should always be populated
    mandatory = ["QTY_DSPNSD_NUM", "DAYS_SUPLY_NUM", "TOT_RX_CST_AMT"]
    for col in mandatory:
        n_null = int(result[col].isna().sum())
        status = "✓" if n_null == 0 else "✗"
        print(f"  {status} {col}: {n_null} nulls")

    # V2: First rx for each bene should have NaN cumulative history
    first_rows = result.groupby("BENE_ID").head(1)
    for col in ["BENE_PREV_RX_COUNT", "BENE_PREV_RX_COST"]:
        bad = first_rows[col].notna().sum()
        print(f"  {'✓' if bad==0 else '✗'} First-row {col} all NaN: {bad} violations")

    # V3: Window counts always >= 0
    for col in ["BENE_RX_30D", "BENE_RX_90D"]:
        neg = int((result[col] < 0).sum())
        print(f"  {'✓' if neg==0 else '✗'} {col} >= 0: {neg} negatives")

    # V4: 30D <= 90D window counts
    bad_window = int((result["BENE_RX_30D"] > result["BENE_RX_90D"]).sum())
    print(f"  {'✓' if bad_window==0 else '✗'} BENE_RX_30D <= BENE_RX_90D: {bad_window} violations")

    # V5: No future leak — spot-check BENE_PREV_RX_COUNT equals row position
    df_sorted = result.sort_values(["BENE_ID", "SRVC_DATE"]).copy()
    df_sorted["_pos"] = df_sorted.groupby("BENE_ID").cumcount()
    pos_map = df_sorted["_pos"].to_dict()
    rng = np.random.default_rng(42)
    eligible = result[result["BENE_PREV_RX_COUNT"].notna()].index.tolist()
    sample_idx = rng.choice(eligible, size=min(50, len(eligible)), replace=False)
    t5_fails = sum(
        int(result.loc[i, "BENE_PREV_RX_COUNT"]) != pos_map[i]
        for i in sample_idx
    )
    print(f"  {'✓' if t5_fails==0 else '✗'} Temporal leakage spot-check (50 rows): {t5_fails} failures")

    # ── 10. Save ──────────────────────────────────────────────────────────
    print(f"\nWriting {len(result):,} rows × {len(result.columns)} columns …")
    result.to_csv(OUT_CSV, index=False)
    print(f"✓ Saved → {OUT_CSV.relative_to(ROOT)}")

    # ── 11. Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 64)
    print("  PDE FEATURE PIPELINE SUMMARY")
    print("=" * 64)
    print(f"  Rows              : {len(result):,}")
    print(f"  Columns           : {len(result.columns)}")
    print(f"  Unique BENE_ID    : {result['BENE_ID'].nunique():,}")
    print(f"  Unique PRSCRBR_ID : {result['PRSCRBR_ID'].nunique():,}")
    print()

    # Null rates for key features
    feature_check_cols = (
        PASSTHROUGH_COLS + derived_cols +
        ["BENE_PREV_RX_COUNT", "BENE_PREV_RX_COST",
         "BENE_PREV_AVG_RX_COST", "BENE_PREV_MAX_RX_COST",
         "BENE_RX_30D", "BENE_RX_COST_30D",
         "BENE_RX_90D", "BENE_RX_COST_90D",
         "PRESCRIBER_RX_COUNT", "PRESCRIBER_AVG_RX_COST",
         "PRESCRIBER_MAX_RX_COST", "PRESCRIBER_UNIQUE_BENEFICIARIES"]
    )
    print("  Null rates for feature columns:")
    null_pcts = result[feature_check_cols].isnull().mean().mul(100)
    non_zero = null_pcts[null_pcts > 0]
    if non_zero.empty:
        print("    All features 100% populated")
    else:
        for col, pct in non_zero.sort_values(ascending=False).items():
            print(f"    {col:<40s}: {pct:.1f}%")

    print()
    print("  Key feature statistics:")
    for col in ["TOT_RX_CST_AMT", "COST_PER_DAY", "PATIENT_PAYMENT_RATIO",
                "BENE_PREV_RX_COUNT", "BENE_RX_30D", "PRESCRIBER_RX_COUNT"]:
        s = result[col].dropna()
        print(f"    {col:<40s}: min={s.min():.2f}  median={s.median():.2f}  max={s.max():.2f}")

    print("=" * 64)


if __name__ == "__main__":
    main()
