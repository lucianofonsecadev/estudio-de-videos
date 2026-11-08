"""Monta o vídeo base vertical de um Short (área do apresentador 1080x1660, 29,97 fps) a partir do bruto 4K.
Uso: python -I base.py <pasta_de_trabalho> <nome>      (lê <pasta>/cortes.json, grava <pasta>/<nome>/base.mov)
Enquadramento: rosto a ~28% da altura, centrado; cor parecida com o grade do vídeo longo (Lumetri)."""
import json, os, subprocess, sys

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # raiz do repositório
BRUTO = os.path.join(P, "bruto")
W, nome = os.path.abspath(sys.argv[1]), sys.argv[2]
pecas = json.load(open(os.path.join(W, "cortes.json"), encoding="utf-8"))[nome]
pasta = os.path.join(W, nome); os.makedirs(pasta, exist_ok=True)

# centro do rosto no quadro 4K de cada bruto (medido nos quadros) e o zoom do recorte
# (cx, cy, largura, altura, zoom) — "bruto" no cortes.json pode ser o nome em bruto/ ou um caminho completo
# exemplos reais do canal; cadastre aqui o centro do rosto de cada vídeo seu
ROSTO = {"20261105_165400.mp4": (2150, 760, 3840, 2160, 1.25),
         "situação criadores de conteudo 2026.mp4": (1090, 390, 1920, 1080, 1.0),   # 1080p: sem zoom (já amplia 1,5x)
         # casal lado a lado: modo LARGO (6º valor = largura do recorte) — o quadro aberto fica no alto, com o mesmo
         # vídeo desfocado preenchendo atrás; a legenda e os cartões caem no desfoque, longe dos rostos
         "nosso patrimonio total.mp4": (880, 380, 1920, 1080, 1.0, 1240)}
LARGO_TOPO = 150   # onde o quadro aberto começa, dentro da área de 1660
COR = "eq=contrast=1.10:saturation=0.98:gamma=0.97,unsharp=5:5:0.35:5:5:0,vignette=angle=0.35"

lista = []
for i, p in enumerate(pecas):
    fx, fy, W4, H4, ZOOM, *larg = ROSTO[os.path.basename(p["bruto"])]
    fx = p.get("cx", fx)   # centro por pedaço, se o shorts.json mandar
    h = int(H4 / ZOOM) // 2 * 2; w = int(h * 1080 / 1660) // 2 * 2
    x0 = int(min(max(fx - w / 2, 0), W4 - w)); y0 = int(min(max(fy - 0.28 * h, 0), H4 - h))
    d = p["dur"]; fade = min(0.012, d / 4)
    if larg:
        cw = larg[0]; xl = int(min(max(fx - cw / 2, 0), W4 - cw)); ah = int(1080 * H4 / cw) // 2 * 2
        vf = (f"split[f][q];[f]crop={w}:{h}:{x0}:{y0},scale=1080:1660,boxblur=30:2,eq=brightness=-0.12[fundo];"
              f"[q]crop={cw}:{H4}:{xl}:0,scale=1080:{ah}:flags=lanczos[quadro];[fundo][quadro]overlay=0:{LARGO_TOPO},"
              f"fps=30000/1001,{COR},format=yuv420p")
    else:
        vf = f"crop={w}:{h}:{x0}:{y0},scale=1080:1660:flags=lanczos,fps=30000/1001,{COR},format=yuv420p"
    af = f"aresample=48000,afade=t=in:d={fade},afade=t=out:st={d - fade:.4f}:d={fade}"
    out = os.path.join(pasta, f"p{i:03d}.mov"); lista.append(out)
    if os.path.exists(out): continue
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['src_ini']:.4f}", "-i", os.path.join(BRUTO, p["bruto"]),
                    "-t", f"{d:.4f}", "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                    "-c:a", "pcm_s16le", "-ac", "2", out], check=True)
    print(i, end=" ", flush=True)
with open(os.path.join(pasta, "lista.txt"), "w", encoding="utf-8") as f:
    for x in lista: f.write(f"file '{os.path.basename(x)}'\n")   # relativo à pasta da lista
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(pasta, "lista.txt"),
                "-c", "copy", os.path.join(pasta, "base.mov")], check=True)
print("\nok", os.path.join(pasta, "base.mov"))
