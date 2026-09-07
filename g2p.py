# -*- coding: utf-8 -*-
"""离线 G2P：英文单词 -> 美式 IPA（近似）。
策略：
  1) CMU 形态拆解：按 空格/连字符/撇号 切分，能查到 CMU 的词段直接用 CMU 美式音标；
  2) 查不到的词段用规则式 G2P 推算。
返回 (ipa_str, is_approx)：只要有一段是规则推算，整体标记 approx=True。
"""
import os, re, json

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------- CMU 加载 ----------
cmu = {}
with open(os.path.join(OUT, "cards-data", "cmudict.dict"), encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith(";;;"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        w = parts[0].lower()
        w = re.sub(r"\(\d+\)$", "", w)
        if w not in cmu:
            cmu[w] = parts[1:]

VOWEL = {"AA": "ɑ", "AE": "æ", "AH": "ə", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
         "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "IH": "ɪ", "IY": "i",
         "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ", "UW": "u"}
CONS = {"B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "g", "HH": "h",
        "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
        "R": "r", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w",
        "Y": "j", "Z": "z", "ZH": "ʒ"}


def arpa(p):
    base = re.sub(r"\d$", "", p)
    st = p[-1] if p[-1].isdigit() else ""
    if base in VOWEL:
        v = VOWEL[base]
        if base == "AH" and st == "1":
            v = "ʌ"
        if base == "ER":
            v = "ɝ" if st == "1" else ("ˌɝ" if st == "2" else "ɚ")
        elif st == "1":
            v = "ˈ" + v
        elif st == "2":
            v = "ˌ" + v
        return v
    return CONS.get(base, base.lower())


def conv(ph):
    return "".join(arpa(x) for x in ph)


def cmu_ipa(token):
    """返回该 token 的 CMU 美式音标字符串（不含斜杠），查不到返回 None。"""
    t = token.lower().strip()
    if not t:
        return None
    if t in cmu:
        return conv(cmu[t]).strip("/")
    # 尝试去词尾 s/es/ing/ed 再查
    for suf in ("ies", "es", "s", "ied", "ed", "ing"):
        if t.endswith(suf) and len(t) > len(suf) + 1:
            stem = t[: -len(suf)]
            if stem in cmu:
                return conv(cmu[stem]).strip("/")
    return None


# ---------- 规则式 G2P ----------
def g2p(word):
    w = word.lower().strip()
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return ""
    # 处理词尾不发音 e
    silent_e = False
    if len(w) > 3 and w.endswith("e") and w[-2] not in "aeiou" and w[-2:] != "le":
        w = w[:-1]
        silent_e = True
    out = []
    L = len(w)
    VOW = set("aeiouy")
    i = 0
    while i < L:
        c = w[i]
        c2 = w[i:i + 2]
        c3 = w[i:i + 3]
        nxt = w[i + 1] if i + 1 < L else ""
        nxt2 = w[i + 2] if i + 2 < L else ""
        end = (i + 1 == L)
        # ---- 辅音簇/破擦/擦音 ----
        if c2 == "gh":
            out.append(""); i += 2; continue   # gh 通常不发音（bobsleigh/high）
        if c2 == "th":
            out.append("θ"); i += 2; continue
        if c2 == "ph":
            out.append("f"); i += 2; continue
        if c2 == "sh":
            out.append("ʃ"); i += 2; continue
        if c2 == "ch":
            out.append("tʃ"); i += 2; continue
        if c2 == "wh":
            out.append("w"); i += 2; continue
        if c2 == "qu":
            out.append("kw"); i += 2; continue
        if c2 == "ck":
            out.append("k"); i += 2; continue
        if c3 == "tch":
            out.append("tʃ"); i += 3; continue
        if c3 == "dge":
            out.append("dʒ"); i += 3; continue
        if c2 == "ng":
            out.append("ŋ"); i += 2; continue
        # ---- 元音字母组合 ----
        if c3 == "ough":
            out.append("ʌf"); i += 3; continue
        if c3 == "augh":
            out.append("ɔ"); i += 3; continue
        if c2 in ("ai", "ay"):
            out.append("eɪ"); i += 2; continue
        if c2 in ("ei", "ey"):
            out.append("eɪ"); i += 2; continue
        if c2 in ("oa", "oe"):
            out.append("oʊ"); i += 2; continue
        if c2 in ("au", "aw"):
            out.append("ɔ"); i += 2; continue
        if c2 == "oo":
            out.append("ʊ" if nxt in "kld" else "u"); i += 2; continue
        if c2 == "ou":
            out.append("aʊ"); i += 2; continue
        if c2 == "ow":
            out.append("aʊ" if nxt in VOW or end else "oʊ"); i += 2; continue
        if c3 == "igh":
            out.append("aɪ"); i += 3; continue
        if c3 == "eigh":
            out.append("eɪ"); i += 3; continue
        if c2 == "ee":
            out.append("i"); i += 2; continue
        if c2 == "ea":
            out.append("i"); i += 2; continue
        if c2 == "ie":
            out.append("i" if nxt != "" else "aɪ"); i += 2; continue
        if c2 == "ui":
            out.append("u"); i += 2; continue
        # ---- 单元音 ----
        if c == "a":
            if end and silent_e:
                out.append("eɪ")
            elif nxt == "r":
                out.append("ɑr")
            elif nxt == "l" and nxt2 not in VOW:
                out.append("ɔl")
            elif nxt == "y" and i + 2 == L:
                out.append("eɪ")   # day/play/way
            else:
                out.append("æ")
            i += 1; continue
        if c == "e":
            if end and silent_e:
                out.append("i")
            elif nxt == "r":
                out.append("ɛr")
            else:
                out.append("ɛ")
            i += 1; continue
        if c == "i":
            if end and silent_e:
                out.append("aɪ")
            elif nxt == "r":
                out.append("ɝ")
            else:
                out.append("ɪ")
            i += 1; continue
        if c == "o":
            if end and silent_e:
                out.append("oʊ")
            elif nxt == "r":
                out.append("ɔr")
            else:
                out.append("ɑ")
            i += 1; continue
        if c == "u":
            if end and silent_e:
                out.append("u")
            elif nxt == "r":
                out.append("ɝ")
            else:
                out.append("ʌ")
            i += 1; continue
        if c == "y":
            if i == 0:
                out.append("j")
            elif end:
                out.append("aɪ")
            else:
                out.append("ɪ")
            i += 1; continue
        # ---- 辅音 ----
        if c == "c":
            out.append("s" if nxt in "eiy" else "k"); i += 1; continue
        if c == "g":
            out.append("dʒ" if (nxt in "eiy") else "ɡ"); i += 1; continue
        if c == "x":
            out.append("ks"); i += 1; continue
        if c == "j":
            out.append("dʒ"); i += 1; continue
        out.append(c); i += 1; continue
    return "".join(out)


def resolve(word):
    """返回 (ipa_with_slashes, is_approx)。"""
    toks = [t for t in re.split(r"[\s\-’']+", word.lower()) if t]
    if not toks:
        return "", True
    segs = []
    all_cmu = True
    for t in toks:
        c = cmu_ipa(t)
        if c:
            segs.append(c)
        else:
            g = g2p(t)
            if g:
                segs.append(g)
            all_cmu = False
    if not segs:
        g = g2p(word)
        return ("/" + g + "/" if g else ""), True
    return "/" + " ".join(segs) + "/", (not all_cmu)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for w in sys.argv[1:]:
            print(w, "->", resolve(w))
    else:
        # 预览所有缺失词
        pages = json.load(open(os.path.join(OUT, "pages_meta.json"), encoding="utf-8"))
        seen = {}
        for p in pages:
            for w in p["words"]:
                if not w.get("ipa"):
                    seen.setdefault(w["t"].lower(), w["t"])
        items = sorted(seen.values())
        for t in items:
            ipa, ap = resolve(t)
            print(f"{t:<26} {ipa:<22} {'≈' if ap else ''}")
