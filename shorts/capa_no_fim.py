"""Põe a capa do Short (arte 1080x1920) por ~0,5 s no FIM do vídeo, para ela poder ser escolhida como capa no app do
YouTube (regra do ESTILO.md, 08/11/2026). Áudio em silêncio nesse trecho.
Uso: python -I ferramentas/shorts/capa_no_fim.py <short.mp4> <capa.jpg|png> <saida.mp4> [segundos=0.5]"""
import subprocess, sys

ent, capa, sai = sys.argv[1:4]; seg = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
if ent == sai: raise SystemExit("a saída precisa ser outro arquivo")
fc = (f"[0:v]setsar=1,fps=30000/1001,format=yuv420p[v0];"
      f"[1:v]scale=1080:1920,setsar=1,fps=30000/1001,format=yuv420p,trim=duration={seg}[v1];"
      f"[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
      f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={seg}[a1];"
      f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-loop", "1", "-framerate", "30000/1001", "-t", str(seg), "-i", capa,
                "-f", "lavfi", "-t", str(seg), "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex", fc,
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-profile:v", "high",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", sai], check=True)
print("ok", sai)
