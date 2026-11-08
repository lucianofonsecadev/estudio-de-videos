"""Transcreve o áudio do base.mov com o tempo de cada palavra (Whisper small, português) — para a legenda.
Uso: python palavras.py <pasta_de_trabalho> <nome> [<nome> ...]"""
import json, os, sys, subprocess
import whisper

W = sys.argv[1]
for nome in sys.argv[2:]:
    pasta = os.path.join(W, nome); wav = os.path.join(pasta, "voz.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(pasta, "base.mov"), "-ac", "1", "-ar", "16000", wav], check=True)
    if "modelo" not in globals(): modelo = whisper.load_model("small")
    r = modelo.transcribe(wav, language="pt", word_timestamps=True, fp16=False)
    pal = [{"w": w["word"].strip(), "a": round(w["start"], 3), "b": round(w["end"], 3)}
           for seg in r["segments"] for w in seg.get("words", [])]
    json.dump(pal, open(os.path.join(pasta, "palavras.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(nome, len(pal), "palavras")
