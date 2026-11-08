"""Lê o projeto do FilmCraft e gera o mapa dos pedaços do bruto que ficaram no vídeo final (trilha V1).
Uso: python -I mapa.py <projeto.fcproj> <nome-da-sequencia> <mapa.json>
Cada item: bruto, ini (tempo no vídeo final), dur, src (tempo no bruto). Assim os Shorts usam só o que ficou no
vídeo (cortes de pausas, repetições e os cortes à mão do usuário) e podem ser pedidos com o tempo do BRUTO."""
import json, os, sys
T = 254016000000  # ticks por segundo
proj, nome_seq, saida = sys.argv[1:4]
d = json.load(open(proj, encoding="utf-8"))
it = d["project"]["items"]
seq = next(v for v in it.values() if "Sequence" in v["kind"] and v["name"] == nome_seq)["kind"]["Sequence"]
nomes = {int(k): v["name"] for k, v in it.items()}
BRUTO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bruto")
brutos = set(os.listdir(BRUTO))
out = []
for c in seq["video_tracks"][0]["items"]:
    nome = nomes.get(c["item"], "?")
    if nome in brutos and c.get("enabled", True):
        out.append({"bruto": nome, "ini": c["start"] / T, "dur": c["duration"] / T, "src": c["source_in"] / T})
out.sort(key=lambda x: x["ini"])
json.dump(out, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(out), "pedaços do bruto;", round(sum(o["dur"] for o in out), 1), "s no total")
