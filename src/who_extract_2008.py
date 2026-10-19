"""
WHO voluntary contributions extractor for 2008 (A62/INF.DOC./4).

This report has a structure unlike any later year: one main alphabetical
table (Member States + other contributors, 2 value columns: "Voluntary
contributions - specified" and "- core"), followed by 9 separate
fund-specific sections (Stop TB Partnership Global Drug Facility, TDR,
Water Supply and Sanitation Collaborative Council, HRP, Stop TB Partnership,
WHO Framework Convention on Tobacco Control, Roll Back Malaria Partnership,
Other Partnerships, Revolving Fund for Teaching and Laboratory Equipment),
each with its own single value column and its own contributor list (the
same contributor can and does appear in multiple sections). Each section
ends with its own "TOTAL <n>" line, used here to validate extraction
against WHO's own reported subtotal rather than assumed correct.

Kept as its own bespoke script (like who_extract_2009_biennium.py and
who_extract_2009_assessed.py) rather than folded into a generic multi-year
extractor, since this section-based single-value-column layout is unique
to this one report.
"""

import re

import pdfplumber

MAIN_COL_NAMES = ["Voluntary contributions - specified", "Voluntary contributions - core"]

# (header substring(s) to match, category column name, expected WHO-reported
# section total). Headers are matched against the concatenation of up to 2
# consecutive row-lines, since some wrap onto a second line in the PDF.
SECTIONS = [
    ("STOP TB PARTNERSHIP GLOBAL DRUG FACILITY", "Stop TB Partnership Global Drug Facility", 48043967),
    ("UNICEF/UNDP/WORLD BANK/WHO SPECIAL PROGRAMME OF RESEARCH AND TRAINING IN TROPICAL DISEASES",
     "Special Programme for Research and Training in Tropical Diseases", 37585340),
    ("WATER SUPPLY AND SANITATION COLLABORATIVE COUNCIL", "Water Supply and Sanitation Collaborative Council", 19747550),
    ("UNDP/UNFPA/WHO/WORLD BANK SPECIAL PROGRAMME ON RESEARCH, DEVELOPMENT AND RESEARCH TRAINING IN HUMAN REPRODUCTION",
     "Special Programme of Research, Development and Research Training in Human Reproduction", 12898493),
    ("STOP TB PARTNERSHIP", "Stop TB Partnership", 9836749),
    ("WHO FRAMEWORK CONVENTION ON TOBACCO CONTROL", "WHO Framework Convention on Tobacco Control", 4869544),
    ("ROLL BACK MALARIA PARTNERSHIP", "Roll Back Malaria Partnership", 3156885),
    ("OTHER PARTNERSHIPS", "Other Partnerships (2008)", 2203742),
    ("REVOLVING FUND FOR TEACHING AND LABORATORY EQUIPMENT", "Revolving Fund for Teaching and Laboratory Equipment", 51561),
]
MAIN_EXPECTED_TOTAL = 972931392
GRAND_TOTAL_EXPECTED = 1111325223

PAGE_HEADER_KW = ['a62/inf.doc./4', 'world health organization',
                  'summary of voluntary contributions', 'for the year ended',
                  'voluntary voluntary total', 'contributions', 'specified core',
                  'member states', 'other includes prior period adjustments']

ALWAYS_CONTINUATION = {
    'AND NORTHERN IRELAND',
}

def is_num(t):
    return t.replace(',', '').isdigit()

def is_num_token(t):
    """Plain digit token, or a parenthesized-negative fragment like '(7' or
    '160)' - WHO's 'OTHER' adjustment row reports negative figures in
    accounting-style parentheses, e.g. 'OTHER1 (7 235 160) 52 044 (7 183 116)'."""
    stripped = t.strip('(),')
    return stripped.isdigit() and stripped != ''

def is_always_continuation(text):
    return text.strip().upper() in ALWAYS_CONTINUATION

