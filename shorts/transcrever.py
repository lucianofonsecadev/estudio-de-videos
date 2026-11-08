import json, sys, whisper
m = whisper.load_model("small")
r = m.transcribe(sys.argv[1], language="pt", word_timestamps=True, fp16=False)
seg = [{"a": round(s["start"],2), "b": round(s["end"],2), "t": s["text"].strip(),
        "w": [{"w": w["word"].strip(), "a": round(w["start"],3), "b": round(w["end"],3)} for w in s.get("words", [])]} for s in r["segments"]]
json.dump(seg, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(seg), "frases")
