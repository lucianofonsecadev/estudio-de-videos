// Postador 2 tá bom! — tela. Conversa com servidor.py (só no seu PC).
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const arq = (c) => "/arquivo?c=" + encodeURIComponent(c);
const DIAS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];
let E = null, tela = "fila", sel = null, filtro = "todos", semana0 = inicioSemana(new Date()), sondando = null;

async function api(caminho, dados) {
  const r = await fetch(caminho, dados ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dados) } : {});
  const j = await r.json();
  if (!r.ok) throw new Error(j.erro || "erro");
  return j;
}
function aviso(txt) { const a = $("#aviso"); a.textContent = txt; a.hidden = false; clearTimeout(aviso.t); aviso.t = setTimeout(() => (a.hidden = true), 3500); }
function confirmar(titulo, html) {
  return new Promise((ok) => {
    $("#modal-titulo").textContent = titulo; $("#modal-texto").innerHTML = html; $("#modal").hidden = false; $("#modal-sim").focus();
    const fim = (v) => { $("#modal").hidden = true; ok(v); };
    $("#modal-sim").onclick = () => fim(true); $("#modal-nao").onclick = () => fim(false);
  });
}
function inicioSemana(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; }
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function quandoTxt(q) {
  if (!q || q === "agora") return "sem data";
  const [d, h] = q.split(" "); const x = new Date(d + "T12:00");
  return `${DIAS[x.getDay()].toLowerCase()} ${x.getDate()}/${x.getMonth() + 1} · ${h.replace(":00", "h")}`;
}
function situacao(f) {
  if (f.postado) return f.postado.agendado_para ? ["Agendado no YouTube", "p-ag"] : ["Postado", "p-ok"];
  if (f.erros.length) return ["Precisa de ajuste", "p-er"];
  return ["Aguardando", "p-es"];
}

async function carregar() { E = await api("/api/estado"); desenhar(); }
function desenhar() {
  document.querySelectorAll(".item").forEach((b) => b.classList.toggle("ativo", b.dataset.tela === tela));
  $("#status").innerHTML = `<b><span class="ponto ${E.conectado ? "" : "off"}"></span>${E.conectado ? "Conectado" : "Não conectado"}</b>
    <span>Canal 2 TÁ BOM</span><span>Envios hoje: ${E.envios_hoje} de ${E.cota_dia}</span>`;
  ({ fila: telaFila, calendario: telaCalendario, historico: telaHistorico, config: telaConfig })[tela]();
}

