# -*- coding: utf-8 -*-
"""把 cards-data/cards.json + dict.json 注入 template.html -> index.html"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(HERE, "cards-data", "cards.json")
DICT = os.path.join(HERE, "cards-data", "dict.json")
TPL = os.path.join(HERE, "template.html")
OUT = os.path.join(HERE, "index.html")

with open(CARDS, encoding="utf-8") as f:
    cards = json.load(f)
with open(DICT, encoding="utf-8") as f:
    dic = json.load(f)

cards_js = json.dumps(cards, ensure_ascii=False).replace('</', '<\\/')
dict_js = json.dumps(dic, ensure_ascii=False).replace('</', '<\\/')

with open(TPL, encoding="utf-8") as f:
    tpl = f.read()

# 适配为「图解词典单词卡」标题
tpl = tpl.replace("<title>单词例句闪卡</title>", "<title>视觉词典单词卡</title>")
tpl = tpl.replace('<span class="title">📇 例句闪卡</span>',
                  '<span class="title">📇 图解词典</span>')

html = tpl.replace("__CARDS_JSON__", cards_js).replace("__DICT_JSON__", dict_js)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("index.html size(KB):", round(os.path.getsize(OUT) / 1024, 1))
print("cards:", len(cards), "dict entries:", len(dic))
