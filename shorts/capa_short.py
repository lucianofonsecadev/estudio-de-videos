"""Capa VERTICAL de Short (1080x1920) em camadas editáveis no PhotoCraft (.pcraft) + JPG para o YouTube.
Mesmo padrão da capa do vídeo longo (ferramentas/18): foto, texto branco em minúsculas (Bricolage), valor numa
pílula violeta. Aqui a foto fica em cima (rostos livres) e o texto embaixo, sobre o fundo tinta.
Uso: python -I ferramentas/shorts/capa_short.py <quadro.png> <x0,y0,larg,alt> <saida.pcraft> "linha 1|linha 2" "R$ 2.500" ["linha final"]
  x0,y0,larg,alt: recorte do quadro (de preferência mais alto que largo; vai para 1080 de largura no topo)."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = r"C:\Program Files\ArtCraft\PhotoCraft\photocraft-cli.exe"
FONTE = os.path.join(B, "fontes", "BricolageGrotesque[opsz,wdth,wght].ttf")
quadro, rec, saida, linhas, valor = sys.argv[1:6]; fim = sys.argv[6] if len(sys.argv) > 6 else ""
x0, y0, lw, lh = (int(v) for v in rec.split(","))
W, H, TINTA = 1080, 1920, (24, 18, 43)
pasta = os.path.dirname(os.path.abspath(saida)); nome = os.path.splitext(os.path.basename(saida))[0]
win = lambda p: os.path.abspath(p).replace("/", "\\")
if os.path.exists(saida): raise SystemExit(f"já existe: {saida} (não sobrescrevo)")

# 1) foto no topo, com fade para o fundo tinta
ph = int(W * lh / lw)
foto = Image.open(quadro).convert("RGB").crop((x0, y0, x0 + lw, y0 + lh)).resize((W, ph), Image.LANCZOS)
foto = ImageEnhance.Contrast(foto).enhance(1.12); foto = ImageEnhance.Color(foto).enhance(1.08)
foto = ImageEnhance.Sharpness(foto).enhance(1.4)
m = Image.new("L", (1, ph))
for y in range(ph): m.putpixel((0, y), 255 if y < ph - 380 else int(255 * (1 - (y - (ph - 380)) / 380) ** 1.3))
foto = foto.convert("RGBA"); foto.putalpha(m.resize((W, ph)))
camada_foto = Image.new("RGBA", (W, H), (0, 0, 0, 0)); camada_foto.alpha_composite(foto)
f_foto = os.path.join(pasta, f"{nome}-camada-foto.png"); camada_foto.save(f_foto)

def fonte(sz): f = ImageFont.truetype(FONTE, sz); f.set_variation_by_axes([96, 800, 100]); return f
cmds = []
def c(cid, **p): cmds.extend(["--cmd", cid, "--params", json.dumps(p, ensure_ascii=False)])
def sombra(): c("layer.layerStyle.dropShadow", color="#0B0614", opacity=75, angle=120, distance=5, size=10)

c("file.placeEmbedded", path=win(f_foto), scale=100, center=[W // 2, H // 2]); c("layer.setProps", name="Foto")

X, SZ = 70, 104
y = ph - 250
for ln in linhas.split("|"):
    SZ = 104
    while fonte(SZ).getlength(ln) > W - 2 * X and SZ > 60: SZ -= 4
    asc = fonte(SZ).getmetrics()[0]
    c("type.create", x=X, y=y + asc, text=ln, name=f"Texto: {ln}", font="Bricolage Grotesque", weight=800, size=SZ, color="#FFFFFF", tracking=-20)
    sombra(); y += int(SZ * 1.08)

# 2) pílula violeta com o valor (texto editável por cima)
VS = 170
while fonte(VS).getlength(valor) > W - 2 * X - 100 and VS > 60: VS -= 6   # texto longo: diminui até caber
fv = fonte(VS); bb = fv.getbbox(valor); px, py = 44, 28
pw, phh = (bb[2] - bb[0]) + 2 * px, (bb[3] - bb[1]) + 2 * py
bx, by = X - 8, y + 24
pil = Image.new("RGBA", (pw + 80, phh + 80), (0, 0, 0, 0))
somb = Image.new("RGBA", pil.size, (0, 0, 0, 0))
ImageDraw.Draw(somb).rounded_rectangle([40, 52, 40 + pw, 52 + phh], phh // 2, fill=(30, 10, 70, 170))
pil.alpha_composite(somb.filter(ImageFilter.GaussianBlur(14)))
grad = Image.new("RGBA", (pw, phh))
for x in range(pw):
    t = x / max(1, pw - 1); c1, c2, c3 = (139, 92, 246), (124, 58, 237), (109, 40, 217)
    col = tuple(int(c1[i] + (c2[i] - c1[i]) * t * 2) if t < .5 else int(c2[i] + (c3[i] - c2[i]) * (t - .5) * 2) for i in range(3))
    ImageDraw.Draw(grad).line([(x, 0), (x, phh)], fill=col + (255,))
mk = Image.new("L", (pw, phh), 0); ImageDraw.Draw(mk).rounded_rectangle([0, 0, pw - 1, phh - 1], phh // 2, fill=255)
grad.putalpha(mk); ImageDraw.Draw(grad).rounded_rectangle([1, 1, pw - 2, phh - 2], phh // 2 - 1, outline=(196, 170, 255, 255), width=4)
pil.alpha_composite(grad, (40, 40))
f_pil = os.path.join(pasta, f"{nome}-camada-pilula.png"); pil.save(f_pil)
c("file.placeEmbedded", path=win(f_pil), scale=100, center=[bx - 40 + pil.width / 2, by - 40 + pil.height / 2]); c("layer.setProps", name="Pílula violeta")
c("type.create", x=bx + px - bb[0], y=by + py - bb[1] + fv.getmetrics()[0], text=valor, name=f"Valor: {valor}",
  font="Bricolage Grotesque", weight=800, size=VS, color="#FFFFFF", tracking=-20)
y = by + phh + 20
if fim:
    asc = fonte(SZ).getmetrics()[0]
    c("type.create", x=X, y=y + asc, text=fim, name=f"Texto: {fim}", font="Bricolage Grotesque", weight=800, size=SZ, color="#FFFFFF", tracking=-20)
    sombra()
# selo do canal no pé
fs = ImageFont.truetype(FONTE, 52); fs.set_variation_by_axes([96, 800, 100])
c("type.create", x=X, y=H - 110, text="2 tá bom!", name="Selo: 2 tá bom!", font="Bricolage Grotesque", weight=800, size=52, color="#A78BFA", tracking=-10)

r = subprocess.run([CLI, "run", "--new", json.dumps({"width": W, "height": H, "background": "#18122B", "name": "Capa Short"}), *cmds,
                    "--cmd", "layer.list", "--out", win(saida)], capture_output=True, text=True, encoding="utf-8")
erros = [l for l in r.stdout.splitlines() if '"error"' in l or "refus" in l.lower()]
print("\n".join(erros) or "ok", r.stderr[-1500:])
png = os.path.splitext(saida)[0] + ".png"; jpg = os.path.splitext(saida)[0] + ".jpg"
subprocess.run([CLI, "convert", win(saida), win(png)], capture_output=True)
Image.open(png).convert("RGB").save(jpg, quality=90, optimize=True)   # o YouTube aceita até 2 MB
print("capa:", saida, "| prévia:", png, "| para o YouTube:", jpg, f"({os.path.getsize(jpg) / 1e6:.1f} MB)")
