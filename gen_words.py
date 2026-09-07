import csv, json, re, os

ROOT = os.path.dirname(__file__)

# 1) 读美式音标 + 近似标记 + 出现页
ipa = {}
approx = {}
page = {}
with open(os.path.join(ROOT, "cards-data", "word_ipa_list.csv"), encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        en = (row.get("English") or "").strip()
        ip = (row.get("IPA(美式)") or "").strip()
        if not en:
            continue
        ipa[en] = ip
        approx[en] = 1 if (row.get("近似?") or "").strip() else 0
        pg = re.findall(r"\d+", row.get("出现页") or "")
        page[en] = int(pg[0]) if pg else 0

# 2) 读中文释义
zh = {}
try:
    d = json.load(open(os.path.join(ROOT, "cards-data", "dict.json"), encoding="utf-8"))
    for k, v in d.items():
        trans = v[1] if isinstance(v, list) and len(v) > 1 else ""
        m = re.findall(r"[一-鿿]+", trans or "")
        zh[k.lower()] = "".join(m)
except Exception as e:
    print("dict.json 读取失败:", e)

# 3) 合并 -> 紧凑数组 [英文, 音标, 近似(0/1), 中文, 出现页]
out = []
for en in ipa:
    out.append([en, ipa[en], approx[en], zh.get(en.lower(), ""), page[en]])

out.sort(key=lambda x: x[0])
js = "window.WORDS=" + json.dumps(out, ensure_ascii=False) + ";"
with open(os.path.join(ROOT, "words.js"), "w", encoding="utf-8") as f:
    f.write(js)

print("生成 words.js: 词条数 =", len(out))
print("含中文释义:", sum(1 for x in out if x[3]))
print("有出现页(可跳图):", sum(1 for x in out if x[4]))
print("近似音标数:", sum(1 for x in out if x[2]))
print("样例:", out[0])
