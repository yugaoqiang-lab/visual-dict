# -*- coding: utf-8 -*-
"""
从《Chinese-English Bilingual Visual Dictionary》(DK 图解词典) PDF 抽取单词，
按「中文 -> 拼音 -> 英文」的版式解析，输出：
  - cards-data/pdf_entries.json   原始条目 (en, zh, pinyin)
  - cards-data/word_list.csv      单词表
  - cards-data/cards.json         闪卡数据 (供模板注入)
  - cards-data/dict.json          离线词典 (复用既有 ECDICT 注音 + 本书中文)
"""
import re, json, csv, os

PDF = r"C:\Users\Administrator\Desktop\Chinese-English Bilingual Visual Dictionary.pdf"
OUT = r"C:\Users\Administrator\WorkBuddy\图解词典\visual-dict\cards-data"
ECDICT_BASE = os.path.join(OUT, "ecdict_base.json")

CJK = re.compile(r'[\u4e00-\u9fff]')
HAS_DIGIT = re.compile(r'\d')
HEADER = re.compile(r'[•·]')  # 章节标题分隔符
# 仅在拼音中出现的声调符号（英文外来词一般只用 áéíóúàè 等，不含下面这些）
PINYIN_TONE = re.compile(r'[āǎàēěèīǐōǒòūǔǖǘǚǜńň]')

def has_cjk(s): return bool(CJK.search(s))

def flatten_page(page):
    """把一页的 block 文本按出现顺序拆成行列表。"""
    lines = []
    for b in page.get_text("blocks"):
        t = b[4].strip()
        if not t:
            continue
        for ln in t.split('\n'):
            ln = ln.strip()
            if ln:
                lines.append(ln)
    return lines

def clean_lines(lines):
    """丢弃纯页码、含标题分隔符的行。"""
    out = []
    for ln in lines:
        if HEADER.search(ln):
            continue
        if HAS_DIGIT.search(ln):
            continue  # 页码 / 索引页码
        out.append(ln)
    return out

def is_clean(e):
    """丢弃明显错配的条目：英文里混入了拼音声调符号，或英文==拼音。"""
    en = e['en'].strip()
    if not en:
        return False
    if PINYIN_TONE.search(en):
        return False
    if e['py'] and en.lower() == e['py'].lower():
        return False
    return True

def parse_entries(lines):
    """
    核心：每个标签 = 中文标题行 + 其后若干非中文行（拼音在前、英文在最后）。
    取「下一个中文行之前」的最后一行作为英文，其余作为拼音。
    """
    entries = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not has_cjk(line):
            i += 1
            continue
        # 中文标题行：抽取汉字与可能的内联拼音
        cn = re.sub(r'[^\u4e00-\u9fff]', '', line)
        inline_lat = re.sub(r'[\u4e00-\u9fff]', '', line).strip()
        # 收集其后连续的非中文行作为 tail
        tail = []
        j = i + 1
        while j < n and not has_cjk(lines[j]):
            tail.append(lines[j])
            j += 1
        if tail:
            english = tail[-1]
            pinyin_parts = ([inline_lat] if inline_lat else []) + tail[:-1]
        else:
            english = ''
            pinyin_parts = [inline_lat] if inline_lat else []
        pinyin = ' '.join(p.strip() for p in pinyin_parts if p.strip())
        if cn and english:
            entries.append({'cn': cn, 'py': pinyin, 'en': english})
        i = j if j > i + 1 else i + 1
    return entries

def parse_page(page):
    lines = clean_lines(flatten_page(page))
    if not lines:
        return []
    return [e for e in parse_entries(lines) if is_clean(e)]

def main():
    import pymupdf as fitz
    doc = fitz.open(PDF)
    print("总页数:", doc.page_count)

    all_entries = []
    # 内容页范围：跳过封面/目录/前言(1-12) 与 末尾索引(326-361)
    start, end = 12, 324  # 0-based -> 第13页 ~ 第325页
    skipped = 0
    for idx in range(start, end + 1):
        page = doc[idx]
        ents = parse_page(page)
        if not ents:
            skipped += 1
            continue
        all_entries.extend(ents)

    print("抽取原始条目数:", len(all_entries))
    print("空内容页(跳过)数:", skipped)

    # ---- 去重：以英文(小写)为主键，优先保留有拼音的 ----
    dedup = {}
    for e in all_entries:
        key = e['en'].strip().lower()
        key = re.sub(r'\s+', ' ', key)
        if not key:
            continue
        if key not in dedup:
            dedup[key] = e
        else:
            # 已有则优先补充拼音
            if not dedup[key]['py'] and e['py']:
                dedup[key]['py'] = e['py']
    entries = list(dedup.values())
    print("去重后条目数:", len(entries))

    # ---- 写原始条目 ----
    with open(os.path.join(OUT, "pdf_entries.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    # ---- 单词表 CSV ----
    with open(os.path.join(OUT, "word_list.csv"), "w", encoding="utf-8-sig", newline='') as f:
        w = csv.writer(f)
        w.writerow(["No.", "English", "中文", "拼音", "中文+拼音"])
        for i, e in enumerate(entries, 1):
            w.writerow([i, e['en'], e['cn'], e['py'], f"{e['cn']} {e['py']}".strip()])
    print("已写 word_list.csv")

    # ---- 构建 cards.json ----
    cards = []
    for e in entries:
        zh = f"{e['cn']} {e['py']}".strip()
        en = e['en'].strip()
        cards.append({
            "en": [[en, True]],
            "en_text": en,
            "zh": zh
        })
    with open(os.path.join(OUT, "cards.json"), "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False)
    print("已写 cards.json, 卡片数:", len(cards))

    # ---- 构建 dict.json (复用 ECDICT 注音) ----
    try:
        with open(ECDICT_BASE, encoding="utf-8") as f:
            base = json.load(f)
    except Exception:
        base = {}
    dic = {}
    for e in entries:
        en = e['en'].strip().lower()
        en = re.sub(r'\s+', ' ', en)
        zh = f"{e['cn']} {e['py']}".strip()
        ipa = ''
        if en in base and base[en][0]:
            ipa = base[en][0]
        dic[en] = [ipa, zh]
    with open(os.path.join(OUT, "dict.json"), "w", encoding="utf-8") as f:
        json.dump(dic, f, ensure_ascii=False)
    print("已写 dict.json, 词条数:", len(dic))

    # ---- 抽样展示 ----
    print("\n===== 抽样(前15条) =====")
    for e in entries[:15]:
        print(f"  {e['en']:<28} | {e['cn']} {e['py']}")

if __name__ == "__main__":
    main()
