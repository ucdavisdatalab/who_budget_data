"""
WHO voluntary contributions extractor for older-format PDFs (2010-2015).

These PDFs use a different column schema than the 2016+ files handled by who_extract.py:
  - 7 columns for 2010, 2011, 2012, 2014
  - 8 columns for 2015 (adds Contingency Fund for Emergencies)
  - Column positions vary by year but are auto-detected from the Total row

Column schemas:
  7-col: Core VC account | Other VC-core | VC-specified | HRP | Stop TB | TDR | Total revenue
  8-col: Core VC account | Other VC-core | VC-specified | CFE | HRP | Stop TB | TDR | Total revenue
"""

import pdfplumber
import csv

COL_NAMES_8 = [
    "Core voluntary contributions account",
    "Other voluntary contributions – core",
    "Voluntary contributions – specified",
    "Contingency Fund for Emergencies",
    "Special Programme of Research, Development and Research Training in Human Reproduction",
    "Stop TB Partnership",
    "Special Programme for Research and Training in Tropical Diseases",
    "Total revenue",
]

COL_NAMES_7 = [
    "Core voluntary contributions account",
    "Other voluntary contributions – core",
    "Voluntary contributions – specified",
    "Special Programme of Research, Development and Research Training in Human Reproduction",
    "Stop TB Partnership",
    "Special Programme for Research and Training in Tropical Diseases",
    "Total revenue",
]

ALWAYS_CONTINUATION = {
    'Northern Ireland', 'NORTHERN IRELAND',
    'Ireland', 'IRELAND',
    'Response Fund', 'RESPONSE FUND',
    'Melinda Gates Foundation)', 'MELINDA GATES FOUNDATION)',
}

def is_num(t):
    return t.replace(',', '').isdigit()

def is_always_continuation(text):
    return text.strip().upper() in {s.upper() for s in ALWAYS_CONTINUATION}

def has_unmatched_open_paren(name_parts):
    """True if the name accumulated so far has an opening '(' with no closing
    ')' yet - e.g. "AFRICAN PROGRAMME FOR ONCHOCERCIASIS CONTROL" followed by
    a trailing "(APOC)" line. Unlike nearby-numbers heuristics, this has no
    false-positive risk against a genuinely new entity's name, so it's safe
    to always act on."""
    joined = ' '.join(name_parts)
    return joined.count('(') > joined.count(')')

def detect_col_boundaries(pdf_path):
    """
    Auto-detect column boundaries by finding the row with the most number groups (7 or 8).
    Uses Total General Fund row in preference to Total Member States (more columns filled).
    Returns (boundaries_list, num_cols).
    """
    best_groups = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            by_top = {}
            for w in words:
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            for top in sorted(by_top.keys()):
                rw = by_top[top]
                names = ' '.join(w['text'] for w in rw if w['x0'] < 220)
                if 'Total' not in names:
                    continue
                if not ('Member' in names or 'General' in names):
                    continue
                nums = sorted(
                    [w for w in rw if w['x0'] >= 220 and is_num(w['text'])],
                    key=lambda w: w['x0']
                )
                if len(nums) < 6:
                    continue
                groups = []
                cur = [nums[0]]
                for i in range(1, len(nums)):
                    if nums[i]['x0'] - cur[-1]['x1'] <= 6:
                        cur.append(nums[i])
                    else:
                        groups.append(cur)
                        cur = [nums[i]]
                groups.append(cur)
                if len(groups) in (7, 8):
                    if best_groups is None or len(groups) > len(best_groups):
                        best_groups = groups
    if best_groups is None:
        return None, None
    bs = []
    for i in range(len(best_groups) - 1):
        mid = (max(f['x1'] for f in best_groups[i]) + min(f['x0'] for f in best_groups[i+1])) / 2
        bs.append(mid)
    bs.append(max(f['x1'] for f in best_groups[-1]) + 20)
    return bs, len(best_groups)

def assign_col(x1, bs):
    for i, b in enumerate(bs):
        if x1 <= b:
            return i
    return len(bs) - 1