def has_unmatched_open_paren(name_parts):
    joined = ' '.join(name_parts)
    return joined.count('(') > joined.count(')')

def is_page_header(text):
    tl = text.strip().lower()
    if tl.isdigit():
        return True
    if tl == 'total':
        # The single-value-column sections repeat "Total" as their bare
        # column-header on every continuation page (distinct from an actual
        # "TOTAL <n>" section-ending line, which is_total_line handles).
        return True
    return any(kw in tl for kw in PAGE_HEADER_KW)

def is_total_line(text):
    # Bare "Total" (no number) is just the repeated column-header line on
    # each continuation page, not an actual section-ending total.
    return bool(re.match(r'^(GRAND\s+)?TOTAL\s+[\d,]', text.strip(), re.IGNORECASE))

def parse_total_line_value(rw):
    """The rightmost number group on a 'TOTAL ...' row is that section's
    grand total (for the 2-column main table, the 3rd/last group)."""
    _, nums = row_name_and_nums(rw)
    if not nums:
        return None
    ws = sorted(nums, key=lambda w: w['x0'])
    groups = []
    cur = [ws[0]]
    for w in ws[1:]:
        if w['x0'] - cur[-1]['x1'] <= 6:
            cur.append(w)
        else:
            groups.append(cur)
            cur = [w]
    groups.append(cur)
    s = ''.join(w['text'] for w in groups[-1])
    try:
        return int(s)
    except ValueError:
        return None

