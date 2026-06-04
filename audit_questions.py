"""
Comprehensive audit of questions.json.
Checks for:
  1. Coverage: extracted vs answer-key count per PDF
  2. Bleeding artifacts: option text containing mid-line "N. text" patterns
  3. Answer skew: suspicious answer-letter distribution per source file
  4. Option quality: very short or duplicate options
  5. Question text quality: very short, starts with option marker, etc.
  6. Duplicate questions (same text from different years)
Run: python audit_questions.py > audit_out.txt 2>&1
"""
import json, re, sys, io
from collections import defaultdict, Counter
from pathlib import Path

import fitz
import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATA_PATH = Path(r"C:\Users\Adi\Code\Chinease_medicine\questions.json")
BASE_DIR  = Path(r"C:\Users\Adi\Code\Chinease_medicine\Data\extracted\מבחן הסמכה שאלות לדוגמא מבחנים 2019-2012")

BIDI = re.compile(r'[​-‏‪-‮⁦-⁩﻿]')
_Q_NUM_MID = re.compile(r'\s\d{1,2}\.(?!\d)\s')  # "N. text" mid-string
_LETTER_MARKER = re.compile(r'^[אבגד]\.')

def clean(t):
    t = BIDI.sub(' ', str(t or ''))
    return re.sub(r'\s+', ' ', t).strip()


# ── 1. Load questions ──────────────────────────────────────────────────────────

data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
all_questions = []
for topic in data['topics']:
    for q in topic['questions']:
        q['_topic'] = topic['name']
        all_questions.append(q)

print(f"Total questions loaded: {len(all_questions)}")
print(f"Topics: {[t['name'] + ' (' + str(len(t['questions'])) + ')' for t in data['topics']]}\n")


# ── 2. Per-source coverage ─────────────────────────────────────────────────────

def extract_answers_count(pdf_path):
    answers = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table or len(table) < 2:
                        continue
                    header = [clean(c) for c in table[0]]
                    if not header or header[0] not in ('תובושת', 'תשובות', 'שאלות'):
                        continue
                    col_qnums = []
                    for cell in header[1:]:
                        nums = [int(n) for n in re.findall(r'\d+', cell) if 1 <= int(n) <= 50]
                        col_qnums.append(nums)
                    for row in table[1:]:
                        if not row: continue
                        letter = clean(row[0])
                        if letter not in ('א', 'ב', 'ג', 'ד'): continue
                        for ci, cell in enumerate(row[1:]):
                            if ci >= len(col_qnums): break
                            if 'X' not in clean(cell): continue
                            if len(col_qnums[ci]) == 1:
                                answers[col_qnums[ci][0]] = letter
    except:
        pass
    return answers

print("=" * 70)
print("COVERAGE AUDIT (extracted q / answer-key q per PDF)")
print("=" * 70)

by_source = defaultdict(list)
for q in all_questions:
    src = q.get('source', '')
    # source format: "יסודות 2016 שאלה 3" → file stem = "יסודות 2016"
    m = re.match(r'^(.+?) שאלה (\d+)$', src)
    if m:
        by_source[m.group(1)].append(int(m.group(2)))

answer_pdfs = {p.stem: p for p in BASE_DIR.glob("*.pdf") if 'תשובות' in p.name}
coverage_issues = []

for stem, qnums in sorted(by_source.items()):
    a_stem = stem + ' תשובות'
    a_pdf  = answer_pdfs.get(a_stem)
    if a_pdf is None:
        print(f"  {stem}: {len(qnums)} extracted  [no answer PDF found]")
        continue
    ans_count = len(extract_answers_count(a_pdf))
    coverage = len(qnums) / ans_count * 100 if ans_count else 0
    flag = ''
    if coverage < 70:
        flag = ' ◄ LOW COVERAGE'
        coverage_issues.append((stem, len(qnums), ans_count))
    print(f"  {stem}: {len(qnums)}/{ans_count} extracted ({coverage:.0f}%){flag}")

if coverage_issues:
    print(f"\n  [{len(coverage_issues)} files with <70% coverage]")
else:
    print("\n  [All files ≥70% coverage]")


# ── 3. Bleeding artifact check ────────────────────────────────────────────────

print("\n" + "=" * 70)
print("BLEEDING ARTIFACT AUDIT (mid-option question-number patterns)")
print("=" * 70)

bleed_found = []
for q in all_questions:
    for i, opt in enumerate(q['options']):
        if _Q_NUM_MID.search(opt):
            bleed_found.append((q.get('source','?'), i, opt))

if bleed_found:
    print(f"  [{len(bleed_found)} options with suspected bleeding]")
    for src, i, opt in bleed_found[:20]:
        letters = ['א','ב','ג','ד']
        print(f"  {src} opt-{letters[i]}: {opt[:80]}")
else:
    print("  [No bleeding artifacts found]")


# ── 4. Answer distribution per source ────────────────────────────────────────

print("\n" + "=" * 70)
print("ANSWER DISTRIBUTION AUDIT (suspicious skew per source)")
print("=" * 70)

