import os
from PIL import Image, ImageDraw, ImageFont

RES = os.path.join(os.path.dirname(__file__), "app", "src", "main", "res")
# (density dir, px size)
SIZES = [("mipmap-mdpi", 48), ("mipmap-hdpi", 72), ("mipmap-xhdpi", 96),
         ("mipmap-xxhdpi", 144), ("mipmap-xxxhdpi", 192)]

# 找中文字体
font_path = None
for p in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
          "C:/Windows/Fonts/simsun.ttc"]:
    if os.path.exists(p):
        font_path = p
        break

for d, size in SIZES:
    dstdir = os.path.join(RES, d)
    os.makedirs(dstdir, exist_ok=True)
    img = Image.new("RGBA", (size, size), (21, 101, 192, 255))  # #1565C0 蓝底
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, int(size * 0.62)) if font_path else ImageFont.load_default()
    t = "词"
    bb = d.textbbox((0, 0), t, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size - tw) / 2 - bb[0], (size - th) / 2 - bb[1]), t, font=font, fill=(255, 255, 255, 255))
    out = os.path.join(dstdir, "ic_launcher.png")
    img.save(out)
    print("生成", out, size, "px")
print("字体:", font_path)
