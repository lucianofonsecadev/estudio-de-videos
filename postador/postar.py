"""Posta vídeos no canal 2 TÁ BOM pela API oficial do YouTube (envio em pedaços: aguenta vídeo de qualquer tamanho).

Uso (rodar da pasta do projeto, com o Python do projeto):
  python ferramentas/youtube/postar.py --lista                 mostra a fila e o que já foi postado
  python ferramentas/youtube/postar.py --teste <id> [<id>...]  confere as fichas SEM enviar nada
  python ferramentas/youtube/postar.py <id> [<id> ...]         envia (publica ou agenda, conforme a ficha)
  python ferramentas/youtube/postar.py --conectar              só faz o login (abre o navegador para "Permitir")

As fichas ficam em final/postagens.json:
  {"patrimonio2": {"arquivo": "final/shorts/....mp4", "titulo": "...", "descricao": "...", "tags": ["..."],
                   "quando": "2026-11-11 18:00" | "agora", "visibilidade": "public"|"unlisted"|"private",
                   "capa": null | "trabalho/capa/x.jpg", "playlist": null | "<id da playlist>"}}
O texto fixo e as hashtags de config.json entram no fim de toda descrição.
Registro do que já subiu: ferramentas/youtube/postados.json (não posta o mesmo id duas vezes).
Arquivos secretos (não mandar para ninguém): credencial.json e token.json, nesta pasta."""
import datetime as dt, json, os, re, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(AQUI)   # raiz do repositório
FICHAS = os.path.join(P, "final", "postagens.json")
POSTADOS = os.path.join(AQUI, "postados.json")
CONFIG = os.path.join(AQUI, "config.json")
CREDENCIAL, TOKEN = os.path.join(AQUI, "credencial.json"), os.path.join(AQUI, "token.json")
ESCOPOS = ["https://www.googleapis.com/auth/youtube"]   # envio, capa e playlist
FUSO = dt.timezone(dt.timedelta(hours=-3))                # Brasília (sem horário de verão)
COTA_DIA = 6                                              # 10.000 unidades / 1.600 por envio
CATEGORIA = "22"                                          # Pessoas e blogs

def ler(arq, padrao):
    return json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else padrao
