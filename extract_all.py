"""
Extract TCM exam questions from Hebrew PDFs → questions.json
"""
import fitz
import pdfplumber
import re, json, sys, io
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = Path(r"C:\Users\Adi\Code\Chinease_medicine\Data\extracted\מבחן הסמכה שאלות לדוגמא מבחנים 2019-2012")

TOPICS = {
    'יסודות':       {'id': 'yesodot',  'name': 'יסודות הרפואה הסינית'},
    'דיקור':        {'id': 'dikur',    'name': 'דיקור'},
    'איתור':        {'id': 'itur',     'name': 'איתור נקודות'},
    'צמחים':        {'id': 'tsmakim',  'name': 'צמחים סיניים'},
    'מערבית':       {'id': 'maaravit', 'name': 'רפואה מערבית'},
    'רפואה מערבית': {'id': 'maaravit', 'name': 'רפואה מערבית'},
}

BIDI = re.compile(r'[​-‏‪-‮⁦-⁩﻿]')

def clean(t):
    # Replace bidi control chars with spaces to preserve word boundaries
    t = BIDI.sub(' ', str(t or ''))
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


# ── Answer key (via pdfplumber table extraction) ───────────────────────────────

def extract_answers(pdf_path):
    """Read answer key tables; skip ambiguous merged cells."""
    answers = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table or len(table) < 2:
                        continue
                    header = [clean(c) for c in table[0]]
                    # Detect answer-key table: first cell is 'תובושת' (reversed 'תשובות')
                    if not header or header[0] not in ('תובושת', 'תשובות', 'שאלות'):
                        continue

                    # Map each header column to a list of question numbers
                    col_qnums = []
                    for cell in header[1:]:
                        nums = [int(n) for n in re.findall(r'\d+', cell)
                                if 1 <= int(n) <= 50]
                        col_qnums.append(nums)

                    for row in table[1:]:
                        if not row:
                            continue
                        letter = clean(row[0])
                        if letter not in ('א', 'ב', 'ג', 'ד'):
                            continue
                        for ci, cell in enumerate(row[1:]):
                            if ci >= len(col_qnums):
                                break
                            cell_s = clean(cell)
                            if 'X' not in cell_s:
                                continue
                            qnums = col_qnums[ci]
                            if len(qnums) == 1:
                                answers[qnums[0]] = letter
                            # len>1 = merged cell → ambiguous, skip
    except Exception as e:
        print(f"  [WARN] answer extraction: {e}")
    return answers


# ── Question text (via PyMuPDF) ────────────────────────────────────────────────

def extract_raw_lines(pdf_path):
    doc = fitz.open(str(pdf_path))
    lines = []
    for page in doc:
        for ln in page.get_text("text").split('\n'):
            l = clean(ln).strip()
            if l:
                lines.append(l)
    doc.close()
    return lines


# ── Format detection ───────────────────────────────────────────────────────────

def detect_format(lines):
    """Return 'digits' (1/2/3/4 options) or 'hebrew' (א./ב./ג./ד. options)."""
    for l in lines:
        if re.match(r'^[אבגד]\.\s*', l):
            return 'hebrew'
    return 'digits'


# ── Format A: options are standalone digits 1,2,3,4 ───────────────────────────

def find_digit_option_blocks(lines):
    """Find (i1,i2,i3,i4) where lines[iN]=='N' in sequence."""
    blocks, i, n = [], 0, len(lines)

    def search(start, target, window=20):
        j = start
        while j < min(start + window, n):
            if lines[j] == str(target):
                return j
            j += 1
        return None

    while i < n:
        if lines[i] == '1':
            j = search(i + 1, 2)
            if j is None: i += 1; continue
            k = search(j + 1, 3)
            if k is None: i += 1; continue
            m = search(k + 1, 4)
            if m is None: i += 1; continue
            blocks.append((i, j, k, m))
            i = m + 1
        else:
            i += 1
    return blocks


_STANDALONE_INT = re.compile(r'^\d{1,2}$')
# Matches "3. text" or "3.text" (inline question number) but NOT "3.5" (decimal)
_Q_NUM_INLINE   = re.compile(r'^\d{1,2}\.(?:[^\d.]|$)')


def _is_inline_qnum(line):
    """Return (q_num, rest_text) if line starts an inline question number, else None."""
    m = re.match(r'^(\d{1,2})\.\s*(.*)', line)
    if m and 1 <= int(m.group(1)) <= 50:
        after_dot = m.group(0)[len(m.group(1)) + 1:]  # everything after the digit
        # exclude decimals like "3.5"
        if re.match(r'^\.\d', '.' + after_dot.lstrip('.')):
            return None
        return int(m.group(1)), m.group(2).strip()
    return None


