import os, random
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exports", "trim_atlas.png")
W, H = 1024, 2048
img = Image.new("RGB", (W, H), (198, 198, 195))
d = ImageDraw.Draw(img)
rnd = random.Random(5)
for i in range(4):
    y = 64 + i * 128
    d.rectangle([0, y, W, y + 4], fill=(88, 90, 92))
    d.rectangle([0, y + 6, W, y + 9], fill=(226, 227, 223))
for x in range(0, W, 160):
    d.rectangle([x, 0, x + 3, 512], fill=(92, 94, 96))
    for yy in range(30, 500, 60):
        d.ellipse([x - 9, yy - 4, x + 1, yy + 4], fill=(152, 154, 152))
d.rectangle([0, 512, W, 1024], fill=(58, 60, 62))
for i in range(0, W, 32):
    d.rectangle([i, 520, i + 18, 1016], fill=(114, 117, 120))
d.rectangle([0, 1024, W, 1536], fill=(206, 158, 26))
for i in range(-H, W, 96):
    d.polygon([(i, 1536), (i + 48, 1536), (i + 48 + 320, 1024), (i + 320, 1024)], fill=(38, 38, 40))
d.rectangle([0, 1536, W, 2048], fill=(196, 198, 196))
try:
    f = ImageFont.truetype("arialbd.ttf", 110)
except Exception:
    f = ImageFont.load_default()
for i, t in enumerate(["HAB-01", "DOCK-3", "MTX-2", "O2"]):
    d.text((50 + (i % 2) * 520, 1600 + (i // 2) * 210), t, fill=(50, 52, 54), font=f)
for _ in range(6000):
    x, y = rnd.randrange(W), rnd.randrange(H)
    r, g, b = img.getpixel((x, y))
    k = rnd.randrange(-12, 12)
    img.putpixel((x, y), (max(0, min(255, r + k)),) * 3)
img.save(OUT)
print("TRIM", OUT, os.path.getsize(OUT))