def parse_nums(words, bs):
    max_x1 = bs[-1]
    cols = {}
    for w in words:
        if not is_num(w['text']):
            continue
        if w['x1'] > max_x1:
            continue
        c = assign_col(w['x1'], bs)
        cols.setdefault(c, []).append(w)
    result = {}
    for c, fs in cols.items():
        fs.sort(key=lambda w: w['x0'])
        s = ''.join(f['text'] for f in fs)
        try:
            result[c] = int(s)
        except:
            pass
    return result

def parse_nums_neg(words, bs):
    max_x1 = bs[-1]
    words = [w for w in words if not (is_num(w['text']) and w['x1'] > max_x1)]
    result = {}
    ws = sorted(words, key=lambda w: w['x0'])
    i = 0
    while i < len(ws):
        w = ws[i]
        t = w['text']
        if t.startswith('(') and not t.endswith(')'):
            neg = t.lstrip('(')
            rx = w['x1']
            i += 1
            while i < len(ws):
                n = ws[i]
                if n['text'].endswith(')'):
                    neg += n['text'].rstrip(')')
                    rx = n['x1']
                    i += 1
                    break
                elif is_num(n['text']):
                    neg += n['text']
                    rx = n['x1']
                    i += 1
                else:
                    i += 1
                    break
            if is_num(neg):
                result[assign_col(rx, bs)] = -int(neg)
        elif t.startswith('(') and t.endswith(')'):
            inner = t[1:-1]
            if is_num(inner):
                result[assign_col(w['x1'], bs)] = -int(inner)
            i += 1
        elif is_num(t):
            c = assign_col(w['x1'], bs)
            result[c] = result.get(c, '')
            if isinstance(result[c], str):
                result[c] += t
            i += 1
        else:
            i += 1
    final = {}
    for k, v in result.items():
        if isinstance(v, str):
            try:
                final[k] = int(v)
            except:
                pass
        else:
            final[k] = v
    return final

SKIP_KW = ['schedule', 'world health', 'note ', 'revenue ',
           'general fund', 'a. general', 'contributor', 'pass through',
           'refunds to', 'other and', 'grand total', 'interfund',
           'alliance for health policy', 'donor']

def should_skip(text):
    tl = text.lower()
    # 'for the' (as in 'For the year ended...') is a header-only phrase but also a
    # substring of real donor names like "Light For The World" - only skip when it
    # actually STARTS the text, not when it merely appears somewhere in it.
    return (any(k in tl for k in SKIP_KW) or tl.strip().startswith('for the') or
            tl.strip().startswith('total') or
            text.replace(' ', '').isdigit() or len(text.strip()) < 2)

def row_has_nearby_nums(tops, by_top, start_idx, window=2):
    for k in range(start_idx, min(start_idx + window, len(tops))):
        if any(is_num(w['text']) and w['x0'] >= 200 for w in by_top[tops[k]]):
            return True
    return False

def try_append_trailing(tops, by_top, j, name_parts, skip):
    if j >= len(tops):
        return
    kt = tops[j]
    kr = sorted(by_top[kt], key=lambda w: w['x0'])
    knames = [w['text'] for w in kr if w['x0'] < 200]
    knums = [w for w in kr if w['x0'] >= 200 and is_num(w['text'])]
    if knames and not knums:
        ks = ' '.join(knames).strip()
        if not should_skip(ks):
            if is_always_continuation(ks) or has_unmatched_open_paren(name_parts):
                name_parts.append(ks)
                skip.add(kt)
            elif not row_has_nearby_nums(tops, by_top, j + 1, 2):
                name_parts.append(ks)
                skip.add(kt)

