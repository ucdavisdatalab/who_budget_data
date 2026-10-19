"""
Extracts A63_ID4-en-voluntarytable.pdf (Schedule 2 - Voluntary contributions, by
fund and by donor, for the biennium ended 31 December 2009) into a clean
per-donor CSV.

This document uses a 9-column schema, different order from the 2010-2015 files:
  Voluntary Contributions - Specified | TDR | Stop TB | HRP | Roll Back Malaria |
  WSSCC | Core voluntary contributions account | Other voluntary contributions -
  core | Total

Never previously run through the deterministic pdfplumber pipeline (only the
vision/Claude extraction touched this file, which fragmented multi-line donor
names - e.g. "American Psychiatric\nFoundation" got truncated to just
"Foundation"). Donor names are kept as extracted - entities with similar but
distinct names (e.g. "Bill & Melinda Gates Foundation" vs an unrelated
"Foundation") are NOT merged; multi-line names are reassembled in full instead.
"""

import csv
import re

import pdfplumber

COL_NAMES = [
    "Voluntary Contributions - Specified",
    "Special Programme for Research and Training in Tropical Diseases",
    "Stop TB Partnership",
    "Special Programme of Research Development and Research Training in Human Reproduction",
    "Roll Back Malaria Partnership",
    "Water Supply and Sanitation Collaborative Council",
    "Core voluntary contributions account",
    "Other voluntary contributions - core",
    "Total",
]

# Column boundaries derived from the "Total General Fund - Programme Budget" row (page 19).
BOUNDARIES = [248.0, 302.5, 365.5, 432.0, 497.0, 562.0, 633.0, 697.5, 778]
STOP_LABEL = "TOTAL GENERAL FUND"

# Left edge of the numeric data area. Donor names occupy the left column and a
# name can legitimately CONTAIN a number - e.g. "The Asian Pacific Digestive
# Week 2007 (APDW)" - so a numeric token is only data if it also sits in the
# data area. Without this, that donor's name-year 2007 was consumed as a value
# and concatenated onto the real figure, inventing a $2,007,178,010 amount.
# Measured on this document: data numerics start at x0>=189.8, donor-name
# tokens stay below x1~155 (the wider text further right all appears after the
# TOTAL GENERAL FUND stop line, so it never reaches donor parsing).
DATA_COL_MIN_X = 180.0

# Fixed lines that repeat on every page (title/column-header block) - never part
# of a donor name, and never a name-continuation prefix either.
HEADER_LINES = {
    "special special",
    "programme programme on",
    "of research research,",
    "and development water supply other",
    "voluntary training in and training in roll back and sanitation core voluntary voluntary",
    "contributions – tropical stop tb human malaria collaborative contributions contributions –",
    "donor specified diseases partnership reproduction partnership council account core total",
    "member states",
}
HEADER_PREFIXES = ("world health organization", "schedule 2", "for the biennium")
# Page number and document code sometimes appear combined on one line ("5 A63/INF.DOC./4"),
# sometimes as two separate lines ("5" then "A63/INF.DOC./4" alone) - match both shapes.
PAGE_NUM_RE = re.compile(r"^\d+\s+A63/INF\.DOC\./4$|^\d+$|^A63/INF\.DOC\./4$")


def is_num(t):
    return t.replace(",", "").replace("-", "").replace("–", "").isdigit()


def is_header_or_pagenum(text):
    t = text.strip().lower()
    if t in HEADER_LINES:
        return True
    if any(t.startswith(p) for p in HEADER_PREFIXES):
        return True
    if PAGE_NUM_RE.match(text.strip()):
        return True
    return False


SKIP_KW = ["pass through", "refunds to"]


def should_skip_donor(text):
    tl = text.lower().strip()
    if not tl or len(tl) < 2:
        return True
    if tl.startswith("total"):
        return True
    if any(k in tl for k in SKIP_KW):
        return True
    return False


def assign_col(x1):
    for i, b in enumerate(BOUNDARIES):
        if x1 <= b:
            return i
    return len(BOUNDARIES) - 1


def parse_nums(words):
    max_x1 = BOUNDARIES[-1]
    cols = {}
    for w in words:
        if not is_num(w["text"]) or w["x1"] > max_x1:
            continue
        c = assign_col(w["x1"])
        cols.setdefault(c, []).append(w)
    result = {}
    for c, fs in cols.items():
        fs.sort(key=lambda w: w["x0"])
        s = "".join(f["text"] for f in fs)
        try:
            result[c] = int(s)
        except ValueError:
            pass
    return result


def extract_rows(pdf_path):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            by_top = {}
            for w in words:
                rk = round(w["top"] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            tops = sorted(by_top.keys())
            pending_name_parts = []
            stop = False
            for top in tops:
                if stop:
                    break
                rw = sorted(by_top[top], key=lambda w: w["x0"])
                full_text = " ".join(w["text"] for w in rw)
                if STOP_LABEL in full_text.upper():
                    stop = True
                    break
                if is_header_or_pagenum(full_text):
                    continue

                num_words = [w for w in rw if is_num(w["text"]) and w["x0"] >= DATA_COL_MIN_X]
                if num_words:
                    name_here = " ".join(
                        w["text"] for w in rw if w["x0"] < DATA_COL_MIN_X
                    ).strip()
                    donor = " ".join(pending_name_parts + ([name_here] if name_here else [])).strip()
                    pending_name_parts = []
                    if should_skip_donor(donor):
                        continue
                    cv = parse_nums(num_words)
                    if cv:
                        results.append((donor, cv))
                else:
                    # name-only continuation line - buffer it for the next numbered row
                    if full_text.strip():
                        pending_name_parts.append(full_text.strip())
    return results


def write_csv(pdf_path, out_path):
    rows = extract_rows(pdf_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Contributor"] + COL_NAMES)
        for name, cols in rows:
            w.writerow([name] + [cols.get(i, "") for i in range(len(COL_NAMES))])
    return rows


if __name__ == "__main__":
    rows = write_csv(
        "A63_ID4-en-voluntarytable.pdf",
        "WHO_voluntary_contributions_2008to2009_biennium.csv",
    )
    print(f"{len(rows)} donor rows extracted")
    names = [n for n, _ in rows]
    dupes = {n for n in names if names.count(n) > 1}
    print(f"{len(dupes)} distinct donor names appear more than once: {sorted(dupes)[:20]}")
