import re, base64, os

base = r"C:\Users\Administrator\WorkBuddy\图解词典\visual-dict"
html_path = os.path.join(base, "index2.html")
out_path = os.path.join(base, "index2-standalone.html")

html = open(html_path, encoding="utf-8").read()

# 找出所有 pages 图片引用
refs = re.findall(r'pages/[\w\-]+\.jpg', html)
uniq = sorted(set(refs))
print("图片引用总数:", len(refs), "| 唯一:", len(uniq))

cache = {}
def repl(m):
    p = m.group(0)
    if p in cache:
        return cache[p]
    fp = os.path.join(base, p.replace("/", os.sep))
    if not os.path.exists(fp):
        fp = os.path.join(base, p)
    with open(fp, "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    uri = "data:image/jpeg;base64," + b
    cache[p] = uri
    return uri

new = re.sub(r'pages/[\w\-]+\.jpg', repl, html)
open(out_path, "w", encoding="utf-8").write(new)

# 自检：是否还有任何外部 http(s) 依赖
ext = re.findall(r'(?:src|href)="(https?://[^"]+)"', new)
print("残留外链 http(s) 引用:", len(ext))
print("输出文件大小(MB):", round(os.path.getsize(out_path) / 1024 / 1024, 1))
print("输出路径:", out_path)