def extract_rows(pdf_path, bs, min_top=110):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            by_top = {}
            for w in words:
                if w['top'] < min_top:
                    continue
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            tops = sorted(by_top.keys())
            skip = set()
            i = 0
            while i < len(tops):
                top = tops[i]
                if top in skip:
                    i += 1
                    continue
                rw = sorted(by_top[top], key=lambda w: w['x0'])
                # Dynamically find name boundary: all text words before first numeric word
                num_words = [w for w in rw if is_num(w['text'])]
                if num_words:
                    first_num_x = min(w['x0'] for w in num_words)
                    names = [w['text'] for w in rw if not is_num(w['text']) and w['x0'] < first_num_x + 5]
                    nums = [w for w in num_words if True]  # all nums
                else:
                    names = [w['text'] for w in rw if w['x0'] < 200]
                    nums = []
                if not names:
                    i += 1
                    continue
                contributor = ' '.join(names).strip()
                if should_skip(contributor):
                    i += 1
                    continue

                if nums:
                    # Check if next row is a text-only continuation (e.g. "IRELAND" after UK)
                    name_parts = [contributor]
                    if i + 1 < len(tops):
                        nxt = tops[i + 1]
                        nrw = sorted(by_top[nxt], key=lambda w: w['x0'])
                        nnums = [w for w in nrw if is_num(w['text'])]
                        nnames = [w['text'] for w in nrw if not is_num(w['text'])]
                        if nnames and not nnums:
                            ns = ' '.join(nnames).strip()
                            if is_always_continuation(ns):
                                name_parts.append(ns)
                                skip.add(nxt)
                    # An unmatched opening paren (e.g. "AFRICAN PROGRAMME FOR
                    # ONCHOCERCIASIS CONTROL" wrapping its "(APOC)" acronym to
                    # its own line) unambiguously needs a trailing line to
                    # close it, regardless of what follows - unlike generic
                    # nearby-numbers heuristics, this has no false-positive
                    # risk against a genuinely new entity's name.
                    if has_unmatched_open_paren(name_parts):
                        try_append_trailing(tops, by_top, i + 1, name_parts, skip)
                    cv = parse_nums(nums, bs)
                    if cv:
                        full_name = ' '.join(name_parts)
                        full_name = full_name.replace('OFGREAT', 'OF GREAT').replace('ofgreat', 'of great')
                        results.append((full_name, cv))
                    i += 1
                    continue

                # No numbers on this row - look ahead
                name_parts = [contributor]
                found_nums = []
                j = i + 1

                if j < len(tops):
                    jt = tops[j]
                    jr = sorted(by_top[jt], key=lambda w: w['x0'])
                    jnum_words = [w for w in jr if is_num(w['text'])]
                    if jnum_words:
                        j_first_num_x = min(w['x0'] for w in jnum_words)
                        jnames = [w['text'] for w in jr if not is_num(w['text']) and w['x0'] < j_first_num_x + 5]
                        jnums = jnum_words
                    else:
                        jnames = [w['text'] for w in jr if w['x0'] < 200]
                        jnums = []

                    # A lone stray token (e.g. a page number sitting in the table's
                    # column area) can look like "no name, has numbers" without being
                    # real column data - only take this path if it actually parses
                    # into a real column value; otherwise treat it as noise and keep
                    # looking ahead in the while-loop below instead of silently
                    # dropping the current name-only row.
                    if not jnames and jnums and parse_nums(jnums, bs):
                        found_nums = jnums
                        skip.add(jt)
                        j += 1
                        try_append_trailing(tops, by_top, j, name_parts, skip)
                    else:
                        while j < len(tops) and j < i + 6:
                            jt = tops[j]
                            jr = sorted(by_top[jt], key=lambda w: w['x0'])
                            jnum_words2 = [w for w in jr if is_num(w['text'])]
                            if jnum_words2:
                                j2_first_num_x = min(w['x0'] for w in jnum_words2)
                                jnames = [w['text'] for w in jr if not is_num(w['text']) and w['x0'] < j2_first_num_x + 5]
                                jnums = jnum_words2
                            else:
                                jnames = [w['text'] for w in jr if w['x0'] < 200]
                                jnums = []
                            if jnames:
                                js = ' '.join(jnames).strip()
                                if should_skip(js):
                                    break
                                if not found_nums:
                                    name_parts.append(js)
                                    skip.add(jt)
                                    if jnums:
                                        found_nums = jnums
                                        j += 1
                                        break
                                    j += 1
                                else:
                                    break
                            elif jnums and parse_nums(jnums, bs):
                                found_nums = jnums
                                skip.add(jt)
                                j += 1
                                break
                            else:
                                # jnums present but doesn't parse into a real column
                                # (e.g. a stray page number) - treat as noise, keep
                                # looking ahead rather than consuming it as data.
                                j += 1
                        if found_nums:
                            try_append_trailing(tops, by_top, j, name_parts, skip)

                if found_nums:
                    cv = parse_nums(found_nums, bs)
                    if cv:
                        full_name = ' '.join(name_parts)
                        full_name = full_name.replace('OFGREAT', 'OF GREAT').replace('ofgreat', 'of great')
                        results.append((full_name, cv))
                i += 1
    return results

