# -*- coding: utf-8 -*-
import os, re, json, time, sys, urllib.request, urllib.parse
OUT=os.path.dirname(os.path.abspath(__file__))
META=os.path.join(OUT,"pages_meta.json"); CACHE=os.path.join(OUT,"ipa_api_cache.json")
API="https://api.dictionaryapi.dev/api/v2/entries/en/"
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BRIT=set("ɒəʊeəɛəɪəʊəɔːɜː")
TIMEOUT=12
def log(m): sys.stderr.write(m+"\n"); sys.stderr.flush()
def pick(data):
    if not isinstance(data,list): return ""
    txt=[]
    for e in data:
        if isinstance(e,dict):
            if e.get("phonetic"): txt.append(e["phonetic"])
            for ph in e.get("phonetics",[]) or []:
                if ph.get("text"): txt.append(ph["text"])
    c=[t for t in txt if t and not any(m in t for m in BRIT)]
    pool=c if c else [t for t in txt if t]
    for t in pool:
        s=t.strip().strip("/").strip().replace(".",""); s=re.sub(r"\s+","",s)
        if s: return "/"+s+"/"
    return ""
def fetch(w):
    for a in range(3):
        try:
            req=urllib.request.Request(API+urllib.parse.quote(w.lower()),headers=UA)
            with urllib.request.urlopen(req,timeout=TIMEOUT) as r:
                return "ok",pick(json.loads(r.read().decode()))
        except urllib.error.HTTPError as e:
            if e.code==429: time.sleep(1.5+a*1.5); continue
            if e.code==404: return "ok",""
            time.sleep(1.0)
        except Exception: time.sleep(1.0)
    return "fail",""
def main():
    pages=json.load(open(META,encoding="utf-8"))
    cache={}
    if os.path.exists(CACHE): cache=json.load(open(CACHE,encoding="utf-8"))
    missing=set()
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa"): missing.add(w["t"])
    todo=[t for t in missing if t not in cache]
    limit=int(os.environ.get("LIMIT","0"))
    if limit: todo=todo[:limit]
    log("todo=%d"%len(todo))
    done=filled=0
    for t in todo:
        st,ipa=fetch(t)
        if st=="ok":
            cache[t]=ipa
            if ipa: filled+=1
        done+=1
        if done%50==0:
            json.dump(cache,open(CACHE,"w",encoding="utf-8"),ensure_ascii=False)
            log("progress %d/%d filled %d"%(done,len(todo),filled))
    json.dump(cache,open(CACHE,"w",encoding="utf-8"),ensure_ascii=False)
    before=sum(1 for p in pages for w in p["words"] if w.get("ipa"))
    total=sum(len(p["words"]) for p in pages)
    for p in pages:
        for w in p["words"]:
            if not w.get("ipa") and w["t"] in cache and cache[w["t"]]: w["ipa"]=cache[w["t"]]
    after=sum(1 for p in pages for w in p["words"] if w.get("ipa"))
    json.dump(pages,open(META,"w",encoding="utf-8"),ensure_ascii=False)
    log("coverage %d/%d -> %d/%d (%.1f%%)"%(before,total,after,total,100*after/total))
    log("new=%d still=%d"%(after-before,total-after))
main()
