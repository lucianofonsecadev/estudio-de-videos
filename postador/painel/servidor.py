"""Postador 2 tá bom! — página no navegador (só no seu PC) em cima do postar.py.
Uso: python -I ferramentas/youtube/painel/servidor.py   (ou dois cliques em abrir-postador.bat) → http://localhost:8787
Só escuta em 127.0.0.1: ninguém de fora do computador acessa."""
import datetime as dt, json, mimetypes, os, re, sys, threading, traceback, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

AQUI = os.path.dirname(os.path.abspath(__file__)); Y = os.path.dirname(AQUI); P = os.path.dirname(Y)
sys.path.insert(0, Y)
import postar  # noqa: E402

PORTA = 8787
FONTES = os.path.join(P, "fontes")
tarefa = {"rodando": False, "id": None, "pct": 0, "texto": "", "erro": None, "link": None, "fila": []}
trava = threading.Lock()

def ler(arq, padrao): return postar.ler(arq, padrao)
def salvar(arq, d): postar.salvar(arq, d)

def videos_soltos(fichas):
    """Vídeos em final/ e final/shorts/ que ainda não têm ficha."""
    usados = {f.get("arquivo", "").replace("\\", "/") for f in fichas.values()}
    out = []
    for pasta in ("final", "final/shorts"):
        ab = os.path.join(P, pasta)
        if not os.path.isdir(ab): continue
        for n in sorted(os.listdir(ab)):
            rel = f"{pasta}/{n}"
            if n.lower().endswith((".mp4", ".mov")) and rel not in usados: out.append(rel)
    return out

def estado():
    fichas, postados, cfg = ler(postar.FICHAS, {}), ler(postar.POSTADOS, {}), ler(postar.CONFIG, {})
    hoje = dt.date.today().isoformat()
    lista = []
    for i, f in fichas.items():
        _, video, erros = postar.conferir(i, f, cfg, {k: v for k, v in postados.items() if k != i})
        ab = os.path.join(P, f.get("arquivo", ""))
        lista.append({"id": i, **f, "postado": postados.get(i), "erros": erros,
                      "mb": round(os.path.getsize(ab) / 1e6) if os.path.isfile(ab) else None,
                      "short": "/shorts/" in f.get("arquivo", "").replace("\\", "/")})
    return {"fichas": lista, "postados": postados, "config": cfg, "soltos": videos_soltos(fichas),
            "conectado": os.path.exists(postar.TOKEN), "credencial": os.path.exists(postar.CREDENCIAL),
            "envios_hoje": sum(1 for p in postados.values() if str(p.get("quando_postou", "")).startswith(hoje)),
            "cota_dia": postar.COTA_DIA, "tarefa": tarefa}

def postar_um(i):
    """Mesmo caminho do postar.py (conferir → conectar → enviar → registrar), avisando o progresso."""
    fichas, postados, cfg = ler(postar.FICHAS, {}), ler(postar.POSTADOS, {}), ler(postar.CONFIG, {})
    corpo, video, erros = postar.conferir(i, fichas[i], cfg, postados)
    if erros: raise ValueError("; ".join(erros))
    hoje = dt.date.today().isoformat()
    if sum(1 for p in postados.values() if str(p.get("quando_postou", "")).startswith(hoje)) >= postar.COTA_DIA:
        raise ValueError(f"limite de {postar.COTA_DIA} envios por dia atingido")
    yt, canal = postar.conectar()
    f = fichas[i]; capa = os.path.join(P, f["capa"]) if f.get("capa") else None
    pl = f.get("playlist") or (cfg.get("playlist_shorts") if "/shorts/" in f["arquivo"] else None)
    def prog(pct, txt):
        if pct >= 0: tarefa["pct"] = pct
        tarefa["texto"] = txt
    vid, _ = postar.enviar(yt, corpo, video, capa, pl, progresso=prog)
    link = f"https://youtu.be/{vid}"
    postados = ler(postar.POSTADOS, {})
    postados[i] = {"video_id": vid, "link": link, "titulo": corpo["snippet"]["title"], "arquivo": f["arquivo"],
                   "quando_postou": dt.datetime.now(postar.FUSO).isoformat(timespec="seconds"),
                   "agendado_para": corpo["status"].get("publishAt"), "canal": canal}
    salvar(postar.POSTADOS, postados)
    return link

def trabalhador(ids):
    for i in ids:
        tarefa.update(id=i, pct=0, texto="conectando", erro=None, link=None)
        try:
            tarefa["link"] = postar_um(i); tarefa["texto"] = "pronto"
        except Exception as e:
            traceback.print_exc(); tarefa["erro"] = str(e); tarefa["texto"] = "falhou"; break
        finally:
            tarefa["fila"] = [x for x in tarefa["fila"] if x != i]
    tarefa["rodando"] = False