def extract_special(pdf_path, bs, min_top=110):
    special = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            by_top = {}
            for w in words:
                if w['top'] < min_top:
                    continue
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            tops = sorted(by_top.keys())
            for idx, top in enumerate(tops):
                rw = sorted(by_top[top], key=lambda w: w['x0'])
                lt = ' '.join(w['text'] for w in rw if w['x0'] < 200)
                at = ' '.join(w['text'] for w in rw)
                label = None
                if 'Total' in lt and 'Member' in at and 'States' in at:
                    label = 'Total – Member States'
                elif lt.strip().startswith('Total') and 'General' in at and 'Fund' in at:
                    label = 'Total General Fund'
                elif 'Other' in lt and ('miscellaneous' in at.lower() or 'miscell' in at.lower()):
                    label = 'Other and miscellaneous receipts'
                elif 'Pass' in lt and 'through' in at.lower():
                    label = 'Pass through funding'
                elif 'Refunds' in lt and ('donors' in at.lower() or 'donor' in at.lower()):
                    label = 'Refunds to donors'
                if not label or label in special:
                    continue
                nw = [w for w in rw if w['x0'] >= 200]
                if idx + 1 < len(tops):
                    nt = tops[idx + 1]
                    nr = by_top[nt]
                    nl = ' '.join(w['text'] for w in nr if w['x0'] < 200).strip()
                    if nl == '' or nl.lower().startswith('(note') or nl.lower().startswith('note'):
                        nw.extend([w for w in nr if w['x0'] >= 200])
                cv = parse_nums_neg(nw, bs)
                if cv:
                    special[label] = cv
    return special

def write_csv(pdf_path, out_path, num_cols):
    bs, detected_cols = detect_col_boundaries(pdf_path)
    if bs is None:
        raise ValueError(f"Could not detect column boundaries in {pdf_path}")
    col_names = COL_NAMES_8 if detected_cols == 8 else COL_NAMES_7
    rows = extract_rows(pdf_path, bs)
    special = extract_special(pdf_path, bs)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Contributor'] + col_names)
        for name, cols in rows:
            w.writerow([name] + [cols.get(i, '') for i in range(detected_cols)])
        for label in ['Total – Member States', 'Other and miscellaneous receipts',
                      'Pass through funding', 'Refunds to donors', 'Total General Fund']:
            if label in special:
                w.writerow([label] + [special[label].get(i, '') for i in range(detected_cols)])
    return rows, special, detected_cols

if __name__ == '__main__':
    import sys

    runs = [
        (2015, "/mnt/user-data/uploads/A69_INF3-en-voluntarytable.pdf",  "/home/claude/WHO_2015_final.csv"),
        (2014, "/mnt/user-data/uploads/A68_INF1-en-voluntarytable.pdf",  "/home/claude/WHO_2014_final.csv"),
        (2012, "/mnt/user-data/uploads/A66_29Add1-en-voluntarytable.pdf","/home/claude/WHO_2012_final.csv"),
        (2011, "/mnt/user-data/uploads/A65_29Add1-en-voluntarytable.pdf","/home/claude/WHO_2011_biennium_final.csv"),
        (2010, "/mnt/user-data/uploads/A64_29Add1Corr1-en-voluntarytable.pdf", "/home/claude/WHO_2010_final.csv"),
    ]

    for year, pdf, out in runs:
        print(f"\n{'='*60}\nExtracting {year}...")
        rows, special, ncols = write_csv(pdf, out, None)
        print(f"  {ncols} columns detected")
        print(f"  {len(rows)} contributor rows")
        for k in ['Total – Member States', 'Total General Fund']:
            if k in special:
                total_col = ncols - 1
                tv = special[k].get(total_col, '?')
                print(f"  {k}: Total col = {tv:,}" if isinstance(tv, int) else f"  {k}: Total col = {tv}")
