import pdfplumber
import csv

COL_NAMES = [
    "Core Voluntary Contributions Account",
    "Voluntary Contributions – Core",
    "Voluntary Contributions – Specified",
    "Special Programmes and Collaborative Arrangements",
    "Outbreak and Crisis Response",
    "Contingency Fund for Emergencies",
    "Special Programme of Research Development and Research Training in Human Reproduction",
    "Special Programme for Research and Training in Tropical Diseases",
    "Grand Total"
]

# Phrases that are always continuations of the previous name line, regardless of what follows
ALWAYS_CONTINUATION = {
    'Northern Ireland', 'Response Fund', 'Melinda Gates Foundation)',
}

def is_always_continuation(text):
    t = text.strip()
    return t in ALWAYS_CONTINUATION

def detect_col_boundaries(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            for w in words:
                if 'Total' in w['text'] and w['x0'] < 185:
                    tt = w['top']
                    total_nums = sorted(
                        [ww for ww in words if abs(ww['top']-tt) < 4 and ww['x0'] >= 185
                         and ww['text'].replace(',','').isdigit()],
                        key=lambda w: w['x0']
                    )
                    if len(total_nums) >= 20:
                        groups = []; cur = [total_nums[0]]
                        for i in range(1, len(total_nums)):
                            if total_nums[i]['x0'] - cur[-1]['x1'] <= 5:
                                cur.append(total_nums[i])
                            else:
                                groups.append(cur); cur = [total_nums[i]]
                        groups.append(cur)
                        if len(groups) == 9:
                            bs = []
                            for i in range(len(groups)-1):
                                bs.append((max(w['x1'] for w in groups[i]) +
                                           min(w['x0'] for w in groups[i+1])) / 2)
                            bs.append(max(w['x1'] for w in groups[-1]) + 20)
                            return bs
    return None

def assign_col(x1, bs):
    for i, b in enumerate(bs):
        if x1 <= b: return i
    return len(bs) - 1

def is_num(t): return t.replace(',','').isdigit()

def is_num_token(t):
    """Plain digit token, or a parenthesized-negative fragment like '(48' or
    '000)' - WHO sometimes reports a negative reversal/correction inline in
    a regular contributor row (e.g. 'Saudi Arabia 48 000 000 3 095 491
    (48 000 000) 3 095 491'), not just in the special summary rows."""
    stripped = t.strip('(),')
    return stripped.isdigit() and stripped != ''

def parse_nums(words, bs):
    cols = {}
    max_x1 = bs[-1]
    for w in words:
        if not is_num(w['text']): continue
        if w['x1'] > max_x1: continue  # skip stray numbers beyond table (e.g. page sidebars)
        c = assign_col(w['x1'], bs)
        cols.setdefault(c, []).append(w)
    result = {}
    for c, fs in cols.items():
        fs.sort(key=lambda w: w['x0'])
        s = ''.join(f['text'] for f in fs)
        try: result[c] = int(s)
        except: pass
    return result

def parse_nums_neg(words, bs):
    max_x1 = bs[-1]
    words = [w for w in words if not (is_num(w['text']) and w['x1'] > max_x1)]
    result = {}; ws = sorted(words, key=lambda w: w['x0']); i = 0
    while i < len(ws):
        w = ws[i]; t = w['text']
        if t.startswith('(') and not t.endswith(')'):
            neg = t.lstrip('('); rx = w['x1']; i += 1
            while i < len(ws):
                n = ws[i]
                if n['text'].endswith(')'):
                    neg += n['text'].rstrip(')'); rx = n['x1']; i += 1; break
                elif is_num(n['text']): neg += n['text']; rx = n['x1']; i += 1
                else: i += 1; break
            if is_num(neg): result[assign_col(rx, bs)] = -int(neg)
        elif t.startswith('(') and t.endswith(')'):
            inner = t[1:-1]
            if is_num(inner): result[assign_col(w['x1'], bs)] = -int(inner)
            i += 1
        elif is_num(t):
            c = assign_col(w['x1'], bs)
            result[c] = result.get(c, '')
            if isinstance(result[c], str): result[c] += t
            i += 1
        else: i += 1
    final = {}
    for k, v in result.items():
        if isinstance(v, str):
            try: final[k] = int(v)
            except: pass
        else: final[k] = v
    return final

SKIP_KW = ['schedule', 'world health', 'note ', 'revenue ',
           'general fund', 'a. general', 'contributor', 'pass through',
           'refunds to', 'other and', 'grand total', 'interfund']
# 'alliance for health policy' used to be in SKIP_KW, presumably mistaken for
# a section label - it's actually a real, recurring donor ("Alliance for
# Health Policy and Systems Research (AHPSR)", confirmed present in 2016,
# 2018, 2020, 2021, 2024) that was being silently dropped every year.

def should_skip(text):
    tl = text.lower()
    # 'for the' (as in 'For the year ended...') is a header-only phrase but also a
    # substring of real donor names like "Light For The World" - only skip when it
    # actually STARTS the text, not when it merely appears somewhere in it.
    return (any(k in tl for k in SKIP_KW) or tl.strip().startswith('for the') or
            tl.strip().startswith('total') or
            text.replace(' ','').isdigit() or len(text.strip()) < 2)

def row_has_nearby_nums(tops, by_top, start_idx, window=2):
    for k in range(start_idx, min(start_idx + window, len(tops))):
        if any(is_num_token(w['text']) and w['x0'] >= 185 for w in by_top[tops[k]]):
            return True
    return False

def has_unmatched_open_paren(name_parts):
    """True if the name accumulated so far has an opening '(' with no closing
    ')' yet - e.g. "Health Equity Matters (previously Australian Federation
    of AIDS". This is an unambiguous signal that a trailing name-only row is
    a required continuation (the closing parenthetical), not the start of a
    new entity - unlike nearby-numbers heuristics, it has no false-positive
    risk against a genuinely new entity's name, so it's safe to use even
    when generic continuation-detection would be too aggressive."""
    joined = ' '.join(name_parts)
    return joined.count('(') > joined.count(')')

def try_append_trailing(tops, by_top, j, name_parts, skip):
    """Try to append a trailing name-only row as a continuation."""
    if j >= len(tops): return
    kt = tops[j]
    kr = sorted(by_top[kt], key=lambda w: w['x0'])
    knames = [w['text'] for w in kr if w['x0'] < 185]
    knums = [w for w in kr if w['x0'] >= 185 and is_num_token(w['text'])]
    if knames and not knums:
        ks = ' '.join(knames).strip()
        if not should_skip(ks):
            # Always append known geographic/structural continuations, and
            # always close out an unmatched opening parenthesis - both are
            # unambiguous regardless of what follows.
            if is_always_continuation(ks) or has_unmatched_open_paren(name_parts):
                name_parts.append(ks); skip.add(kt)
            # Otherwise only append if NOT followed by its own numbers
            elif not row_has_nearby_nums(tops, by_top, j + 1, 2):
                name_parts.append(ks); skip.add(kt)

def is_watermark_noise(w):
    """A rotated annex/document-code stamp bleeds single characters into the
    table's name column (x0 < 185) on some pages - real contributor names
    never consist of a lone 1-character word there, so any such token is
    stamp noise, not content."""
    return len(w['text'].strip()) == 1 and w['x0'] < 185

def extract_rows(pdf_path, bs, min_top=155):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = [w for w in page.extract_words() if not is_watermark_noise(w)]
            by_top = {}
            for w in words:
                if w['top'] < min_top: continue
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            tops = sorted(by_top.keys()); skip = set(); i = 0
            while i < len(tops):
                top = tops[i]
                if top in skip: i += 1; continue
                rw = sorted(by_top[top], key=lambda w: w['x0'])
                names = [w['text'] for w in rw if w['x0'] < 185]
                nums = [w for w in rw if w['x0'] >= 185 and is_num_token(w['text'])]
                if not names: i += 1; continue
                contributor = ' '.join(names).strip()
                if should_skip(contributor): i += 1; continue

                if nums:
                    cv = parse_nums_neg(nums, bs)
                    if cv:
                        name_parts = [contributor]
                        # Only look for a trailing continuation line when the
                        # name itself demands one (unmatched open paren) -
                        # checking unconditionally on every single-line match
                        # risks swallowing the start of the next, unrelated
                        # entity's name.
                        if has_unmatched_open_paren(name_parts):
                            try_append_trailing(tops, by_top, i + 1, name_parts, skip)
                        results.append((' '.join(name_parts), cv))
                    i += 1; continue

                # No numbers: look ahead
                name_parts = [contributor]; found_nums = []; j = i + 1

                if j < len(tops):
                    jt = tops[j]
                    jr = sorted(by_top[jt], key=lambda w: w['x0'])
                    jnames = [w['text'] for w in jr if w['x0'] < 185]
                    jnums = [w for w in jr if w['x0'] >= 185 and is_num_token(w['text'])]

                    if not jnames and jnums:
                        # Orphan numbers row (numbers between name lines, like UK 2024)
                        found_nums = jnums; skip.add(jt); j += 1
                        try_append_trailing(tops, by_top, j, name_parts, skip)
                    else:
                        # Multi-line name search
                        while j < len(tops) and j < i + 6:
                            jt = tops[j]
                            jr = sorted(by_top[jt], key=lambda w: w['x0'])
                            jnames = [w['text'] for w in jr if w['x0'] < 185]
                            jnums = [w for w in jr if w['x0'] >= 185 and is_num_token(w['text'])]
                            if jnames:
                                js = ' '.join(jnames).strip()
                                if should_skip(js): break
                                if not found_nums:
                                    name_parts.append(js); skip.add(jt)
                                    if jnums: found_nums = jnums; j += 1; break
                                    j += 1
                                else: break
                            elif jnums:
                                found_nums = jnums; skip.add(jt); j += 1; break
                            else: j += 1
                        if found_nums:
                            try_append_trailing(tops, by_top, j, name_parts, skip)

                if found_nums:
                    cv = parse_nums_neg(found_nums, bs)
                    if cv: results.append((' '.join(name_parts), cv))
                i += 1
    return results

def extract_special(pdf_path, bs, min_top=155):
    special = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = [w for w in page.extract_words() if not is_watermark_noise(w)]
            by_top = {}
            for w in words:
                if w['top'] < min_top: continue
                rk = round(w['top'] / 3) * 3
                by_top.setdefault(rk, []).append(w)
            tops = sorted(by_top.keys())
            for idx, top in enumerate(tops):
                rw = sorted(by_top[top], key=lambda w: w['x0'])
                lt = ' '.join(w['text'] for w in rw if w['x0'] < 185)
                at = ' '.join(w['text'] for w in rw)
                label = None
                if 'Total' in lt and 'Member' in at and 'States' in at:
                    label = 'Total – Member States'
                elif lt.strip().startswith('Grand') and 'total' in at.lower():
                    label = 'Grand Total'
                elif 'Other' in lt and 'miscellaneous' in at:
                    label = 'Other and miscellaneous receipts'
                elif 'Pass' in lt and 'through' in at:
                    label = 'Pass through funding'
                elif 'Refunds' in lt and 'donors' in at:
                    label = 'Refunds to donors'
                if not label or label in special: continue
                nw = [w for w in rw if w['x0'] >= 185]
                if idx + 1 < len(tops):
                    nt = tops[idx+1]; nr = by_top[nt]
                    nl = ' '.join(w['text'] for w in nr if w['x0'] < 185).strip()
                    if nl == '' or nl.lower().startswith('(note'):
                        nw.extend([w for w in nr if w['x0'] >= 185])
                cv = parse_nums_neg(nw, bs)
                if cv: special[label] = cv
    return special

def write_csv(pdf_path, out_path):
    bs = detect_col_boundaries(pdf_path)
    rows = extract_rows(pdf_path, bs)
    special = extract_special(pdf_path, bs)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Contributor'] + COL_NAMES)
        for name, cols in rows:
            w.writerow([name] + [cols.get(i, '') for i in range(9)])
        for label in ['Total – Member States', 'Other and miscellaneous receipts',
                      'Pass through funding', 'Refunds to donors', 'Grand Total']:
            if label in special:
                w.writerow([label] + [special[label].get(i, '') for i in range(9)])
    return rows, special

if __name__ == '__main__':
    for year, pdf, out in [
        (2022, "/mnt/user-data/uploads/A76_INF2-en-voluntarytable.pdf", "/home/claude/WHO_2022_final.csv"),
        (2023, "/mnt/user-data/uploads/A77_INF2-en-voluntarytable.pdf", "/home/claude/WHO_2023_final.csv"),
        (2024, "/mnt/user-data/uploads/A78_INF3-en-table.pdf",           "/home/claude/WHO_2024_final.csv"),
    ]:
        rows, special = write_csv(pdf, out)
        print(f"\n{'='*60}")
        print(f"{year}: {len(rows)} contributor rows extracted")
        checks = ['United Kingdom', 'United States', 'Germany', 'Norway',
                  'Gates Foundation', 'Gates Philanthropy', "Children's Investment",
                  'Kitasato', 'United Nations Central', 'UNICEF', 'Christoffel']
        for name, cols in rows:
            if any(x in name for x in checks):
                print(f"  {name}")
                print(f"    {cols}")
        for k in ['Total – Member States', 'Grand Total']:
            if k in special:
                print(f"  {k}: {special[k]}")