def salvar(arq, dados):
    json.dump(dados, open(arq, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def conferir(id_, f, cfg, postados):
    """Devolve (corpo da API, caminho do vídeo, lista de problemas)."""
    erros = []
    if id_ in postados: erros.append(f"já foi postado em {postados[id_]['quando_postou']}: {postados[id_]['link']}")
    video = os.path.join(P, f.get("arquivo", ""))
    if not os.path.isfile(video): erros.append(f"arquivo não encontrado: {f.get('arquivo')}")
    titulo = f.get("titulo", "").strip()
    if not titulo: erros.append("falta o título")
    if len(titulo) > 100: erros.append(f"título com {len(titulo)} letras (máximo 100)")
    if "<" in titulo or ">" in titulo: erros.append("título não pode ter < ou >")
    eh_short = "/shorts/" in f.get("arquivo", "").replace("\\", "/")
    if eh_short and len([h for h in re.findall(r"#\w+", titulo) if h.lower() != "#shorts"]) < 2:
        erros.append("Short sem 2 ou 3 hashtags do tema no título (regra do ESTILO.md, 08/11/2026)")
    desc = f.get("descricao", "").strip()
    fixo = cfg.get("fim_da_descricao", "").strip()
    if fixo and fixo not in desc: desc = desc + "\n\n" + fixo
    if len(desc.encode("utf-8")) > 5000: erros.append("descrição passou de 5.000 bytes")
    tags = list(dict.fromkeys(f.get("tags", []) + cfg.get("tags_fixas", [])))
    if sum(len(t) + 2 for t in tags) > 500: erros.append("tags passaram de 500 letras")
    vis = f.get("visibilidade", cfg.get("visibilidade_padrao", "public"))
    status = {"privacyStatus": vis, "selfDeclaredMadeForKids": False, "embeddable": True}
    quando = f.get("quando", "agora")
    if quando != "agora":
        try:
            t = dt.datetime.strptime(quando, "%Y-%m-%d %H:%M").replace(tzinfo=FUSO)
            if t < dt.datetime.now(FUSO) + dt.timedelta(minutes=15): erros.append(f"agendamento no passado ou em menos de 15 min: {quando}")
            status = {**status, "privacyStatus": "private", "publishAt": t.isoformat()}   # regra da API: agendado = privado até a hora
        except ValueError:
            erros.append(f"'quando' inválido: {quando} (use AAAA-MM-DD HH:MM ou agora)")
    capa = f.get("capa")
    if capa and not os.path.isfile(os.path.join(P, capa)): erros.append(f"capa não encontrada: {capa}")
    if capa and os.path.isfile(os.path.join(P, capa)) and os.path.getsize(os.path.join(P, capa)) > 2 * 1024 * 1024:
        erros.append("capa maior que 2 MB")
    corpo = {"snippet": {"title": titulo, "description": desc, "tags": tags, "categoryId": CATEGORIA,
                         "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"}, "status": status}
    return corpo, video, erros

def conectar():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    cred = Credentials.from_authorized_user_file(TOKEN, ESCOPOS) if os.path.exists(TOKEN) else None
    if cred and cred.expired and cred.refresh_token:
        try: cred.refresh(Request())
        except Exception: cred = None
    if not cred or not cred.valid:
        if not os.path.exists(CREDENCIAL):
            raise SystemExit(f"Falta a credencial do Google: {CREDENCIAL}\nVeja ferramentas/youtube/LEIAME.md, passo 1.")
        print("Abrindo o navegador: entre com a conta do canal 2 TÁ BOM e clique em Permitir.")
        cred = InstalledAppFlow.from_client_secrets_file(CREDENCIAL, ESCOPOS).run_local_server(port=0, open_browser=True)
        open(TOKEN, "w", encoding="utf-8").write(cred.to_json())
    yt = build("youtube", "v3", credentials=cred)
    canal = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
    return yt, canal

def enviar(yt, corpo, video, capa, playlist, progresso=None):
    """progresso: função opcional f(porcentagem, texto) — usada pela página do Postador."""
    avisa = progresso or (lambda pct, txt: None)
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(video, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/*")
    req = yt.videos().insert(part="snippet,status", body=corpo, media_body=media, notifySubscribers=True)
    resp, falhas = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"\r  enviando… {int(st.progress() * 100)}%", end="", flush=True); avisa(int(st.progress() * 100), "enviando")
            falhas = 0
        except Exception as e:            # internet caiu / erro do servidor: espera e continua do mesmo ponto
            falhas += 1
            if falhas > 8: raise
            espera = min(2 ** falhas, 120); print(f"\n  falhou ({e.__class__.__name__}); tentando de novo em {espera}s…")
            avisa(-1, f"internet falhou; tentando de novo em {espera}s"); time.sleep(espera)
    print("\r  enviando… 100%"); avisa(100, "capa e playlist")
    vid = resp["id"]
    if capa:
        try: yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(capa)).execute(); print("  capa ok")
        except Exception as e: print(f"  AVISO: a capa não entrou ({e}). Em Short isso é normal; dá para pôr no app.")
    if playlist:
        try:
            yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist,
                                      "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute(); print("  playlist ok")
        except Exception as e: print(f"  AVISO: não entrou na playlist ({e})")
    return vid, resp.get("status", {})

def main(args):
    fichas, postados, cfg = ler(FICHAS, {}), ler(POSTADOS, {}), ler(CONFIG, {})
    if not args or args[0] in ("-h", "--ajuda"): print(__doc__); return
    if args[0] == "--lista":
        print("FILA (final/postagens.json):")
        for i, f in fichas.items():
            print(f"  {'✓' if i in postados else '·'} {i:38} {f.get('quando', 'agora'):17} {f.get('titulo', '')}")
        hoje = dt.date.today().isoformat(); n = sum(1 for p in postados.values() if p["quando_postou"].startswith(hoje))
        print(f"Envios hoje: {n} de {COTA_DIA}"); return
    if args[0] == "--conectar":
        _, canal = conectar(); print("Conectado ao canal:", canal); return
    teste = args[0] == "--teste"; ids = args[1:] if teste else args
    falta = [i for i in ids if i not in fichas]
    if falta: raise SystemExit(f"Sem ficha em final/postagens.json: {', '.join(falta)}")
    pronto, ruim = [], False
    for i in ids:
        corpo, video, erros = conferir(i, fichas[i], cfg, postados)
        s = corpo["status"]; mb = os.path.getsize(video) / 1e6 if os.path.isfile(video) else 0
        print(f"\n[{i}] {corpo['snippet']['title']}")
        print(f"  arquivo: {fichas[i].get('arquivo')} ({mb:.0f} MB)")
        print(f"  quando: {'agendado para ' + s['publishAt'] if 'publishAt' in s else 'na hora, ' + s['privacyStatus']}")
        print(f"  tags: {', '.join(corpo['snippet']['tags'])}")
        for e in erros: print("  PROBLEMA:", e); ruim = True
        if not erros: print("  ok"); pronto.append((i, corpo, video))
    if teste or ruim:
        print("\nNada foi enviado." + (" Corrija os problemas acima." if ruim else "")); return
    hoje = dt.date.today().isoformat()
    if sum(1 for p in postados.values() if p["quando_postou"].startswith(hoje)) + len(pronto) > COTA_DIA:
        raise SystemExit(f"Passaria do limite de {COTA_DIA} envios por dia. Mande o resto amanhã.")
    yt, canal = conectar(); print(f"\nCanal: {canal}")
    for i, corpo, video in pronto:
        print(f"\nEnviando {i}…")
        f = fichas[i]; capa = os.path.join(P, f["capa"]) if f.get("capa") else None
        vid, st = enviar(yt, corpo, video, capa, f.get("playlist") or cfg.get("playlist_shorts") if "/shorts/" in f["arquivo"] else f.get("playlist"))
        link = f"https://youtu.be/{vid}"
        postados[i] = {"video_id": vid, "link": link, "titulo": corpo["snippet"]["title"], "arquivo": f["arquivo"],
                       "quando_postou": dt.datetime.now(FUSO).isoformat(timespec="seconds"),
                       "agendado_para": corpo["status"].get("publishAt"), "canal": canal}
        salvar(POSTADOS, postados)
        print(f"  pronto: {link}" + (f"  (vai ao ar {corpo['status']['publishAt']})" if corpo["status"].get("publishAt") else ""))
        if st.get("privacyStatus") == "private" and not corpo["status"].get("publishAt") and corpo["status"]["privacyStatus"] != "private":
            print("  ATENÇÃO: o YouTube deixou o vídeo PRIVADO. Enquanto a análise do Google não sair, é assim (LEIAME, passo 4).")

if __name__ == "__main__":
    main(sys.argv[1:])
