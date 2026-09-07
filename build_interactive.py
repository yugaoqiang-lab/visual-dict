# -*- coding: utf-8 -*-
"""
Build an interactive version of the PDF that KEEPS the original page images
and only adds, after every English word:
  - an American-style IPA (normalized from the bundled ECDICT dict + RP->GA shift)
  - click-to-pronounce (uses the browser's en-US TTS -> genuinely American audio)

Pipeline:
  1. Render each content page to JPEG (original illustrations preserved).
  2. Extract every English label's bounding box (percent based) via PyMuPDF.
  3. Attach IPA to each label (lookup in ECDICT, normalized + British->American).
  4. Emit pages_meta.json and a self-contained index2.html (overlay embedded).
"""
import os, re, json, sys
import pymupdf as fitz

PDF = r"C:\Users\Administrator\Desktop\Chinese-English Bilingual Visual Dictionary.pdf"
OUT = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(OUT, "pages")
os.makedirs(PAGES_DIR, exist_ok=True)

# content pages (1-indexed) -- index starts at p326, cover/toc before p13
START, END = 13, 325
ZOOM = 2.0
JQ = 82
RERENDER = False   # reuse existing page images, only recompute words+IPA

# ---------- load base dictionary ----------
dic = json.load(open(os.path.join(OUT, "cards-data", "ecdict_base.json"), encoding="utf-8"))

EN = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")

def to_american(ipa):
    """Normalize a messy ECDICT phonetic into a clean, American-leaning IPA.

    Keeps length marks on iː/uː/ɑː (dropping them makes e.g. bu:ts -> buts,
    which a reader misreads). Applies clear RP/ECDICT -> General-American shifts.
    """
    if not ipa:
        return ""
    s = ipa.strip().strip("/").strip()
    if not s:
        return ""
    if "." in s:                      # ECDICT sometimes joins variants with '.'
        s = s.split(".")[0]
    # fix mojibake / alternate glyphs
    s = s.replace("ә", "ə").replace("ε", "e").replace("є", "e").replace("ɵ", "θ")
    s = s.replace("ˋ", "").replace("ˊ", "").replace("^", "")
    s = s.replace("'", "ˈ")           # ascii apostrophe -> primary stress
    s = s.replace(":", "ː")           # length colon -> IPA length mark
    # multi-char RP/ECDICT diphthongs -> standard (GA where clear)
    s = s.replace("əʊ", "oʊ").replace("əu", "oʊ")
    s = s.replace("ai", "aɪ").replace("au", "aʊ")
    s = s.replace("ei", "eɪ")
    s = s.replace("ɪə", "ɪr").replace("eə", "ɛr").replace("ʊə", "ʊr")
    # single-char RP -> GA
    s = s.replace("ɒ", "ɑ")           # LOT/PALM/CLOTH -> American /ɑ/
    s = s.replace("ɜː", "ɝ")
    s = s.replace("ɔː", "ɔ")          # drop length on this one (ɔ vs ɔː both read "aw")
    s = re.sub(r"\s+", "", s)
    if not s:
        return ""
    return "/" + s + "/"

def lookup(word):
    w = word.strip().lower()
    for k in (w, w.rstrip("'"), w.rstrip("'s")):
        if k in dic and dic[k] and dic[k][0]:
            return to_american(dic[k][0])
    # light stemming
    for k in (w.rstrip("s"), w.rstrip("es"), w[:-3] + "y" if w.endswith("ies") else w):
        if k in dic and dic[k] and dic[k][0]:
            return to_american(dic[k][0])
    return ""

def ipa_for(text):
    parts = text.split()
    # try full phrase, then each word
    ip = lookup(text)
    if ip:
        return ip
    for p in parts:
        ip = lookup(p)
        if ip:
            return ip
    return ""

def extract_words(page):
    words = page.get_text("words")  # x0,y0,x1,y1,word,block,line,wordno
    en = [(w[0], w[1], w[2], w[3], w[4]) for w in words if EN.match(w[4])]
    en.sort(key=lambda t: (round(t[1] / 4), t[0]))
    groups = []
    cur = None
    cy = None
    px1 = None
    gx0 = gy0 = gx1 = gy1 = None
    for x0, y0, x1, y1, w in en:
        if cur is None:
            cur = [w]; cy = y0; px1 = x1; gx0, gy0, gx1, gy1 = x0, y0, x1, y1
        else:
            if abs(y0 - cy) > 4:                      # new line -> new label
                groups.append((gx0, gy0, gx1, gy1, cur)); cur = [w]; cy = y0; px1 = x1
                gx0, gy0, gx1, gy1 = x0, y0, x1, y1
            elif x0 - px1 > 25:                       # same line, big gap -> new label
                groups.append((gx0, gy0, gx1, gy1, cur)); cur = [w]; cy = y0; px1 = x1
                gx0, gy0, gx1, gy1 = x0, y0, x1, y1
            else:                                     # same label
                cur.append(w); px1 = x1
                gx1 = max(gx1, x1); gy1 = max(gy1, y1); gy0 = min(gy0, y0)
    if cur:
        groups.append((gx0, gy0, gx1, gy1, cur))
    return groups

def main():
    doc = fitz.open(PDF)
    pw = doc[0].rect.width
    ph = doc[0].rect.height
    pages = []
    total = 0
    ipa_hits = 0
    for pno in range(START, END + 1):
        idx = pno - 1
        page = doc[idx]
        # render (skip if image already exists and RERENDER is off)
        fname = "page_%03d.jpg" % pno
        fpath = os.path.join(PAGES_DIR, fname)
        if RERENDER or not os.path.exists(fpath):
            mat = fitz.Matrix(ZOOM, ZOOM)
            pix = page.get_pixmap(matrix=mat)
            pix.save(fpath, output="jpeg", jpg_quality=JQ)
        # words
        groups = extract_words(page)
        words = []
        for x0, y0, x1, y1, ws in groups:
            text = " ".join(ws)
            x = round(x0 / pw * 100, 3)
            y = round(y0 / ph * 100, 3)
            w = round((x1 - x0) / pw * 100, 3)
            h = round((y1 - y0) / ph * 100, 3)
            ipa = ipa_for(text)
            if ipa:
                ipa_hits += 1
            words.append({"x": x, "y": y, "w": w, "h": h, "t": text, "ipa": ipa})
            total += 1
        pages.append({"n": pno, "img": "pages/" + fname, "words": words})
        if (pno - START + 1) % 25 == 0:
            print(f"  rendered page {pno} ({len(pages)} pages, {total} words)")
    doc.close()
    json.dump(pages, open(os.path.join(OUT, "pages_meta.json"), "w", encoding="utf-8"))
    print(f"DONE: {len(pages)} pages, {total} english labels, {ipa_hits} with IPA "
          f"({100*ipa_hits/max(total,1):.1f}%)")
    return pages

if __name__ == "__main__":
    main()