skew_issues = []
for stem, qnums in sorted(by_source.items()):
    src_qs = [q for q in all_questions if q.get('source','').startswith(stem + ' שאלה')]
    if len(src_qs) < 5:
        continue
    counts = Counter(q['answer'] for q in src_qs)
    total  = len(src_qs)
    for idx, cnt in counts.items():
        pct = cnt / total * 100
        if pct > 60:  # more than 60% same answer is suspicious
            skew_issues.append((stem, idx, cnt, total))
            print(f"  {stem}: answer {idx} appears {cnt}/{total} ({pct:.0f}%) ◄ SUSPICIOUS SKEW")

if not skew_issues:
    print("  [No suspicious answer skew detected]")


# ── 5. Option quality check ───────────────────────────────────────────────────

print("\n" + "=" * 70)
print("OPTION QUALITY AUDIT (short, duplicate, or malformed options)")
print("=" * 70)

opt_issues = []
for q in all_questions:
    src = q.get('source', '?')
    # Very short option
    for i, opt in enumerate(q['options']):
        if len(opt) < 3:
            opt_issues.append(('short-option', src, i, opt))
    # Duplicate options
    if len(set(q['options'])) < 4:
        dupes = [o for o in q['options'] if q['options'].count(o) > 1]
        opt_issues.append(('duplicate-option', src, -1, str(set(dupes))))
    # Option starting with a letter marker (א./ב.) - suggests parse error
    for i, opt in enumerate(q['options']):
        if _LETTER_MARKER.match(opt):
            opt_issues.append(('marker-in-option', src, i, opt[:60]))

if opt_issues:
    print(f"  [{len(opt_issues)} option quality issues]")
    shown = 0
    for kind, src, i, text in opt_issues:
        if shown >= 30: print("  ... (truncated)"); break
        letters = ['א','ב','ג','ד']
        label = f"opt-{letters[i]}" if i >= 0 else 'dup'
        print(f"  [{kind}] {src} {label}: {text}")
        shown += 1
else:
    print("  [No option quality issues]")


# ── 6. Question text quality ──────────────────────────────────────────────────

print("\n" + "=" * 70)
print("QUESTION TEXT QUALITY AUDIT")
print("=" * 70)

q_issues = []
for q in all_questions:
    src = q.get('source', '?')
    qt  = q['q']
    if len(qt) < 15:
        q_issues.append(('too-short', src, qt))
    elif _LETTER_MARKER.match(qt):
        q_issues.append(('starts-with-marker', src, qt[:60]))
    elif re.match(r'^\d+\.?\s', qt) and len(qt) < 40:
        q_issues.append(('starts-with-number', src, qt[:60]))

if q_issues:
    print(f"  [{len(q_issues)} question text issues]")
    for kind, src, text in q_issues[:20]:
        print(f"  [{kind}] {src}: {text}")
else:
    print("  [No question text issues]")


# ── 7. Duplicate questions across years ──────────────────────────────────────

print("\n" + "=" * 70)
print("DUPLICATE QUESTIONS ACROSS YEARS (same text, different source)")
print("=" * 70)

by_text = defaultdict(list)
for q in all_questions:
    key = re.sub(r'\s+', ' ', q['q'].strip())[:80]
    by_text[key].append(q.get('source', '?'))

true_dupes = {k: v for k, v in by_text.items() if len(v) > 1}
print(f"  {len(true_dupes)} question texts appear in multiple sources")
print(f"  (expected - same question reused across years)\n")

# Show ones where SAME source has duplicates (unexpected)
same_src_dupes = {k: v for k, v in true_dupes.items() if len(set(v)) < len(v)}
if same_src_dupes:
    print(f"  [{len(same_src_dupes)} questions duplicated WITHIN same source - unexpected]")
    for text, srcs in list(same_src_dupes.items())[:10]:
        print(f"  {srcs}: {text[:60]}")
else:
    print("  [No within-source duplicates - OK]")


# ── 8. Answer consistency for reused questions ────────────────────────────────

print("\n" + "=" * 70)
print("ANSWER CONSISTENCY FOR REUSED QUESTIONS")
print("=" * 70)

answer_mismatch = []
for key, srcs in true_dupes.items():
    qs_with_key = [q for q in all_questions if re.sub(r'\s+', ' ', q['q'].strip())[:80] == key]
    answers = set(q['answer'] for q in qs_with_key)
    if len(answers) > 1:
        answer_mismatch.append((key, [(q.get('source','?'), q['answer'], q['options'][q['answer']][:40]) for q in qs_with_key]))

if answer_mismatch:
    print(f"  [{len(answer_mismatch)} questions with INCONSISTENT answers across years]")
    for text, instances in answer_mismatch[:15]:
        print(f"\n  Q: {text[:70]}")
        for src, ans_idx, ans_text in instances:
            print(f"    {src} → option {ans_idx}: {ans_text}")
else:
    print("  [All reused questions have consistent answers - OK]")


# ── Summary ───────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Total questions:          {len(all_questions)}")
print(f"  Coverage issues (<70%):   {len(coverage_issues)}")
print(f"  Bleeding artifacts:       {len(bleed_found)}")
print(f"  Answer skew issues:       {len(skew_issues)}")
print(f"  Option quality issues:    {len(opt_issues)}")
print(f"  Question text issues:     {len(q_issues)}")
print(f"  Answer inconsistencies:   {len(answer_mismatch)}")
