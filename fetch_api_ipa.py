# -*- coding: utf-8 -*-
"""Fetch authoritative American IPA from dictionaryapi.dev for words that
currently lack an IPA in pages_meta.json, then patch pages_meta.json.

Concurrent (thread pool) + incremental save + resumable.
Network failures are NOT cached (so a resumed run retries them); only real
404 (no entry) is cached as empty.
Selection rule: among the phonetics the API returns, pick the one whose text
contains NO British-only symbols (ɒ əʊ eə ɛə ɪə ʊə ɔː ɜː). That yields the
General-American transcription. Results are cached in ipa_api_cache.json.
"""
import os, re, json, time, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(OUT, "pages_meta.json")
CACHE = os.path.join(OUT, "ipa_api_cache.json")
API = "https://api.dictionaryapi.dev/api/v2/entries/en/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BRIT = set("ɒəʊeəɛəɪəʊəɔːɜː")  # British-only IPA markers
WORKERS = 6
SAVE_EVERY = 50
TIMEOUT = 12

def log(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()

def pick_ipa(data):
    if not isinstance(data, list):
        return ""
    texts = []
    for e in data:
        if isinstance(e, dict):
            if e.get("phonetic"):
                texts.append(e["phonetic"])
            for ph in e.get("phonetics", []) or []:
                if ph.get("text"):
                    texts.append(ph["text"])
    cands = [t for t in texts if t and not any(m in t for m in BRIT)]
    pool = cands if cands else [t for t in texts if t]
    for t in pool:
        s = t.strip().strip("/").strip()
        s = s.replace(".", "")
        s = re.sub(r"\s+", "", s)
        if s:
            return "/" + s + "/"
    return ""

def fetch(word):
    """Return ('ok', ipa_or_empty) or ('fail', '') ."""
    url = API + urllib.parse.quote(word.lower())
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return "ok", pick_ipa(json.loads(r.read().decode()))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5 + attempt * 1.5)
                continue
            if e.code == 404:
                return "ok", ""          # genuinely no entry
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
    return "fail", ""

def main():
    pages = json.load(open(META, encoding="utf-8"))
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))

    missing = set()
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa"):
                missing.add(w["t"])
    todo = [t for t in missing if t not in cache]   # resume: skip cached
    limit = int(os.environ.get("LIMIT", "0"))
    if limit:
        todo = todo[:limit]
    log(f"missing unique words: {len(missing)} | need to fetch: {len(todo)}")

    done = 0
    filled = 0

    def handle(t):
        st, ipa = fetch(t)
        return t, st, ipa

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(handle, t): t for t in todo}
        for fut in as_completed(futs):
            t, st, ipa = fut.result()
            if st == "ok":
                cache[t] = ipa
                if ipa:
                    filled += 1
            done += 1
            if done % SAVE_EVERY == 0:
                json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
                log(f"  progress {done}/{len(todo)}  filled {filled}")

    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    log("cache saved.")

    before = sum(1 for p in pages for w in p["words"] if w.get("ipa"))
    total = sum(len(p["words"]) for p in pages)
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa") and w["t"] in cache and cache[w["t"]]:
                w["ipa"] = cache[w["t"]]
    after = sum(1 for p in pages for w in p["words"] if w.get("ipa"))
    json.dump(pages, open(META, "w", encoding="utf-8"), ensure_ascii=False)
    log(f"IPA coverage: {before}/{total} -> {after}/{total} ({100*after/total:.1f}%)")
    log(f"newly filled: {after - before}; still missing: {total - after}")

if __name__ == "__main__":
    main()
