"""Compõe o Short final (1080x1920) no visual do 2 tá bom! (identidade Lulu).
Uso: python -I render.py <pasta_de_trabalho> <nome>     (lê <pasta>/<nome>.json, <nome>/base.mov e <nome>/palavras.json)
Camadas: faixa de título (fundo tinta, valor numa pílula violeta, @2tabom discreto), apresentador, cartões no peito
(nunca no rosto: começa abaixo do queixo, y >= 1060), legenda que vai ficando violeta conforme a fala, barra de progresso violeta embaixo, música baixinha.
Eventos no json:
  {"tipo":"faixa","t":[a,b],"l1":"peguei R$ 4 mil","l2":"e hoje devo R$ 48 mil"}
  {"tipo":"numero","t":[a,b],"linhas":[["peguei","R$ 4 mil",""],["hoje cobram","R$ 48 mil","r"]],"aceso":2?}
       cor do valor: "" tinta, "r" gasto/dívida (framboesa), "g" entrada/acordo (verde), "v" violeta
  {"tipo":"palavra","t":[a,b],"txt":"12x maior"}
"corrigir": [["texto errado do whisper","texto certo"]], "musica": arquivo em biblioteca/musica."""
import json, os, re, subprocess, sys, unicodedata
from PIL import Image, ImageDraw, ImageFont, ImageFilter

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # raiz do repositório
FONTES = os.path.join(P, "fontes")
BRIC, MANR = os.path.join(FONTES, "BricolageGrotesque[opsz,wdth,wght].ttf"), os.path.join(FONTES, "Manrope[wght].ttf")
VIOLETA, VIO_FORTE, VIO_SUAVE, LINHA = (124, 58, 237), (109, 40, 217), (239, 233, 255), (219, 208, 246)
TINTA, TINTA2, BRANCO, GASTO, ENTRADA = (24, 18, 43), (95, 87, 121), (255, 255, 255), (200, 30, 74), (11, 122, 83)
W, H, BAND = 1080, 1920, 260

Wd, nome = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(Wd, f"{nome}.json"), encoding="utf-8"))
pasta = os.path.join(Wd, nome); png = os.path.join(pasta, "png"); os.makedirs(png, exist_ok=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join(pasta, "base.mov")], capture_output=True, text=True).stdout)

def fonte(arq, tam, peso=800):
    f = ImageFont.truetype(arq, tam)
    try: f.set_variation_by_axes([96, peso, 100] if arq == BRIC else [peso])
    except Exception: pass
    return f
def caber(txt, arq, tam, larg, peso=800):
    while fonte(arq, tam, peso).getlength(txt) > larg and tam > 20: tam -= 2
    return fonte(arq, tam, peso)
def grad(w, h):
    g = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(g)
    for x in range(w):
        t = x / max(1, w - 1); a, b = ((139, 92, 246), VIOLETA) if t < .5 else (VIOLETA, VIO_FORTE); u = (t * 2) % 1 if t < .5 else (t - .5) * 2
        d.line([(x, 0), (x, h)], fill=tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)) + (255,))
    return g
