"""Cortes dos Shorts tirando as pausas > 0,4 s pelo SOM (silencedetect), deixando 0,12 s de folga."""
import json, re, subprocess, sys
SRC = sys.argv[1]; SH = json.load(open("shorts.json", encoding="utf-8")); res = {}
for nome, faixas in SH.items():
    lst = []
    for a, b in faixas:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(a), "-t", str(b - a), "-i", SRC, "-vn", "-af",
                            "silencedetect=n=-30dB:d=0.4", "-f", "null", "-"], capture_output=True, text=True).stderr
        ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]; fim = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
        fala, t = [], 0.0
        for s0, s1 in zip(ini, fim + [b - a] * (len(ini) - len(fim))):
            if s0 - t > 0.05: fala.append((t, s0 + 0.12))
            t = max(s1 - 0.12, 0)
        if (b - a) - t > 0.05: fala.append((t, b - a))
        lst += [{"bruto": SRC, "src_ini": round(a + x, 4), "dur": round(y - x, 4)} for x, y in fala if y - x > 0.15]
    res[nome] = lst; print(nome, len(lst), "pedaços,", round(sum(p["dur"] for p in lst), 1), "s")
json.dump(res, open("cortes.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