def clean_block(lines_list, stop_at_qnum=False):
    """Join lines into text.  If stop_at_qnum=True, break at next standalone int ≥2."""
    parts = []
    for l in lines_list:
        if l in ('.', '..'):
            continue
        # Stop at next question number (standalone digit or "N. text")
        if stop_at_qnum:
            if _STANDALONE_INT.match(l) and int(l) >= 2:
                break
            if _Q_NUM_INLINE.match(l):
                break
        if l.startswith('.') and len(l) > 1:
            parts.append(l[1:].strip())
        elif l.startswith('?') and len(l) > 1:
            parts.append(l[1:].strip() + '?')
        else:
            parts.append(l)
    t = ' '.join(parts)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\(\s+', '(', t)
    t = re.sub(r'\s+\)', ')', t)
    return t.strip()


def _scan_q_raw(q_raw):
    """Scan pre-option lines for question number and body text.
    Handles both standalone '3' and inline '3. text' patterns."""
    q_num = None
    q_body = []
    for ql in q_raw:
        # Standalone number: "3"
        if re.match(r'^\d+$', ql) and 1 <= int(ql) <= 50:
            q_num = int(ql)
            q_body = []
        # Inline number + text: "3. מטופלת..."
        elif _Q_NUM_INLINE.match(ql):
            parsed = _is_inline_qnum(ql)
            if parsed:
                q_num, inline_text = parsed
                q_body = []
                if inline_text:
                    q_body.append(inline_text)
        elif q_num is not None and ql not in ('.', '..'):
            q_body.append(ql)
    return q_num, q_body


def parse_digit_format(lines, answers, source_name=''):
    questions = []
    blocks = find_digit_option_blocks(lines)

    for b_idx, (i1, i2, i3, i4) in enumerate(blocks):
        prev_end = blocks[b_idx - 1][3] + 1 if b_idx > 0 else 0
        q_raw = lines[prev_end:i1]
        q_num, q_body = _scan_q_raw(q_raw)

        if q_num is None:
            continue  # skip if no question number found

        # option 4 ends at next block's start or EOF
        opt4_end = blocks[b_idx + 1][0] if b_idx + 1 < len(blocks) else len(lines)

        opt1 = clean_block(lines[i1 + 1: i2])
        opt2 = clean_block(lines[i2 + 1: i3])
        opt3 = clean_block(lines[i3 + 1: i4])
        opt4 = clean_block(lines[i4 + 1: opt4_end], stop_at_qnum=True)
        q_text = clean_block(q_body, stop_at_qnum=True)

        if not q_text or not all([opt1, opt2, opt3, opt4]):
            continue

        correct_letter = answers.get(q_num)
        correct_idx = {'א': 0, 'ב': 1, 'ג': 2, 'ד': 3}.get(correct_letter)
        if correct_idx is None:
            continue

        questions.append({
            'q': q_text,
            'options': [opt1, opt2, opt3, opt4],
            'answer': correct_idx,
            'source': f'{source_name} שאלה {q_num}',
        })
    return questions


# ── Format B: options start with א./ב./ג./ד. ──────────────────────────────────

_ALEF  = re.compile(r'^א\.')
_BET   = re.compile(r'^ב\.')
_GIMEL = re.compile(r'^ג\.')
_DALET = re.compile(r'^ד\.')
_LETTER_MARKER = re.compile(r'^[אבגד]\.')

def find_hebrew_option_blocks(lines):
    blocks, i, n = [], 0, len(lines)

    def search(start, pat, window=25):
        j = start
        while j < min(start + window, n):
            if pat.match(lines[j]):
                return j
            j += 1
        return None

    while i < n:
        if _ALEF.match(lines[i]):
            j = search(i + 1, _BET)
            if j is None: i += 1; continue
            k = search(j + 1, _GIMEL)
            if k is None: i += 1; continue
            m = search(k + 1, _DALET)
            if m is None: i += 1; continue
            blocks.append((i, j, k, m))
            i = m + 1
        else:
            i += 1
    return blocks


def option_text_from_marker(marker_line, body_lines):
    """Extract option text: inline after marker OR from following body lines."""
    m = re.match(r'^[אבגד]\.\s*(.*)', marker_line)
    inline = m.group(1).strip() if m else ''
    parts = [inline] if inline else []
    for l in body_lines:
        # Stop at next option marker, standalone question number, or inline "N. text"
        if _LETTER_MARKER.match(l) or re.match(r'^\d+$', l) or _Q_NUM_INLINE.match(l):
            break
        if l in ('.', '..'):
            continue
        if l.startswith('.') and len(l) > 1:
            parts.append(l[1:].strip())
        elif l.startswith('?') and len(l) > 1:
            parts.append(l[1:].strip() + '?')
        else:
            parts.append(l)
    t = ' '.join(parts)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\(\s+', '(', t)
    t = re.sub(r'\s+\)', ')', t)
    # Truncate at a mid-line question number: "option text N. next question text"
    # This handles cases where PyMuPDF merges two lines into one.
    # (?!\d) ensures we don't match decimals like "1.5"
    t = re.sub(r'\s+\d{1,2}\.(?!\d)\s+.*$', '', t)
    return t.strip()


def parse_hebrew_format(lines, answers, source_name=''):
    questions = []
    blocks = find_hebrew_option_blocks(lines)

    for b_idx, (i1, i2, i3, i4) in enumerate(blocks):
        prev_end = blocks[b_idx - 1][3] + 1 if b_idx > 0 else 0
        q_raw = lines[prev_end:i1]
        q_num, q_body = _scan_q_raw(q_raw)

        if q_num is None:
            continue  # skip if no question number found

        opt4_end = blocks[b_idx + 1][0] if b_idx + 1 < len(blocks) else len(lines)

        opt1 = option_text_from_marker(lines[i1], lines[i1 + 1: i2])
        opt2 = option_text_from_marker(lines[i2], lines[i2 + 1: i3])
        opt3 = option_text_from_marker(lines[i3], lines[i3 + 1: i4])
        opt4 = option_text_from_marker(lines[i4], lines[i4 + 1: opt4_end])

        q_text = clean_block(q_body)

        if not q_text or not all([opt1, opt2, opt3, opt4]):
            continue

        correct_letter = answers.get(q_num)
        correct_idx = {'א': 0, 'ב': 1, 'ג': 2, 'ד': 3}.get(correct_letter)
        if correct_idx is None:
            continue

        questions.append({
            'q': q_text,
            'options': [opt1, opt2, opt3, opt4],
            'answer': correct_idx,
            'source': f'{source_name} שאלה {q_num}',
        })
    return questions


# ── Main ───────────────────────────────────────────────────────────────────────

_GARBAGE_WORDS  = re.compile(r'שאלות|דקות|בהצלחה|אוקטובר|ינואר|יוני')
_PICTURE_Q      = re.compile(r'ציור|תמונ')   # requires a diagram not in the app

def quality_ok(q):
    qt = q['q']
    if len(qt) < 15:
        return False
    if _GARBAGE_WORDS.search(qt) and len(qt) < 40:
        return False
    if not any(len(o) >= 3 for o in q['options']):
        return False
    if _PICTURE_Q.search(qt):
        return False
    return True


def process_pair(q_pdf, a_pdf):
    print(f"  {q_pdf.name}")
    answers = extract_answers(a_pdf)
    if not answers:
        print(f"    [WARN] no answers")
        return []
    lines = extract_raw_lines(q_pdf)
    fmt = detect_format(lines)
    source_name = q_pdf.stem  # e.g. "יסודות 2014"
    if fmt == 'digits':
        qs = parse_digit_format(lines, answers, source_name)
    else:
        qs = parse_hebrew_format(lines, answers, source_name)
    qs = [q for q in qs if quality_ok(q)]
    print(f"    [{fmt}] {len(qs)} q / {len(answers)} ans")
    return qs


def main():
    all_pdfs = sorted(BASE_DIR.glob("*.pdf"))
    answer_pdfs = {p.stem: p for p in all_pdfs if 'תשובות' in p.name}
    question_pdfs = [p for p in all_pdfs
                     if 'תשובות' not in p.name
                     and 'לדוגמא' not in p.name
                     and 'טקסט' not in p.name]

    topic_questions = defaultdict(list)

    for q_pdf in question_pdfs:
        topic_key = next((tk for tk in TOPICS if q_pdf.stem.startswith(tk)), None)
        if topic_key is None:
            continue
        a_stem = q_pdf.stem + ' תשובות'
        a_pdf = answer_pdfs.get(a_stem)
        if a_pdf is None:
            print(f"  [SKIP] no answer file: {q_pdf.name}")
            continue
        qs = process_pair(q_pdf, a_pdf)
        topic_questions[TOPICS[topic_key]['id']].extend(qs)

    output = {'topics': []}
    seen = set()
    for meta in TOPICS.values():
        tid = meta['id']
        if tid in seen:
            continue
        seen.add(tid)
        qs = topic_questions.get(tid, [])
        if qs:
            output['topics'].append({'id': tid, 'name': meta['name'], 'questions': qs})
            print(f"\n{meta['name']}: {len(qs)} questions")

    out = Path(r"C:\Users\Adi\Code\Chinease_medicine\questions.json")
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(len(t['questions']) for t in output['topics'])
    print(f"\n✓ {total} questions total → {out}")


if __name__ == '__main__':
    main()