def dentro_do_projeto(rel):
    ab = os.path.abspath(os.path.join(P, unquote(rel)))
    return ab if ab.startswith(os.path.abspath(P) + os.sep) and os.path.isfile(ab) else None

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, d, cod=200):
        b = json.dumps(d, ensure_ascii=False).encode("utf-8")
        self.send_response(cod); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def _arquivo(self, ab, tipo=None):
        tipo = tipo or mimetypes.guess_type(ab)[0] or "application/octet-stream"
        tam = os.path.getsize(ab); ini, fim = 0, tam - 1
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)", rng or "")
        if m:
            if m.group(1): ini = int(m.group(1))
            if m.group(2): fim = min(int(m.group(2)), tam - 1)
            self.send_response(206); self.send_header("Content-Range", f"bytes {ini}-{fim}/{tam}")
        else: self.send_response(200)
        self.send_header("Content-Type", tipo); self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1)); self.end_headers()
        with open(ab, "rb") as f:
            f.seek(ini); falta = fim - ini + 1
            while falta > 0:
                bloco = f.read(min(1 << 20, falta))
                if not bloco: break
                try: self.wfile.write(bloco)
                except (ConnectionResetError, BrokenPipeError): return
                falta -= len(bloco)
    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path in ("/", "/index.html"): return self._arquivo(os.path.join(AQUI, "index.html"), "text/html; charset=utf-8")
        if u.path in ("/app.css", "/app.js"): return self._arquivo(os.path.join(AQUI, u.path[1:]))
        if u.path in ("/favicon.svg", "/favicon.ico"): return self._arquivo(os.path.join(AQUI, "favicon.svg"), "image/svg+xml")
        if u.path.startswith("/fontes/"):
            ab = os.path.join(FONTES, os.path.basename(unquote(u.path)))
            return self._arquivo(ab, "font/ttf") if os.path.isfile(ab) else self._json({"erro": "não achei"}, 404)
        if u.path == "/api/estado": return self._json(estado())
        if u.path == "/api/tarefa": return self._json(tarefa)
        if u.path == "/arquivo":
            ab = dentro_do_projeto(q.get("c", [""])[0])
            return self._arquivo(ab) if ab else self._json({"erro": "arquivo fora do projeto ou inexistente"}, 404)
        self._json({"erro": "não achei"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        try: d = self._corpo()
        except Exception: return self._json({"erro": "pedido inválido"}, 400)
        if u.path == "/api/ficha":
            i = re.sub(r"[^\w-]", "", d.get("id", ""))
            if not i: return self._json({"erro": "falta o id"}, 400)
            fichas = ler(postar.FICHAS, {})
            campos = ("arquivo", "titulo", "descricao", "tags", "quando", "capa", "visibilidade", "playlist")
            fichas[i] = {k: d["ficha"][k] for k in campos if k in d.get("ficha", {})}
            salvar(postar.FICHAS, fichas); return self._json({"ok": True})
        if u.path == "/api/apagar-ficha":
            fichas = ler(postar.FICHAS, {}); fichas.pop(d.get("id"), None); salvar(postar.FICHAS, fichas)
            return self._json({"ok": True})
        if u.path == "/api/config":
            cfg = ler(postar.CONFIG, {}); cfg.update({k: v for k, v in d.items() if k in
                ("fim_da_descricao", "tags_fixas", "visibilidade_padrao", "playlist_shorts", "horarios")})
            salvar(postar.CONFIG, cfg); return self._json({"ok": True})
        if u.path == "/api/postar":
            ids = [i for i in d.get("ids", []) if i in ler(postar.FICHAS, {})]
            with trava:
                if tarefa["rodando"]: return self._json({"erro": "já tem um envio em andamento"}, 409)
                if not ids: return self._json({"erro": "nada para enviar"}, 400)
                tarefa.update(rodando=True, fila=list(ids), erro=None, link=None, pct=0, texto="começando")
            threading.Thread(target=trabalhador, args=(ids,), daemon=True).start()
            return self._json({"ok": True})
        self._json({"erro": "não achei"}, 404)

if __name__ == "__main__":
    url = f"http://localhost:{PORTA}"
    if sys.stdout is None:   # rodando escondido (pythonw, início do Windows): mensagens vão para um arquivo
        sys.stdout = sys.stderr = open(os.path.join(AQUI, "servidor.log"), "a", encoding="utf-8", buffering=1)
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/api/tarefa", timeout=1); ja_ligado = True
    except Exception: ja_ligado = False
    try:
        if ja_ligado: raise OSError
        ThreadingHTTPServer.allow_reuse_address = False   # no Windows, reuse deixaria 2 servidores na mesma porta
        srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    except OSError:          # já está ligado (ex.: ligou com o Windows): só abre a página
        print(f"O Postador já está ligado em {url}")
        if "--sem-navegador" not in sys.argv: webbrowser.open(url)
        sys.exit(0)
    print(f"Postador 2 tá bom! em {url}  (feche esta janela para desligar)")
    if "--sem-navegador" not in sys.argv: webbrowser.open(url)
    srv.serve_forever()
