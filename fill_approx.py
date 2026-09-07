# -*- coding: utf-8 -*-
"""把缺失音标的词用离线 G2P 补成「近似音标」，写入 pages_meta.json。
对已有音标的词标记 approx=False；新补的标记 approx=True。
"""
import os, json
import g2p

OUT = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(OUT, "pages_meta.json")

pages = json.load(open(META, encoding="utf-8"))

filled = 0
for p in pages:
    for w in p["words"]:
        if w.get("ipa"):
            w["approx"] = False
        else:
            ipa, ap = g2p.resolve(w["t"])
            if ipa:
                w["ipa"] = ipa
                w["approx"] = ap
                filled += 1
            else:
                w["approx"] = True

json.dump(pages, open(META, "w", encoding="utf-8"), ensure_ascii=False)

total = sum(len(p["words"]) for p in pages)
with_ipa = sum(1 for p in pages for w in p["words"] if w.get("ipa"))
approx_cnt = sum(1 for p in pages for w in p["words"] if w.get("ipa") and w.get("approx"))
print("filled (new approximate):", filled)
print("total words:", total, "| with ipa:", with_ipa, f"({100*with_ipa/total:.1f}%)")
print("of which approx (rule-derived):", approx_cnt)
