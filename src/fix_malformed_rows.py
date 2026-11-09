"""Repair rows in the Georgia Tech CSVs that were broken by thousands separators.

The source system wrote numbers >= 1,000 with an unquoted comma (``1,200``), so
the CSV reader splits each such value into two or more fields. Every row with
too many fields contains one or more of these split numbers.

Repair strategy:
  1. Read the file as raw tokens (no type inference).
  2. For a row with extra fields, enumerate every way of re-joining tokens of the
     form ``d{1,3}`` + ``,ddd`` + ... that yields the correct field count.
  3. Drop impossible candidates, then rank the rest with domain consistency checks.
  4. Rows with no confident repair are returned separately for manual review.

Raw files are never modified.
"""

import csv
import math
import re
from pathlib import Path

import pandas as pd

LEAD_GROUP = re.compile(r"[1-9]\d{0,2}")  # first group of "1,234"
THOUSANDS_GROUP = re.compile(r"\d{3}")  # each following group
LEADING_ZERO = re.compile(r"0\d+")  # "080" is never a value on its own


def candidate_splits(tokens, n_fields, mergeable=lambda field_idx: True):
    """Return every way to regroup ``tokens`` into ``n_fields`` values."""

    def go(i, field):
        if i == len(tokens):
            return [()] if field == n_fields else []
        if field == n_fields:
            return []
        out = [(tokens[i],) + rest for rest in go(i + 1, field + 1)]
        if mergeable(field) and LEAD_GROUP.fullmatch(tokens[i]):
            j = i + 1
            while j < len(tokens) and THOUSANDS_GROUP.fullmatch(tokens[j]):
                j += 1
                merged = "".join(tokens[i:j])
                out += [(merged,) + rest for rest in go(j, field + 1)]
        return out

    return go(0, 0)


def _read_raw(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    # Row 2 is a second, legacy header (e.g. "VTFS_JE,DT_START,TLV,...").
    return rows[0], rows[2:]


def _to_frame(header, records):
    df = pd.DataFrame(records, columns=header)
    return df.apply(lambda s: s.str.strip()).replace("", pd.NA)


# --------------------------------------------------------------------------- picks


def fix_picks(path):
    """Only ACT_QTY / REQ_QTY can be split, and every split turns out unambiguous."""
    header, rows = _read_raw(path)
    n_fixed = len(header) - 2  # columns before ACT_QTY never contain commas
    good, bad = [], []
    for row in rows:
        if len(row) == len(header):
            good.append(row)
            continue
        cands = candidate_splits(row[n_fixed:], 2)
        if len(cands) == 1:
            good.append(row[:n_fixed] + list(cands[0]))
        else:
            bad.append(row)
    return _to_frame(header, good), bad


# ---------------------------------------------------------------------------- SKUs


def _num(value):
    try:
        return float(value)
    except ValueError:
        return None


def _consistency_error(rec):
    """Mean relative error of two checks that should hold for a pallet-level SKU.

    * cases per pallet (QTY2IN3) == CASES_PER_LAYER * LAYERS_PER_PALLET
    * pallet weight (WGT3) ~= cases per pallet * case weight (WGT2)
    """
    q23, cpl, lpp, w2, w3 = (
        _num(rec[c])
        for c in ("QTY2IN3", "CASES_PER_LAYER", "LAYERS_PER_PALLET", "WGT2", "WGT3")
    )
    errors = []
    if q23 and cpl and lpp:
        errors.append(abs(q23 - cpl * lpp) / max(q23, cpl * lpp))
    if q23 and w2 and w3:
        errors.append(abs(w3 - q23 * w2) / max(w3, q23 * w2))
    return sum(errors) / len(errors) if errors else math.inf


def fix_skus(path, margin=0.15):
    header, rows = _read_raw(path)
    n_fixed = 4  # SKU and UOM1-3 are text
    cols = header[n_fixed:]
    good, bad = [], []
    for row in rows:
        if len(row) == len(header):
            good.append(row)
            continue
        cands = [dict(zip(cols, c)) for c in candidate_splits(row[n_fixed:], len(cols))]
        cands = [c for c in cands if not any(LEADING_ZERO.fullmatch(v) for v in c.values())]
        if row[3].strip():  # has a 3rd unit of measure, so QTY2IN3 must be > 0
            cands = [c for c in cands if (_num(c["QTY2IN3"]) or 0) > 0]

        # Rank: consistency first; prefer a split pallet weight (by far the most
        # common value >= 1,000) as the tie-breaker.
        def key(c):
            merged_elsewhere = sum(len(v) > 3 for k, v in c.items() if k != "WGT3")
            return (_consistency_error(c), merged_elsewhere)

        ranked = sorted(cands, key=key)
        confident = len(ranked) == 1 or (
            len(ranked) > 1
            and (key(ranked[1])[0] - key(ranked[0])[0] > margin
                 or key(ranked[1])[1] > key(ranked[0])[1])
        )
        if ranked and confident:
            good.append(row[:n_fixed] + [ranked[0][c] for c in cols])
        else:
            bad.append(row)
    return _to_frame(header, good), bad


if __name__ == "__main__":
    raw = Path(__file__).resolve().parents[1] / "data" / "raw" / "georgia_tech"
    for name, fixer in [("picks.csv", fix_picks), ("SKUs.csv", fix_skus)]:
        df, unresolved = fixer(raw / name)
        print(f"{name}: {len(df):,} rows kept, {len(unresolved)} need manual review")
        for row in unresolved:
            print("   ", ",".join(row))