// ---------------- Fila ----------------
function telaFila() {
  const fs = E.fichas;
  const cont = { todos: fs.length, aguardando: fs.filter((f) => !f.postado).length, youtube: fs.filter((f) => f.postado).length };
  const vis = fs.filter((f) => filtro === "todos" || (filtro === "aguardando" ? !f.postado : f.postado));
  if (!sel || !fs.find((f) => f.id === sel)) sel = (vis[0] || fs[0] || {}).id;
  $("#tela").innerHTML = `
  <div class="topo"><div><h1>Fila de postagem</h1><p class="sub">${fs.length} fichas · ${cont.aguardando} aguardando · ${cont.youtube} já no YouTube</p></div>
    <div class="lado" style="flex:0 1 auto">${E.soltos.length ? `<select id="novo" aria-label="Vídeo sem ficha"><option value="">+ ficha para vídeo novo (${E.soltos.length})</option>${E.soltos.map((s) => `<option>${esc(s)}</option>`).join("")}</select>` : ""}
    <button class="b1" id="enviar-todos" type="button" ${cont.aguardando && !E.tarefa.rodando ? "" : "disabled"}>Enviar todos que estão prontos</button></div></div>
  ${progressoHtml()}
  <div class="grade">
    <section class="lista" aria-label="Vídeos">
      <div class="filtros">${[["todos", "Todos"], ["aguardando", "Aguardando"], ["youtube", "No YouTube"]].map(([k, n]) => `<button type="button" class="chip ${filtro === k ? "ativo" : ""}" data-f="${k}">${n} ${cont[k]}</button>`).join("")}</div>
      ${vis.length ? vis.map(cardHtml).join("") : `<div class="vazio">Nada aqui.</div>`}
    </section>
    ${sel ? editorHtml(fs.find((f) => f.id === sel)) : `<div class="vazio">Sem fichas. Escolha um vídeo novo acima.</div>`}
  </div>`;
  document.querySelectorAll(".chip").forEach((b) => (b.onclick = () => { filtro = b.dataset.f; desenhar(); }));
  document.querySelectorAll(".card").forEach((b) => (b.onclick = () => { sel = b.dataset.id; desenhar(); }));
  const nv = $("#novo"); if (nv) nv.onchange = () => novaFicha(nv.value);
  $("#enviar-todos").onclick = enviarTodos;
  if (sel) ligarEditor(fs.find((f) => f.id === sel));
}
function cardHtml(f) {
  const [st, cls] = situacao(f);
  return `<button type="button" class="card ${f.id === sel ? "sel" : ""}" data-id="${esc(f.id)}">
    ${f.capa ? `<img class="mini" alt="" src="${arq(f.capa)}">` : `<div class="mini"></div>`}
    <div style="min-width:0;display:flex;flex-direction:column;gap:5px"><span class="t">${esc(f.titulo || "(sem título)")}</span>
    <span class="a">${esc(f.arquivo)}</span><span class="linha"><span class="pill ${cls}">${st}</span>${esc(f.postado?.agendado_para ? quandoTxt(f.quando) : f.postado ? "" : quandoTxt(f.quando))}</span></div></button>`;
}
function editorHtml(f) {
  const [d, h] = f.quando && f.quando !== "agora" ? f.quando.split(" ") : ["", (E.config.horarios?.shorts_hora || "18:00")];
  const tags = (f.titulo || "").match(/#\w+/gu) || [];
  const trav = !!f.postado;
  return `<section class="painel" aria-label="Editar ${esc(f.id)}">
    <div class="previa">${f.arquivo ? `<video controls preload="metadata" src="${arq(f.arquivo)}" ${f.capa ? `poster="${arq(f.capa)}"` : ""}></video>` : ""}
      <small>${f.mb ? f.mb + " MB" : ""}${f.short ? " · Short" : ""}</small>
      ${f.capa ? `<img alt="Capa" src="${arq(f.capa)}">` : ""}<small>${f.capa ? "Capa" : "Sem capa"}</small></div>
    <form class="form" id="ed" onsubmit="return false">
      ${f.postado ? `<div class="okbox">Já está no YouTube: <a href="${esc(f.postado.link)}" target="_blank" rel="noopener">${esc(f.postado.link)}</a>${f.postado.agendado_para ? " · vai ao ar " + esc(quandoTxt(f.quando)) : ""}</div>` : ""}
      <div class="campo"><div class="lado"><label for="titulo">Título</label><span class="dica" id="cont" style="text-align:right"></span></div>
        <input id="titulo" type="text" value="${esc(f.titulo)}" ${trav ? "disabled" : ""}>
        <span class="dica ${f.short && tags.filter((t) => t.toLowerCase() !== "#shorts").length < 2 ? "ruim" : ""}" id="dica-tags">Short: 2 ou 3 hashtags do tema no fim do título.</span></div>
      <div class="campo"><label for="descricao">Descrição</label><textarea id="descricao" rows="5" ${trav ? "disabled" : ""}>${esc(f.descricao)}</textarea>
        <span class="dica">O fim fixo das Configurações entra sozinho no final.</span></div>
      <div class="campo"><label for="tags">Tags (separe por vírgula)</label><input id="tags" type="text" value="${esc((f.tags || []).join(", "))}" ${trav ? "disabled" : ""}></div>
      <fieldset class="campo" style="border:0;padding:0;margin:0"><legend class="rot" style="margin-bottom:6px">Quando postar</legend>
        <div class="lado"><label class="opc"><input type="radio" name="q" value="agora" ${!d ? "checked" : ""} ${trav ? "disabled" : ""}> Agora</label>
        <label class="opc"><input type="radio" name="q" value="agendar" ${d ? "checked" : ""} ${trav ? "disabled" : ""}> Agendar</label>
        <input id="data" type="date" aria-label="Data" value="${d}" ${trav ? "disabled" : ""}><input id="hora" type="time" aria-label="Hora" value="${h}" ${trav ? "disabled" : ""}></div></fieldset>
      <div class="lado"><div class="campo"><label for="vis">Visibilidade</label><select id="vis" ${trav ? "disabled" : ""}>
        ${[["public", "Público"], ["unlisted", "Não listado"], ["private", "Privado"]].map(([v, n]) => `<option value="${v}" ${(f.visibilidade || E.config.visibilidade_padrao || "public") === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>
        <div class="campo"><label for="capa">Capa (arquivo)</label><input id="capa" type="text" value="${esc(f.capa || "")}" ${trav ? "disabled" : ""}></div></div>
      ${f.erros.length && !trav ? `<div class="erros">${f.erros.map(esc).join("<br>")}</div>` : ""}
      ${trav ? "" : `<div class="lado"><button type="button" class="b2" id="salvar">Salvar</button>
        <button type="button" class="b1" id="postar" ${E.tarefa.rodando ? "disabled" : ""} style="flex:2 1 200px">${d ? "Agendar para " + esc(quandoTxt(f.quando)) : "Postar agora"}</button>
        <button type="button" class="b2 perigo" id="apagar" style="flex:0 1 auto">Tirar da fila</button></div>`}
    </form></section>`;
}
function lerEditor(f) {
  const q = document.querySelector("input[name=q]:checked").value, d = $("#data").value, h = $("#hora").value || "18:00";
  return { arquivo: f.arquivo, titulo: $("#titulo").value.trim(), descricao: $("#descricao").value,
    tags: $("#tags").value.split(",").map((t) => t.trim()).filter(Boolean),
    quando: q === "agendar" && d ? `${d} ${h}` : "agora", visibilidade: $("#vis").value, capa: $("#capa").value.trim() || null };
}
function ligarEditor(f) {
  const t = $("#titulo"); if (!t) return;
  const conta = () => { const n = t.value.length; $("#cont").textContent = `${n} / 100`; $("#cont").className = "dica" + (n > 100 ? " ruim" : "");
    const k = (t.value.match(/#\w+/gu) || []).filter((x) => x.toLowerCase() !== "#shorts").length;
    $("#dica-tags").className = "dica" + (f.short && k < 2 ? " ruim" : ""); };
  t.oninput = conta; conta();
  if (f.postado) return;
  const salvar = async () => { await api("/api/ficha", { id: f.id, ficha: lerEditor(f) }); await carregar(); };
  $("#salvar").onclick = async () => { await salvar(); aviso("Ficha salva"); };
  $("#apagar").onclick = async () => {
    if (!(await confirmar("Tirar da fila?", `<p>A ficha <b>${esc(f.titulo)}</b> sai da fila. O vídeo continua em <code>${esc(f.arquivo)}</code>.</p>`))) return;
    await api("/api/apagar-ficha", { id: f.id }); sel = null; await carregar();
  };
  $("#postar").onclick = async () => {
    await salvar(); const g = E.fichas.find((x) => x.id === f.id);
    if (g.erros.length) return aviso("Corrija os problemas em vermelho antes");
    const ok = await confirmar(g.quando === "agora" ? "Postar agora?" : "Agendar no YouTube?", `<ul>
      <li><b>${esc(g.titulo)}</b></li><li>${g.quando === "agora" ? "Vai ao ar assim que subir (" + esc(g.visibilidade || "public") + ")" : "Vai ao ar " + esc(quandoTxt(g.quando))}</li>
      <li>Arquivo: ${esc(g.arquivo)} (${g.mb} MB)</li><li>Capa: ${esc(g.capa || "nenhuma")}</li></ul>`);
    if (ok) iniciarEnvio([g.id]);
  };
}
async function novaFicha(caminho) {
  if (!caminho) return;
  const id = caminho.split("/").pop().replace(/\.\w+$/, "").replace(/^2tabom-/, "").replace(/[^\w-]/g, "");
  await api("/api/ficha", { id, ficha: { arquivo: caminho, titulo: "", descricao: "", tags: [], quando: "agora", capa: null } });
  sel = id; filtro = "todos"; await carregar(); aviso("Ficha criada: preencha título e descrição");
}
async function enviarTodos() {
  const prontos = E.fichas.filter((f) => !f.postado && !f.erros.length);
  if (!prontos.length) return aviso("Nenhuma ficha pronta (sem problemas em vermelho)");
  const ok = await confirmar(`Enviar ${prontos.length} vídeo(s)?`, `<ul>${prontos.map((f) => `<li><b>${esc(f.titulo)}</b> — ${esc(quandoTxt(f.quando))}</li>`).join("")}</ul>
    <p>Limite de hoje: ${E.cota_dia - E.envios_hoje} envio(s).</p>`);
  if (ok) iniciarEnvio(prontos.slice(0, E.cota_dia - E.envios_hoje).map((f) => f.id));
}
async function iniciarEnvio(ids) {
  try { await api("/api/postar", { ids }); } catch (e) { return aviso(e.message); }
  await carregar(); sondar();
}
function progressoHtml() {
  const t = E.tarefa; if (!t.rodando && !t.erro && !t.link) return "";
  if (t.erro) return `<div class="erros">Falhou ao enviar ${esc(t.id)}: ${esc(t.erro)}</div>`;
  if (!t.rodando) return `<div class="okbox">Pronto! ${esc(t.id)}: <a href="${esc(t.link)}" target="_blank" rel="noopener">${esc(t.link)}</a></div>`;
  return `<div class="prog" role="status"><div class="lado"><b>Enviando ${esc(t.id)}… ${esc(t.texto)}</b><span style="text-align:right">${t.pct}%${t.fila.length > 1 ? ` · faltam ${t.fila.length - 1}` : ""}</span></div><div class="barra"><i style="width:${t.pct}%"></i></div></div>`;
}
function sondar() {
  clearInterval(sondando);
  sondando = setInterval(async () => {
    E.tarefa = await api("/api/tarefa");
    if (!E.tarefa.rodando) { clearInterval(sondando); await carregar(); return; }
    const p = $(".prog"); if (p) p.outerHTML = progressoHtml(); else desenhar();
  }, 1500);
}

// ---------------- Calendário ----------------
function telaCalendario() {
  const dias = [...Array(7)].map((_, i) => { const d = new Date(semana0); d.setDate(d.getDate() + i); return d; });
  const fim = new Date(dias[6]);
  const semData = E.fichas.filter((f) => !f.postado && (!f.quando || f.quando === "agora"));
  $("#tela").innerHTML = `
  <div class="topo"><div><h1>Calendário</h1><p class="sub">Clique num vídeo para abrir a ficha.</p></div>
    <div class="nav"><button class="b2" type="button" id="ant" aria-label="Semana anterior">‹</button>
    <b style="flex:0 0 auto">${dias[0].getDate()}/${dias[0].getMonth() + 1} a ${fim.getDate()}/${fim.getMonth() + 1}</b>
    <button class="b2" type="button" id="prox" aria-label="Próxima semana">›</button><button class="b2" type="button" id="hoje">Hoje</button></div></div>
  <div class="semana"><div class="dias">${dias.map((d) => {
    const evs = E.fichas.filter((f) => f.quando && f.quando.startsWith(iso(d)));
    return `<div class="dia ${iso(d) === iso(new Date()) ? "hoje" : ""}"><header>${DIAS[d.getDay()]}<b>${d.getDate()}</b></header>
      ${evs.map((f) => `<button type="button" class="ev ${f.short ? "" : "longo"} ${f.postado ? "feito" : ""}" data-id="${esc(f.id)}"><small>${esc(f.quando.split(" ")[1])} · ${f.short ? "Short" : "Vídeo longo"}${f.postado ? " · no YouTube" : ""}</small>${esc(f.titulo.replace(/\s#\w+/gu, ""))}</button>`).join("") || `<span class="sub" style="font-size:13px">livre</span>`}</div>`;
  }).join("")}</div></div>
  <section class="bloco"><div class="topo"><h2>Sem data ainda (${semData.length})</h2>
    <button class="b1" type="button" id="distribuir" ${semData.length ? "" : "disabled"}>Distribuir nos horários padrão</button></div>
    <div class="lado">${semData.map((f) => `<button type="button" class="chip" data-id="${esc(f.id)}" style="flex:0 1 auto">${esc(f.titulo || f.id)}</button>`).join("") || `<span class="sub">Todos os vídeos têm data.</span>`}</div></section>`;
  $("#ant").onclick = () => { semana0.setDate(semana0.getDate() - 7); desenhar(); };
  $("#prox").onclick = () => { semana0.setDate(semana0.getDate() + 7); desenhar(); };
  $("#hoje").onclick = () => { semana0 = inicioSemana(new Date()); desenhar(); };
  document.querySelectorAll("[data-id]").forEach((b) => (b.onclick = () => { sel = b.dataset.id; tela = "fila"; filtro = "todos"; desenhar(); }));
  $("#distribuir").onclick = () => distribuir(semData);
}
async function distribuir(lista) {
  const H = E.config.horarios || {}, diasS = H.shorts_dias || [1, 3, 5], horaS = H.shorts_hora || "18:00";
  const ocupado = new Set(E.fichas.filter((f) => f.quando && f.quando !== "agora").map((f) => f.quando.split(" ")[0]));
  const d = new Date(); d.setDate(d.getDate() + 1); const plano = [];
  for (const f of lista) {
    while (!diasS.includes(d.getDay()) || ocupado.has(iso(d))) d.setDate(d.getDate() + 1);
    plano.push([f, `${iso(d)} ${horaS}`]); ocupado.add(iso(d)); d.setDate(d.getDate() + 1);
  }
  const ok = await confirmar("Distribuir assim?", `<ul>${plano.map(([f, q]) => `<li><b>${esc(f.titulo || f.id)}</b> → ${esc(quandoTxt(q))}</li>`).join("")}</ul><p>Só marca as datas nas fichas; nada é enviado.</p>`);
  if (!ok) return;
  for (const [f, q] of plano) { const { id, postado, erros, mb, short, ...ficha } = f; await api("/api/ficha", { id, ficha: { ...ficha, quando: q } }); }
  await carregar(); aviso("Datas marcadas");
}

// ---------------- Histórico ----------------
function telaHistorico() {
  const ps = Object.entries(E.postados).sort((a, b) => String(b[1].quando_postou).localeCompare(String(a[1].quando_postou)));
  $("#tela").innerHTML = `<div><h1>Histórico</h1><p class="sub">Tudo o que o Postador já mandou para o YouTube.</p></div>
  ${ps.length ? `<div class="bloco tab"><table><thead><tr><th>Título</th><th>Enviado em</th><th>Vai ao ar</th><th>Link</th></tr></thead><tbody>
    ${ps.map(([id, p]) => `<tr><td><b>${esc(p.titulo)}</b>${p.apagado_em ? ` <span class="pill p-er">apagado em ${esc(p.apagado_em)}</span>` : ""}<br><span class="sub" style="font-size:12px">${esc(p.arquivo)}</span></td>
      <td>${esc(String(p.quando_postou).replace("T", " ").slice(0, 16))}</td><td>${p.agendado_para ? esc(new Date(p.agendado_para).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })) : "na hora"}</td>
      <td>${p.apagado_em ? "—" : `<a href="${esc(p.link)}" target="_blank" rel="noopener">${esc(p.link)}</a>`}</td></tr>`).join("")}</tbody></table></div>`
    : `<div class="vazio">Nada postado ainda.</div>`}`;
}

// ---------------- Configurações ----------------
function telaConfig() {
  const c = E.config, H = c.horarios || {}, dS = H.shorts_dias || [1, 3, 5];
  $("#tela").innerHTML = `<h1>Configurações</h1>
  <section class="bloco"><h2>Conexão com o YouTube</h2>
    <p style="margin:0">${E.conectado ? "✅ Conectado ao canal 2 TÁ BOM." : "❌ Não conectado. Rode <code>postar.py --conectar</code> (o Claude faz)."}
    ${E.credencial ? "" : "<br>Falta <code>credencial.json</code> (ver LEIAME)."}</p>
    <p class="sub" style="margin:0">Até a análise do YouTube ser aprovada, vídeos enviados pelo Postador podem ficar travados como privados.</p></section>
  <section class="bloco"><h2>Horários padrão</h2>
    <fieldset style="border:0;padding:0;margin:0"><legend class="rot" style="margin-bottom:8px">Dias dos Shorts</legend>
      <div class="lado">${[1, 2, 3, 4, 5, 6, 0].map((n) => `<label class="opc"><input type="checkbox" name="dia" value="${n}" ${dS.includes(n) ? "checked" : ""}> ${DIAS[n].toLowerCase()}</label>`).join("")}</div></fieldset>
    <div class="lado"><div class="campo"><label for="hs">Hora dos Shorts</label><input id="hs" type="time" value="${H.shorts_hora || "18:00"}"></div>
      <div class="campo"><label for="hl">Hora do vídeo longo</label><input id="hl" type="time" value="${H.longo_hora || "10:00"}"></div></div></section>
  <section class="bloco"><h2>Textos e padrões</h2>
    <div class="campo"><label for="fim">Fim de toda descrição</label><textarea id="fim" rows="3">${esc(c.fim_da_descricao || "")}</textarea></div>
    <div class="campo"><label for="tf">Tags fixas (separe por vírgula)</label><input id="tf" type="text" value="${esc((c.tags_fixas || []).join(", "))}"></div>
    <div class="lado"><div class="campo"><label for="vp">Visibilidade padrão</label><select id="vp">${[["public", "Público"], ["unlisted", "Não listado"], ["private", "Privado"]].map(([v, n]) => `<option value="${v}" ${(c.visibilidade_padrao || "public") === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>
      <div class="campo"><label for="pl">ID da playlist dos Shorts (opcional)</label><input id="pl" type="text" value="${esc(c.playlist_shorts || "")}"></div></div></section>
  <div class="lado" style="justify-content:flex-end"><button class="b1" type="button" id="salvar-cfg" style="flex:0 1 240px">Salvar configurações</button></div>`;
  $("#salvar-cfg").onclick = async () => {
    await api("/api/config", { fim_da_descricao: $("#fim").value, tags_fixas: $("#tf").value.split(",").map((t) => t.trim()).filter(Boolean),
      visibilidade_padrao: $("#vp").value, playlist_shorts: $("#pl").value.trim() || null,
      horarios: { shorts_dias: [...document.querySelectorAll("input[name=dia]:checked")].map((i) => +i.value), shorts_hora: $("#hs").value, longo_hora: $("#hl").value } });
    await carregar(); aviso("Configurações salvas");
  };
}

document.querySelectorAll(".item").forEach((b) => (b.onclick = () => { tela = b.dataset.tela; history.replaceState(null, "", "#" + tela); desenhar(); }));
{ const [t, s] = location.hash.slice(1).split("/"); if (["fila", "calendario", "historico", "config"].includes(t)) tela = t; if (s) sel = s; }   // ex.: #calendario ou #fila/patrimonio2
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#modal").hidden) $("#modal-nao").click(); });
carregar().then(() => { if (E.tarefa.rodando) sondar(); }).catch((e) => ($("#tela").innerHTML = `<div class="erros">Não consegui falar com o servidor: ${esc(e.message)}</div>`));
