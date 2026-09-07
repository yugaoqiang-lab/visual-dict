import urllib.request, sys
sys.stderr.write("start\n"); sys.stderr.flush()
try:
    r = urllib.request.urlopen(
        urllib.request.Request('https://api.dictionaryapi.dev/api/v2/entries/en/bottle',
                               headers={'User-Agent': 'Mozilla/5.0'}), timeout=10)
    data = r.read()
    sys.stderr.write("OK bytes=%d\n" % len(data)); sys.stderr.flush()
except Exception as e:
    sys.stderr.write("ERR %s %s\n" % (type(e).__name__, str(e)[:80])); sys.stderr.flush()
