"""Converte os trechos de cada Short (tempo do BRUTO, como na transcrição) nos pedaços que ficaram no vídeo final.
Uso: python -I cortes.py <mapa.json> <shorts.json> <cortes.json>
shorts.json: {"nome-do-short": [[ini, fim], ...]} em segundos do bruto, na ordem em que entram no Short.
Só entra o que ficou no vídeo final (pausas, repetições e cortes à mão ficam fora também no Short)."""
import json, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
SHORTS = json.load(open(sys.argv[2], encoding="utf-8"))

def pedacos(a, b):
    out = []
    for c in sorted(m, key=lambda c: c["src"]):
        si, sf = c["src"], c["src"] + c["dur"]
        x, y = max(a, si), min(b, sf)
        if y - x > 0.02:
            out.append({"bruto": c["bruto"], "src_ini": round(x, 4), "dur": round(y - x, 4)})
    return out

res = {}
for nome, faixas in SHORTS.items():
    lst = [p for a, b in faixas for p in pedacos(a, b)]
    res[nome] = lst
    print(nome, len(lst), "pedaços,", round(sum(p["dur"] for p in lst), 1), "s")
json.dump(res, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
