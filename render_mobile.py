import fitz, os, shutil

PDF = r"C:\Users\Administrator\Desktop\Chinese-English Bilingual Visual Dictionary.pdf"
OUT = r"C:\Users\Administrator\WorkBuddy\图解词典\visual-dict\pages_mob"
ZOOM = 1.4
QUALITY = 72

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

doc = fitz.open(PDF)
mat = fitz.Matrix(ZOOM, ZOOM)
for p in range(13, 326):           # 内容页 13–325（共 313 页）
    pix = doc[p - 1].get_pixmap(matrix=mat)
    pix.save(os.path.join(OUT, f"page_{p:03d}.jpg"), jpg_quality=QUALITY)
doc.close()

sz = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024 / 1024
print(f"rendered {len(os.listdir(OUT))} pages | zoom={ZOOM} q{QUALITY} | 总大小 {sz:.1f}MB")
