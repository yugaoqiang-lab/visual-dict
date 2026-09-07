import os, shutil
from PIL import Image

SRC = r"C:\Users\Administrator\WorkBuddy\图解词典\visual-dict\pages"
OUT = r"C:\Users\Administrator\WorkBuddy\图解词典\visual-dict\pages_mob"
MAX_W = 1200
QUALITY = 70

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

files = sorted(f for f in os.listdir(SRC) if f.endswith(".jpg"))
for f in files:
    im = Image.open(os.path.join(SRC, f)).convert("RGB")
    if im.width > MAX_W:
        h = round(im.height * MAX_W / im.width)
        im = im.resize((MAX_W, h), Image.LANCZOS)
    im.save(os.path.join(OUT, f), "JPEG", quality=QUALITY, optimize=True)

sz = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024 / 1024
print(f"重压完成 {len(files)} 张 | 宽<= {MAX_W}px q{QUALITY} | 总大小 {sz:.1f}MB")
