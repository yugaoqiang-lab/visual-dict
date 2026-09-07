# -*- coding: utf-8 -*-
"""Fill missing IPA in pages_meta.json using the locally-downloaded CMUdict
(cards-data/cmudict.dict). ARPABET -> General-American IPA (offline, no network).
"""
import os, re, json

OUT = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(OUT, "pages_meta.json")
CMU = os.path.join(OUT, "cards-data", "cmudict.dict")
CACHE = os.path.join(OUT, "cards-data", "ipa_api_cache.json")

# ARPABET vowel -> IPA base (unstressed)
VOWEL = {
    "AA": "ɑ", "AE": "æ", "AH": "ə", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ",
    "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
}
# CMU stressed AH is /ʌ/; stressed ER is /ɝ/
CONS = {
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "g",
    "HH": "h", "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n",
    "NG": "ŋ", "P": "p", "R": "r", "S": "s", "SH": "ʃ", "T": "t",
    "TH": "θ", "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}

def arpa_to_ipa(phons):
    out = []
    for p in phons:
        base = re.sub(r"\d$", "", p)
        stress = p[-1] if p[-1].isdigit() else ""
        if base in VOWEL:
            v = VOWEL[base]
            if base == "AH" and stress == "1":
                v = "ʌ"
            if base == "ER":
                v = "ɝ" if stress == "1" else ("ˌɝ" if stress == "2" else "ɚ")
            elif stress == "1":
                v = "ˈ" + v
            elif stress == "2":
                v = "ˌ" + v
            out.append(v)
        elif base in CONS:
            out.append(CONS[base])
        else:
            out.append(base.lower())
    s = "".join(out)
    # tidy: collapse a leading stress that landed before a consonant
    s = re.sub(r"([ˈˌ])(?=[^ɑæəɔaʊaɪɛɚeɪɪiʊuʌ])", "", s)
    return "/" + s + "/"

def load_cmu(path):
    d = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;;"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            w = parts[0].lower()
            w = re.sub(r"\(\d+\)$", "", w)  # drop (2) variant marker
            phons = parts[1:]
            if w not in d:
                d[w] = phons
    return d

def main():
    cmu = load_cmu(CMU)
    print("cmudict entries:", len(cmu))
    pages = json.load(open(META, encoding="utf-8"))
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))

    missing = []
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa"):
                missing.append(w["t"])
    print("missing word labels:", len(missing))

    filled = 0
    for t in missing:
        low = t.lower().strip()
        if " " in low:
            # multi-word phrase: only fill if EVERY token is known (full IPA);
            # otherwise keep any existing IPA (do not clear / do not show a
            # misleading single-token pronunciation).
            toks = low.split()
            if all(tk in cmu for tk in toks):
                ipas = [arpa_to_ipa(cmu[tk]).strip("/") for tk in toks]
                ipa = "/" + " ".join(ipas) + "/"
            else:
                continue  # leave w["ipa"] as-is
        else:
            ipa = arpa_to_ipa(cmu[low]).strip("/") if low in cmu else ""
            ipa = "/" + ipa + "/" if ipa else ""
        if ipa:
            cache[t] = ipa
            filled += 1

    # second pass: overwrite multi-word labels with full joined IPA when every
    # token is known (better than a misleading single-token pronunciation).
    mw_fixed = 0
    for p in pages:
        for w in p["words"]:
            low = w["t"].lower().strip()
            if " " in low:
                toks = low.split()
                if all(tk in cmu for tk in toks):
                    ipas = [arpa_to_ipa(cmu[tk]).strip("/") for tk in toks]
                    ipa = "/" + " ".join(ipas) + "/"
                    if ipa != w.get("ipa"):
                        w["ipa"] = ipa
                        cache[w["t"]] = ipa
                        mw_fixed += 1

    # patch meta
    before = sum(1 for p in pages for w in p["words"] if w.get("ipa"))
    total = sum(len(p["words"]) for p in pages)
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa") and w["t"] in cache and cache[w["t"]]:
                w["ipa"] = cache[w["t"]]
    after = sum(1 for p in pages for w in p["words"] if w.get("ipa"))

    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(pages, open(META, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"CMU filled: {filled} | multi-word overwritten: {mw_fixed}")
    print(f"IPA coverage: {before}/{total} -> {after}/{total} ({100*after/total:.1f}%)")
    print(f"still missing: {total - after}")

if __name__ == "__main__":
    main()