def build_rows(pdf_path):
    """Flatten the whole document into (page, top, row_words) tuples, in
    reading order, with page-header/footer noise dropped."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages):
            words = page.extract_words()
            by_top = {}
            for w in words:
                if w['top'] < 55:
                    continue
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            # A footnote-marker digit (e.g. "OTHER" + superscript "1") can
            # shift a word's bounding-box top just enough to land in the next
            # 3pt bucket, splitting one visual table line into two. Normal
            # line spacing in this document is ~11-13pt, so merge adjacent
            # buckets whose actual word tops are much closer than that -
            # unambiguously a split row, not two real lines.
            tops_sorted = sorted(by_top.keys())
            merged_tops = []
            for t in tops_sorted:
                if merged_tops and (min(w['top'] for w in by_top[t]) -
                                     max(w['top'] for w in by_top[merged_tops[-1]]) < 3):
                    by_top[merged_tops[-1]].extend(by_top[t])
                    del by_top[t]
                else:
                    merged_tops.append(t)

            for top in sorted(by_top.keys()):
                rw = sorted(by_top[top], key=lambda w: w['x0'])
                txt = ' '.join(w['text'] for w in rw)
                if is_page_header(txt) or txt.strip() in ('= = =',):
                    continue
                rows.append((pno, top, rw, txt))
    return rows

def row_name_and_nums(rw):
    """Split a row's words into (name_words, number_words) using a dynamic
    boundary at the first numeric token - mirrors who_extract_2010to2015.py,
    which handles long wrapped names better than a fixed x0 cutoff."""
    num_words = [w for w in rw if is_num_token(w['text'])]
    if num_words:
        first_num_x = min(w['x0'] for w in num_words)
        names = [w['text'] for w in rw if not is_num_token(w['text']) and w['x0'] < first_num_x + 5]
        nums = num_words
    else:
        names = [w['text'] for w in rw]
        nums = []
    return names, nums

def extract_section(rows, start_idx, n_value_cols, expected_total):
    """Extract (contributor -> [value_col0, value_col1, ...]) rows starting
    at start_idx until a TOTAL line, handling multi-line names the same way
    as the other extractors: look ahead for a continuation when a row has no
    numbers, and rescue an unmatched trailing '(' close."""
    results = []
    i = start_idx
    skip = set()
    while i < len(rows):
        pno, top, rw, txt = rows[i]
        if (pno, top) in skip:
            i += 1
            continue
        if is_total_line(txt):
            reported = parse_total_line_value(rw)
            computed = sum(sum(v for v in vals if v is not None) for _, vals in results)
            if expected_total is not None and reported != expected_total:
                print(f"  WARNING: PDF's own TOTAL line ({reported}) doesn't match expected ({expected_total})")
            if reported is not None and computed != reported:
                print(f"  WARNING: extracted sum ({computed}) != PDF's own TOTAL line ({reported}), diff={computed - reported}")
            return results, i + 1
        names, nums = row_name_and_nums(rw)
        if not names:
            i += 1
            continue
        contributor = ' '.join(names).strip()
        if not contributor or is_total_line(contributor):
            i += 1
            continue

        if nums:
            if contributor == 'OTHER1':
                # Footnote marker "1" (Other includes prior period adjustments
                # and corrections.) attached directly to the word with no
                # space, so it tokenized as one word.
                contributor = 'OTHER'
            name_parts = [contributor]
            values = assign_values(nums, n_value_cols)
            j = i + 1
            if has_unmatched_open_paren(name_parts) and j < len(rows):
                jnames, jnums = row_name_and_nums(rows[j][2])
                if jnames and not jnums and not is_total_line(rows[j][3]):
                    js = ' '.join(jnames).strip()
                    if not is_page_header(js):
                        name_parts.append(js)
                        skip.add((rows[j][0], rows[j][1]))
            results.append((' '.join(name_parts), values))
            i += 1
            continue

        # No numbers on this row: look ahead for the continuation/value line.
        name_parts = [contributor]
        j = i + 1
        found_values = None
        while j < len(rows) and j < i + 6:
            jpno, jtop, jrw, jtxt = rows[j]
            if is_total_line(jtxt):
                break
            jnames, jnums = row_name_and_nums(jrw)
            if jnames:
                js = ' '.join(jnames).strip()
                if is_page_header(js):
                    j += 1
                    continue
                if found_values is None:
                    name_parts.append(js)
                    skip.add((jpno, jtop))
                    if jnums:
                        found_values = assign_values(jnums, n_value_cols)
                        j += 1
                        break
                    j += 1
                else:
                    break
            elif jnums:
                found_values = assign_values(jnums, n_value_cols)
                skip.add((jpno, jtop))
                j += 1
                break
            else:
                j += 1
        if found_values is not None:
            # One more trailing name-only line can follow (closing paren, etc.)
            if j < len(rows):
                jnames, jnums = row_name_and_nums(rows[j][2])
                if jnames and not jnums and not is_total_line(rows[j][3]):
                    js = ' '.join(jnames).strip()
                    if not is_page_header(js) and (is_always_continuation(js) or has_unmatched_open_paren(name_parts)):
                        name_parts.append(js)
                        skip.add((rows[j][0], rows[j][1]))
            results.append((' '.join(name_parts), found_values))
        i += 1
    return results, i

def cluster_num_groups(num_words):
    """Cluster numeric word-tokens into contiguous groups by x-gap, so e.g.
    '4 005 000' (3 adjacent tokens) forms one group, distinct from an
    unrelated number appearing earlier in the same line of flowing text
    (e.g. the "146" in "(total for 146 Parties)")."""
    ws = sorted(num_words, key=lambda w: w['x0'])
    groups = []
    cur = [ws[0]]
    for w in ws[1:]:
        if w['x0'] - cur[-1]['x1'] <= 6:
            cur.append(w)
        else:
            groups.append(cur)
            cur = [w]
    groups.append(cur)
    return groups

def assign_values(num_words, n_cols):
    """Single-column sections: the value is the LAST (rightmost) numeric
    group - guards against a number embedded earlier in flowing name text
    (e.g. "146" in "(total for 146 Parties)") being mistaken for the value.
    Two-column (main table) sections: use x-position to split into
    [specified, core], ignoring the redundant trailing 'Total' group."""
    groups = cluster_num_groups(num_words)

    def group_val(g):
        is_negative = any('(' in w['text'] for w in g)
        s = ''.join(w['text'].strip('(),') for w in g)
        try:
            v = int(s)
            return -v if is_negative else v
        except ValueError:
            return None

    if n_cols == 1:
        return [group_val(groups[-1])]

    vals = [group_val(g) for g in groups]
    if len(vals) >= 3:
        return [vals[0], vals[1]]
    if len(vals) == 2:
        # Only one of specified/core populated; the 2nd number is the
        # (redundant) Total repeating it. Position tells us which column
        # the lone value belongs to - column boundary from AUSTRALIA-style
        # 3-group rows is roughly x0 ~350; specified sits left of it.
        return [vals[0], None] if groups[0][0]['x0'] < 350 else [None, vals[0]]
    return [vals[0]] if vals else [None]

def find_section_start(rows, marker, from_idx):
    marker_upper = marker.upper()
    for i in range(from_idx, len(rows)):
        txt = rows[i][3].strip().upper()
        combined = txt
        if i + 1 < len(rows):
            combined = (txt + ' ' + rows[i + 1][3].strip().upper()).strip()
        if marker_upper in txt or marker_upper in combined:
            # Advance past this header line (and its continuation line, if any)
            j = i + 1
            if marker_upper not in txt and j < len(rows):
                j += 1
            return j
    raise ValueError(f"Section header not found: {marker}")

def write_csv(pdf_path, out_path):
    rows = build_rows(pdf_path)

    main_start = 0
    print("Main table (specified / core):")
    main_rows, after_idx = extract_section(rows, main_start, 2, MAIN_EXPECTED_TOTAL)
    print(f"  {len(main_rows)} contributor rows")

    section_results = []
    idx = after_idx
    for marker, category, expected_total in SECTIONS:
        start = find_section_start(rows, marker, idx)
        print(f"{category}:")
        srows, idx = extract_section(rows, start, 1, expected_total)
        if category == "WHO Framework Convention on Tobacco Control":
            # This section's first entry is a 4-line label with an embedded
            # year ("... for 2008 (total for 146 Parties) 4 005 000") that
            # the generic name/number split can't tell apart from a genuine
            # value - fold the two fragments it produces back into one row.
            srows = [
                (name, vals) for name, vals in srows
                if name not in ('FOR WHO FRAMEWORK CONVENTION ON TOBACCO CONTROL FOR', 'FOR')
            ]
            srows.insert(0, (
                # Deliberately avoids the word "total" - build_long_format.py's
                # is_footer_row() treats any contributor name containing
                # "total" as a footer/summary row to be dropped, which this
                # legitimate entry would otherwise be mistaken for.
                'Voluntary assessed contributions for WHO Framework Convention on '
                'Tobacco Control for 2008 (146 Parties)', [4005000],
            ))
        print(f"  {len(srows)} contributor rows")
        section_results.append((category, srows))

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        import csv
        w = csv.writer(f)
        header = ['Contributor'] + MAIN_COL_NAMES + [c for c, _ in section_results]
        w.writerow(header)

        all_contributors = {}
        for name, vals in main_rows:
            d = all_contributors.setdefault(name, {})
            d[MAIN_COL_NAMES[0]] = vals[0]
            d[MAIN_COL_NAMES[1]] = vals[1]
        for category, srows in section_results:
            for name, vals in srows:
                d = all_contributors.setdefault(name, {})
                d[category] = (d.get(category) or 0) + (vals[0] or 0)

        for name in all_contributors:
            row = [name] + [all_contributors[name].get(c, '') for c in MAIN_COL_NAMES + [c for c, _ in section_results]]
            w.writerow(row)

    print(f"\nWrote {out_path}: {len(all_contributors)} distinct contributors")
    return all_contributors

if __name__ == '__main__':
    write_csv('A62_ID4-en-voluntarytable.pdf', 'WHO_voluntary_contributions_2008.csv')
