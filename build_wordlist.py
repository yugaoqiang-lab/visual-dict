# -*- coding: utf-8 -*-
"""从 pages_meta.json 生成「单词 + 美式音标」对照表（去重、按字母排序）。
输出：
  cards-data/word_ipa_list.csv   (UTF-8 BOM, Excel 直接打开)
  cards-data/word_ipa_list.md    (Markdown, 便于阅读/打印)
"""
import os, json, re
from collections import defaultdict

OUT = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(OUT, "pages_meta.json")
CSV = os.path.join(OUT, "cards-data", "word_ipa_list.csv")
MD = os.path.join(OUT, "cards-data", "word_ipa_list.md")

pages = json.load(open(META, encoding="utf-8"))

# word(lower) -> {display: 最常见原始大小写, ipa: 首个非空音标, pages: [页码...]}
info = {}
for p in pages:
    pn = p["n"]
    for w in p["words"]:
        t = w["t"].strip()
        if not t:
            continue
        key = t.lower()
        ipa = w.get("ipa", "") or ""
        ap = bool(w.get("approx"))
        rec = info.get(key)
        if rec is None:
            info[key] = {"display": t, "ipa": ipa, "approx": ap, "count": 1, "first_page": pn, "pages": [pn]}
        else:
            rec["count"] += 1
            rec["pages"].append(pn)
            if not rec["ipa"] and ipa:
                rec["ipa"] = ipa
            if not rec.get("approx") and ap:
                rec["approx"] = True
            # 保留更有代表性的原始大小写（首字母大写优先，更像词条）
            if t[:1].isupper() and not rec["display"][:1].isupper():
                rec["display"] = t

# 排序：先按字母（忽略大小写）
items = sorted(info.items(), key=lambda kv: kv[0])

total = len(items)
with_ipa = sum(1 for _, r in items if r["ipa"])

# ---- CSV (BOM) ----
with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
    f.write("No.,English,IPA(美式),近似?,出现页,出现次数\n")
    for i, (key, r) in enumerate(items, 1):
        pages_str = str(r["first_page"])  # 首次出现页
        approx = "是" if r.get("approx") else ""
        f.write("%d,%s,%s,%s,%s,%d\n" % (i, r["display"], r["ipa"], approx, pages_str, r["count"]))

# ---- Markdown ----
with open(MD, "w", encoding="utf-8") as f:
    f.write("# 图解词典 · 单词 + 美式音标对照表\n\n")
    f.write("共 **%d** 个去重单词，全部带美式音标；其中 **%d** 个为规则推算的近似音标（≈，仅供参考）。\n\n" % (total, sum(1 for _, r in items if r.get("approx"))))
    f.write("| # | 单词 | 美式音标 | 近似? | 首次出现页 |\n")
    f.write("|---|------|----------|------|------------|\n")
    for i, (key, r) in enumerate(items, 1):
        ipa = r["ipa"] or "—"
        ap = "≈" if r.get("approx") else ""
        f.write("| %d | %s | %s | %s | %d |\n" % (i, r["display"], ipa, ap, r["first_page"]))

print("total unique words:", total)
print("with IPA:", with_ipa, "(%.1f%%)" % (100 * with_ipa / total))
print("CSV ->", CSV)
print("MD  ->", MD)