def arredondar(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    a = im.split()[3] if im.mode == "RGBA" else m
    im = im.convert("RGBA"); im.putalpha(Image.composite(a, Image.new("L", im.size, 0), m)); return im
def sombra(img, raio=22, op=150):
    a = img.split()[3].filter(ImageFilter.GaussianBlur(raio)).point(lambda v: v * op // 255)
    s = Image.new("RGBA", img.size, (40, 14, 90, 0)); s.putalpha(a); return s
def tela(elem, cx, cy):
    pad = 50; base = Image.new("RGBA", (elem.width + 2 * pad, elem.height + 2 * pad), (0, 0, 0, 0)); base.alpha_composite(elem, (pad, pad))
    t = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pos = (int(cx - base.width / 2), int(cy - base.height / 2))
    t.alpha_composite(sombra(base), (pos[0] + 6, pos[1] + 14)); t.alpha_composite(base, pos); return t
def pilula(txt, tam, larg_max=960):
    f = caber(txt, BRIC, tam, larg_max - 80); bb = f.getbbox(txt); px, py = 36, 20
    w, h = bb[2] - bb[0] + 2 * px, bb[3] - bb[1] + 2 * py
    c = arredondar(grad(w, h), h // 2); d = ImageDraw.Draw(c)
    d.rounded_rectangle([1, 1, w - 2, h - 2], h // 2 - 1, outline=(196, 170, 255, 255), width=3)
    d.text((px - bb[0], py - bb[1]), txt, font=f, fill=BRANCO); return c

def faixa(l1, l2):
    t = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
    d.rectangle([0, 0, W, BAND], fill=TINTA + (255,))
    d.rectangle([0, BAND - 5, W, BAND], fill=VIOLETA + (255,))
    f1 = caber(l1, BRIC, 70, 980); d.text((W / 2, 74), l1, font=f1, fill=BRANCO, anchor="mm")
    p = pilula(l2, 74); t.alpha_composite(p, (int(W / 2 - p.width / 2), 122))
    return t
def selo():
    t = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
    d.text((W - 30, BAND + 28), "@2tabom", font=fonte(MANR, 30, 700), fill=(255, 255, 255, 185), anchor="rm"); return t
def cartao_numero(linhas, aceso=None):
    """Faixa baixa e fina com os valores LADO A LADO (rótulo pequeno em cima, valor embaixo).
    Fica no pé do vídeo (y ~1660–1830), longe do rosto e da boca (pedido do usuário em 06/11/2026)."""
    aceso = len(linhas) if aceso is None else aceso
    n = len(linhas); col = 300 if n >= 3 else 360; lw, alt = col * n + 40, 150
    c = Image.new("RGBA", (lw, alt), BRANCO + (255,)); c = arredondar(c, 30); d = ImageDraw.Draw(c)
    d.rounded_rectangle([1, 1, lw - 2, alt - 2], 29, outline=LINHA, width=3)
    for i, ln in enumerate(linhas):
        rot, val, cor = (list(ln) + [""])[:3]; on = i < aceso; cx = 20 + col * i + col // 2
        if i: d.line([(20 + col * i, 30), (20 + col * i, alt - 30)], fill=LINHA, width=2)
        d.text((cx, 42), rot, font=caber(rot, MANR, 26, col - 30, 700), fill=TINTA2 if on else (215, 210, 228), anchor="mm")
        cv = {"r": GASTO, "g": ENTRADA, "v": VIOLETA}.get(cor, TINTA)
        d.text((cx, 98), val, font=caber(val, BRIC, 58, col - 30), fill=cv if on else (228, 224, 240), anchor="mm")
    return c

camadas = []
for i, ev in enumerate(cfg["eventos"]):
    a, b = ev["t"]; b = min(b, dur); k = ev["tipo"]
    if k == "faixa": img = faixa(ev["l1"], ev["l2"])
    elif k == "palavra": img = tela(pilula(ev["txt"], ev.get("tam", 60)), W / 2, ev.get("y", 1750))
    elif k == "numero": img = tela(cartao_numero(ev["linhas"], ev.get("aceso")), W / 2, ev.get("y", 1745))
    else: raise SystemExit(f"tipo desconhecido: {k}")
    arq = os.path.join(png, f"e{i:02d}.png"); img.save(arq); camadas.append((arq, a, b))
arq = os.path.join(png, "selo.png"); selo().save(arq); camadas.append((arq, 0, dur))

# ---------- legenda (ASS): branca, a palavra falada fica violeta, contorno escuro ----------
pal = json.load(open(os.path.join(pasta, "palavras.json"), encoding="utf-8"))
norm = lambda s: re.sub(r"[^\w]", "", unicodedata.normalize("NFC", s.lower()))
for velho, novo in cfg.get("corrigir", []):
    v = velho.split(); i = 0
    while i <= len(pal) - len(v):
        if [norm(p["w"]) for p in pal[i:i + len(v)]] == [norm(x) for x in v]:
            fim_pont = re.sub(r"^.*?([^\w]*)$", r"\1", pal[i + len(v) - 1]["w"])
            a, b = pal[i]["a"], pal[i + len(v) - 1]["b"]; nv = novo.split(); passo = (b - a) / len(nv)
            pal[i:i + len(v)] = [{"w": w + (fim_pont if j == len(nv) - 1 else ""), "a": a + j * passo, "b": a + (j + 1) * passo} for j, w in enumerate(nv)]
            i += len(nv)
        else: i += 1
# números que o Whisper parte em dois: "R" + "$120" -> "R$ 120"; "3" + ".800" -> "3.800"
i = 0
while i < len(pal) - 1:
    a, b = pal[i]["w"], pal[i + 1]["w"]
    if a == "R" and b.startswith("$"):
        pal[i:i + 2] = [{"w": "R$", "a": pal[i]["a"], "b": pal[i]["b"]}, {"w": b[1:], "a": pal[i + 1]["a"], "b": pal[i + 1]["b"]}] if b[1:] else [{"w": "R$", "a": pal[i]["a"], "b": pal[i + 1]["b"]}]
        continue
    if re.fullmatch(r"\$?\d+", a) and re.fullmatch(r"\.\d{3}[.,?!]?", b):
        pal[i:i + 2] = [{"w": a + b, "a": pal[i]["a"], "b": pal[i + 1]["b"]}]; continue
    i += 1
pal = [p for p in pal if p["a"] < dur]
blocos, atual = [], []
for p in pal:
    # blocos curtos: até 3 palavras e ~16 letras, para nunca passar da largura da tela
    if atual and (len(atual) >= 3 or len(" ".join(x["w"] for x in atual + [p])) > 16
                  or p["a"] - atual[-1]["b"] > 0.35 or re.search(r"[.,?!]$", atual[-1]["w"])):
        blocos.append(atual); atual = []
    atual.append(p)
if atual: blocos.append(atual)
NOMES = {"r$": "R$", "luciene": "Luciene", "luciano": "Luciano", "kombi": "Kombi", "brasil": "Brasil",
         "inglaterra": "Inglaterra", "londres": "Londres", "lulu": "Lulu", "deus": "Deus", "noah": "Noah"}
def minusc(w):   # legenda em minúsculas, menos R$ e nomes próprios
    m = re.match(r"^([^\w$]*)(.*?)([^\w$]*)$", w.lower()); return m.group(1) + NOMES.get(m.group(2), m.group(2)) + m.group(3)
ts = lambda t: f"{int(max(t,0) // 3600)}:{int(max(t,0) % 3600 // 60):02d}:{max(t,0) % 60:05.2f}"
ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "", "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
       "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       # Primary = violeta claro (já falada), Secondary = branco (ainda não), contorno tinta. Cores em &HBBGGRR
       # legenda no peito (base em y=1500), acima da faixa de valores do pé; margens de 90 px dos lados
       "Style: Leg,Bricolage Grotesque,80,&H00FA8BA7,&H00FFFFFF,&H002B1218,&H96000000,0,0,0,0,100,100,0,0,1,7,3,2,90,90,420,1",
       "Style: LegBaixa,Bricolage Grotesque,80,&H00FA8BA7,&H00FFFFFF,&H002B1218,&H96000000,0,0,0,0,100,100,0,0,1,7,3,2,90,90,420,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
peito = [tuple(ev["t"]) for ev in cfg["eventos"] if ev["tipo"] in ("numero", "palavra")]
for j, bl in enumerate(blocos):
    a = bl[0]["a"]; b = blocos[j + 1][0]["a"] if j + 1 < len(blocos) else min(bl[-1]["b"] + 0.4, dur); b = min(b, bl[-1]["b"] + 0.6)
    txt, t0 = "", a
    for p in bl:
        k = max(int(round((p["a"] - t0) * 100)), 0); txt += ("{\\k%d}" % k if k else "") + minusc(p["w"]).rstrip(",") + " "; t0 = p["a"]
    estilo = "LegBaixa" if any(a < pb and b > pa for pa, pb in peito) else "Leg"
    ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},{estilo},,0,0,0,,{txt.strip()}")
open(os.path.join(pasta, "legenda.ass"), "w", encoding="utf-8").write("\n".join(ass))

# ---------- ffmpeg ----------
mus = os.path.join(P, "biblioteca", "musica", cfg.get("musica", "No Rush - Dyalla.mp3"))
if not os.path.exists(mus): mus = None   # sem música na pasta biblioteca/musica: vai só a voz
ins = ["-i", os.path.join(pasta, "base.mov")] + (["-stream_loop", "-1", "-i", mus] if mus else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
for arq, a, b in camadas: ins += ["-loop", "1", "-framerate", "30000/1001", "-t", f"{dur:.3f}", "-i", arq]
n = len(camadas)
fc = [f"color=c=0x18122B:s={W}x{H}:r=30000/1001:d={dur:.3f}[bg]", f"[bg][0:v]overlay=0:{BAND}[v0]"]
ult = "v0"
for i, (arq, a, b) in enumerate(camadas):
    fc.append(f"[{ult}][{i + 2}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]"); ult = f"v{i + 1}"
fc.append(f"color=c=0x7C3AED:s={W}x10:r=30000/1001:d={dur:.3f}[barra]")
fc.append(f"[{ult}][barra]overlay=x='-{W}+{W}*t/{dur:.3f}':y={H - 10}[vb]")
ass_path = os.path.join(pasta, "legenda.ass").replace("\\", "/").replace(":", "\\:")
fontes_dir = FONTES.replace("\\", "/").replace(":", "\\:")
fc.append(f"[vb]ass='{ass_path}':fontsdir='{fontes_dir}',format=yuv420p[vout]")
fc.append("[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[voz]")
fc.append(f"[1:a]volume=-26dB,afade=t=out:st={dur - 1.5:.3f}:d=1.5[mus]")
fc.append("[voz][mus]amix=inputs=2:duration=first:normalize=0[aout]")
out = os.path.join(pasta, f"{nome}.mp4")
filtro = os.path.join(pasta, "filtro.txt"); open(filtro, "w", encoding="utf-8").write(";".join(fc))
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", filtro, "-map", "[vout]", "-map", "[aout]",
                "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-profile:v", "high",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], check=True)
print("ok", out, f"{dur:.1f}s", n, "camadas,", len(blocos), "blocos de legenda")
