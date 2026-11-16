/* Fluxo da demonstração: voto → ficha → ponto → tese → termo → ementa → alerta.
 *
 * A ordem das etapas é decidida por código (máquina de estados igual à de
 * backend/app/harness/estados.py). Cada chamada ao Claude é uma tarefa, com
 * prompt versionado (prompts.js, gerado de backend/app/prompts/) e saída JSON
 * conferida por código: evidências, teses, linter e montagem vêm do nucleo.js.
 *
 * Diferença assumida em relação à arquitetura definitiva (documento 01, regra 8):
 * aqui a página chama o Claude direto, sem o gateway do backend, e os termos são
 * sugestões marcadas como fora do tesauro, porque a base do TCN não está carregada.
 */
(function () {
  "use strict";
  const N = window.Nucleo, L = window.Leitura, PROMPTS = window.PROMPTS;
  const SOL = '<svg viewBox="0 0 24 24" aria-hidden="true"><polygon fill="#FFB300" points="12,0 13.6,5.9 18,1.6 16.5,7.5 22.4,6 18.1,10.4 24,12 18.1,13.6 22.4,18 16.5,16.5 18,22.4 13.6,18.1 12,24 10.4,18.1 6,22.4 7.5,16.5 1.6,18 5.9,13.6 0,12 5.9,10.4 1.6,6 7.5,7.5 6,1.6 10.4,5.9"/></svg>';
  const PASSOS = ["Voto", "Ficha", "Ponto", "Tese", "Tesauro", "Ementa", "Alerta"];
  const LIMITE_VOTO = 180000;

  // ------------------------------------------------ máquina de estados
  const TRANSICOES = {
    "AGUARDANDO_VOTO|ENVIAR_VOTO": "EXTRAINDO",
    "EXTRAINDO|CONCLUIR": (c) => (c.unica ? "PROPONDO_TESES" : "AGUARDANDO_OCORRENCIA"),
    "AGUARDANDO_OCORRENCIA|ESCOLHER": "PROPONDO_TESES",
    "PROPONDO_TESES|CONCLUIR": "AGUARDANDO_TESE",
    "AGUARDANDO_TESE|ESCOLHER": "BUSCANDO_TERMOS",
    "AGUARDANDO_TESE|DISPENSAR_TESE": "BUSCANDO_TERMOS",
    "AGUARDANDO_TESE|PEDIR_NOVAS_TESES": "PROPONDO_TESES",
    "BUSCANDO_TERMOS|CONCLUIR": "AGUARDANDO_TERMO",
    "AGUARDANDO_TERMO|ESCOLHER": "MONTANDO",
    "MONTANDO|CONCLUIR": (c) => (c.unica || c.restantes === 0 ? "VERIFICANDO" : "AGUARDANDO_MAIS_OCORRENCIA"),
    "AGUARDANDO_MAIS_OCORRENCIA|ADICIONAR_OCORRENCIA": "AGUARDANDO_OCORRENCIA",
    "AGUARDANDO_MAIS_OCORRENCIA|ENCERRAR": "VERIFICANDO",
    "VERIFICANDO|CONCLUIR": "CONCLUIDA",
    "AGUARDANDO_OCORRENCIA|VOLTAR": "AGUARDANDO_VOTO",
    "AGUARDANDO_TESE|VOLTAR": (c) => (c.unica ? "AGUARDANDO_VOTO" : "AGUARDANDO_OCORRENCIA"),
    "AGUARDANDO_TERMO|VOLTAR": "AGUARDANDO_TESE",
  };
  const PASSO_DO_ESTADO = {
    AGUARDANDO_VOTO: 0, EXTRAINDO: 1, AGUARDANDO_OCORRENCIA: 2, PROPONDO_TESES: 3, AGUARDANDO_TESE: 3,
    BUSCANDO_TERMOS: 4, AGUARDANDO_TERMO: 4, MONTANDO: 5, AGUARDANDO_MAIS_OCORRENCIA: 5, VERIFICANDO: 6, CONCLUIDA: 7,
  };
  function destino(acao) {
    const d = TRANSICOES[S.estado + "|" + acao];
    return d === undefined ? null : typeof d === "function" ? d(S.ctx) : d;
  }
  function disparar(acao) {
    const d = destino(acao);
    if (!d) throw new Error(`Ação ${acao} não é aceita no estado ${S.estado}.`);
    S.estado = d;
    S.fim = d === "CONCLUIDA";
    pinta();
    return d;
  }

  // ------------------------------------------------------- utilidades
  const $ = (id) => document.getElementById(id);
  const col = $("col"), fio = $("fio");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const calmo = matchMedia("(prefers-reduced-motion:reduce)").matches;
  let S, pend = null, aba = "ementa";

  let sample = null;
  const sampleProntoP = (window.claude ? window.claude.use("sample") : Promise.resolve(null)).then((s) => (sample = s)).catch(() => null);
  let downloads = null;
  (window.claude ? window.claude.use("downloads") : Promise.resolve(null)).then((d) => (downloads = d)).catch(() => null);

  function tempo() { const s = Math.floor((Date.now() - S.t0) / 1000); return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); }
  function reg(tipo, txt) { S.reg.push([tempo(), tipo, txt]); if (aba === "registro") painel(); }
  function sit(t) { $("atualSit").textContent = t; }
  function dica(t) { $("txt").placeholder = t; }
  function rola() { requestAnimationFrame(() => (fio.scrollTop = fio.scrollHeight)); }
  function bot(html) { const d = document.createElement("div"); d.className = "msg bot"; d.innerHTML = `<span>${SOL}</span><div>${html}</div>`; col.appendChild(d); rola(); return d; }
  function eu(t) { const d = document.createElement("div"); d.className = "msg eu"; d.innerHTML = `<div>${esc(t)}</div>`; col.appendChild(d); rola(); }
  function opcoes(lista, fn) {
    const id = "g" + Math.random().toString(36).slice(2);
    pend = { id, n: lista.length, fn };
    return `<div class="ops" id="${id}">` + lista.map((o, i) => `<button class="op" data-i="${i}"><span class="n">${i + 1}</span><span>${o}</span></button>`).join("") + `</div>`;
  }
  function escolhe(i) {
    if (!pend || i < 0 || i >= pend.n) return false;
    const g = $(pend.id), fn = pend.fn; pend = null;
    g.querySelectorAll(".op").forEach((b, k) => { b.disabled = true; if (k === i) b.classList.add("sel"); });
    fn(i); return true;
  }
  col.addEventListener("click", (e) => {
    const b = e.target.closest(".op");
    if (b && pend && b.parentNode.id === pend.id) { eu(b.querySelector("span:last-child").innerText.split("\n")[0].slice(0, 140)); escolhe(+b.dataset.i); return; }
    const c = e.target.closest(".chip"); if (c) { $("txt").value = ""; perguntar(c.textContent); }
  });

  function pinta() {
    const passo = PASSO_DO_ESTADO[S.estado] ?? 0;
    $("trilha").innerHTML = PASSOS.map((p, i) => `<li class="passo ${S.fim || i < passo ? "feito" : i === passo ? "agora" : ""}"${i === passo && !S.fim ? ' aria-current="step"' : ""}>${p}</li>`).join("");
    const pct = S.fim ? 100 : ((passo + 0.5) / 7) * 100;
    $("resto").style.width = 100 - pct + "%";
    if (!$("sol").firstChild) $("sol").innerHTML = SOL;
    $("sol").firstChild.style.left = pct + "%";
    $("sol").firstChild.style.display = S.fim ? "none" : "";
    painel();
  }

  /** Bolha de progresso com linhas e botão Parar. */
  function progresso() {
    const d = bot(`<div class="pensa"><ul></ul></div><button class="btn sec parar">Parar</button>`);
    const ul = d.querySelector("ul"), parar = d.querySelector(".parar");
    S.ctl = new AbortController();
    const ctl = S.ctl;
    parar.onclick = () => ctl.abort();
    return {
      linha(t) { if (ul.lastChild) ul.lastChild.className = "ok"; const li = document.createElement("li"); li.innerHTML = "<i></i>" + t; ul.appendChild(li); rola(); },
      fim() { d.remove(); },
      signal: ctl.signal,
    };
  }

  // ---------------------------------------------------- chamada ao Claude
  function renderizar(nome, vars) {
    const p = PROMPTS[nome];
    return p.texto.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, k) => {
      if (!(k in vars)) throw new Error(`Prompt ${nome}: variável ausente ${k}`);
      const v = vars[k];
      return typeof v === "string" ? v : JSON.stringify(v, null, 1);
    });
  }

  async function chamar(nome, vars, { json = true, tier = "default", signal, onText, cache } = {}) {
    await Promise.race([sampleProntoP, new Promise((r) => setTimeout(r, 11000))]);
    if (!sample) throw { code: "sem_claude" };
    const sessao = S, p = PROMPTS[nome], texto = renderizar(nome, vars), t0 = performance.now();
    const opts = { modelTier: tier, signal };
    if (onText) opts.onText = onText;
    if (cache !== undefined) opts.cache = cache;
    try {
      const r = json ? await sample.json(texto, opts) : await sample(texto, opts);
      if (S !== sessao) throw { code: "descartado" };
      const seg = ((performance.now() - t0) / 1000).toFixed(1);
      reg("modelo", `${nome} v${p.versao} · ${seg} s`);
      S.eventos.push({ quando: new Date().toISOString(), etapa: S.estado, tipo: "chamada_modelo", versao_prompt: `${nome}@${p.versao}`, duracao_s: Number(seg) });
      return r;
    } catch (e) {
      if (S !== sessao || (e && e.code === "descartado")) throw { code: "descartado" };
      reg("erro", `${nome} v${p.versao}: ${e && e.code ? e.code : "erro"}`);
      S.eventos.push({ quando: new Date().toISOString(), etapa: S.estado, tipo: "erro", versao_prompt: `${nome}@${p.versao}`, codigo: e && e.code });
      throw e;
    }
  }

  const ERROS = {
    sem_claude: "Esta página precisa ser aberta pelo Claude (claude.ai) para chamar o modelo.",
    not_granted: "O uso do Claude não foi autorizado nesta página. Recarregue a página e autorize para continuar.",
    sampling_disabled: "O Claude não está disponível para esta conta.",
    rate_limited: "O limite de uso do Claude foi atingido. Tente de novo em alguns minutos.",
    session_expired: "A sessão expirou. Entre de novo no Claude e recarregue a página.",
    prompt_too_large: "O voto é grande demais para uma chamada. Envie só relatório, voto e parte dispositiva.",
    invalid_json: "O Claude respondeu fora do formato esperado.",
    refused: "O Claude recusou esta solicitação.",
    cancelled: "Etapa interrompida.",
    formato: "A resposta do Claude veio incompleta.",
  };
  const DEFINITIVOS = new Set(["sem_claude", "not_granted", "sampling_disabled"]);
  function falha(e, tentar) {
    const code = (e && e.code) || "erro";
    if (code === "descartado") return;
    const msg = ERROS[code] || "Falha na chamada ao Claude.";
    const d = bot(`<div class="erro"><b>${esc(msg)}</b>${e && e.detalhe ? esc(e.detalhe) : ""}</div>` +
      (DEFINITIVOS.has(code) ? "" : `<div class="acoes"><button class="btn sec tentar">Tentar de novo</button></div>`));
    const b = d.querySelector(".tentar");
    if (b) b.onclick = () => { b.disabled = true; tentar(); };
    sit("Parado: " + msg.toLowerCase().slice(0, 40));
  }

  // ------------------------------------------------------------ texto
  function votoPaginado() {
    let t = S.doc.paginas.map((p) => `[[p. ${p.numero}]]\n${p.texto}`).join("\n\n");
    if (t.length > LIMITE_VOTO) { t = t.slice(0, LIMITE_VOTO); reg("aviso", "Voto truncado para caber em uma chamada"); }
    return t;
  }
  const textoVoto = () => S.doc.paginas.map((p) => p.texto).join("\n");
  const semEvidencias = (x) => JSON.parse(JSON.stringify(x, (k, v) => (k === "evidencia" || k === "status" || k === "pagina_encontrada" ? undefined : v)));
  const rotuloMod = (m) => (N.ROTULOS_MODALIDADE[m] ? N.ROTULOS_MODALIDADE[m][0].charAt(0) + N.ROTULOS_MODALIDADE[m][0].slice(1).toLowerCase() : m || "não identificada");
  const ROTULOS = {
    PLENO: "Pleno", PRIMEIRA_CAMARA: "Primeira Câmara", SEGUNDA_CAMARA: "Segunda Câmara",
    APLICADA: "aplicada", NAO_APLICADA: "não aplicada", MANUTENCAO: "mantida", REDUCAO: "reduzida", EXCLUSAO: "excluída", MAJORACAO: "majorada",
    DETERMINACOES: "determinações", RECOMENDACOES: "recomendações", CIENCIA: "ciência", MULTA: "multa", DEBITO: "débito",
    REMESSA_MP: "remessa ao Ministério Público", REGISTRO: "registro", NEGATIVA_REGISTRO: "negativa de registro",
    REGULAR: "regularidade", REGULAR_COM_RESSALVAS: "regularidade com ressalvas", IRREGULAR: "irregularidade",
    APROVACAO: "aprovação", APROVACAO_COM_RESSALVAS: "aprovação com ressalvas", REJEICAO: "rejeição", LEGAL: "legalidade", ILEGAL: "ilegalidade",
    CAUTELAR_CONCEDIDA: "cautelar concedida", CAUTELAR_NAO_CONCEDIDA: "cautelar não concedida", NAO_CONHECIDO: "não conhecimento",
    PROVIDO: "provimento", PARCIALMENTE_PROVIDO: "provimento parcial", NAO_PROVIDO: "desprovimento", ACOLHIDOS: "embargos acolhidos",
    REJEITADOS: "embargos rejeitados", PROCEDENTE: "procedência", IMPROCEDENTE: "improcedência", ARQUIVAMENTO: "arquivamento",
  };
  const rotuloEnum = (v) => (v ? ROTULOS[v] || String(v).replace(/_/g, " ").toLowerCase() : "");
  const paginas = (b) => (b.pagina_inicial === b.pagina_final ? `p. ${b.pagina_inicial}` : `p. ${b.pagina_inicial}–${b.pagina_final}`);
  const caminhoLegivel = (c) => c.replace(/^ocorrencias\[[^\]]+\]\./, "").replace(/^(\w+)\[(\d+)\]$/, (_, k, i) => ({ fundamentos: "fundamento", normas: "norma", precedentes: "precedente" }[k] || k) + " " + (Number(i) + 1));

  // ------------------------------------------------------ início
  function inicio() {
    S = { estado: "AGUARDANDO_VOTO", ctx: { unica: false, restantes: null }, fim: false, t0: Date.now(), reg: [], eventos: [],
      doc: null, ficha: null, itens: [], ponto: null, teses: null, teseAtual: undefined, ementa: null, alertas: [], novo: null,
      ciencia: true, aguardandoOrientacao: false, ctl: null };
    pend = null; col.innerHTML = ""; aba = "ementa"; $("abaGabarito").hidden = true;
    col.innerHTML = `<div class="vazio"><h2>Do voto à ementa, uma decisão de cada vez</h2>
      <p>O Claude lê o voto e monta a ficha; você escolhe o ponto decidido, a tese e o termo de indexação. Cada trecho citado é conferido no voto, e a ementa final passa pelas regras da Portaria Normativa TC nº 322/2026.</p>
      <label class="sigilo"><input type="checkbox" id="sigilo"><span>Confirmo que o voto que vou enviar é <b>fictício ou já publicado</b>. Esta demonstração roda fora da rede do Tribunal.</span></label>
      <div class="solta" id="solta"><div class="acoes">
        <button class="btn" id="escolhe" disabled>Escolher o arquivo do voto</button>
        <button class="btn sec" id="colar" disabled>Colar o texto</button>
        <button class="btn sec" id="exemplo">Usar o voto fictício de exemplo</button></div>
        <small>PDF, DOCX, ODT ou TXT. Também é possível arrastar o arquivo para esta área. O arquivo é lido no seu navegador; só o texto é enviado ao Claude.</small>
        <div id="areaCola" hidden><textarea class="cola" id="cola" placeholder="Cole aqui o inteiro teor"></textarea><div class="acoes" style="margin-top:8px"><button class="btn" id="usarCola">Usar este texto</button></div></div>
      </div></div>`;
    const sig = $("sigilo");
    sig.onchange = () => { $("escolhe").disabled = $("colar").disabled = !sig.checked; };
    $("escolhe").onclick = () => $("arq").click();
    $("colar").onclick = () => { $("areaCola").hidden = false; $("cola").focus(); };
    $("usarCola").onclick = () => { const t = $("cola").value.trim(); if (t.length > 200) receber(t, "Texto colado"); };
    $("exemplo").onclick = () => receber(new File([window.VOTO_EXEMPLO], "voto-ficticio-auditoria.txt", { type: "text/plain" }), "voto-ficticio-auditoria.txt");
    const so = $("solta");
    so.ondragover = (e) => { e.preventDefault(); so.classList.add("sobre"); };
    so.ondragleave = () => so.classList.remove("sobre");
    so.ondrop = (e) => { e.preventDefault(); so.classList.remove("sobre"); if (!sig.checked) { sig.focus(); return; } const f = e.dataTransfer.files[0]; if (f) receber(f, f.name); };
    $("atualNome").textContent = "Nova ementa"; sit("Aguardando o voto"); dica("Envie o voto para começar");
    pinta();
    sampleProntoP.then(() => { if (!sample && S.estado === "AGUARDANDO_VOTO" && !document.querySelector(".sem-claude")) bot(`<p class="nota sem-claude">Para o Claude ler o voto, esta página precisa estar aberta pelo Claude (claude.ai). Fora dele só a leitura do arquivo funciona.</p>`); });
  }

  // -------------------------------------------------- 1–2. voto e ficha
  async function receber(origem, nome) {
    eu("Voto enviado: " + nome);
    disparar("ENVIAR_VOTO");
    sit("Lendo o voto"); dica("Lendo o voto…");
    const pr = progresso();
    pr.linha("Convertendo o arquivo em texto, no seu navegador");
    try {
      S.doc = await L.carregar(origem);
    } catch (e) {
      pr.fim(); bot(`<div class="erro"><b>Não consegui ler o arquivo.</b>${esc(e.message || e)}</div>`);
      S.estado = "AGUARDANDO_VOTO"; pinta(); sit("Aguardando o voto"); dica("Envie o voto para começar"); return;
    }
    reg("arquivo", `${S.doc.nome}, ${S.doc.paginas.length} página(s), sha256 ${S.doc.hash.slice(0, 12)}…`);
    pr.linha(`${S.doc.paginas.length} página(s) lida(s)` + (S.doc.bloco ? `; ementa já existente removida (${paginas(S.doc.bloco)})` : ""));
    if (S.doc.avisos.some((a) => /sem camada de texto/.test(a))) {
      pr.fim(); bot(`<div class="erro"><b>O PDF não tem texto.</b>Ele parece digitalizado. Envie uma versão com texto pesquisável.</div>`);
      S.estado = "AGUARDANDO_VOTO"; pinta(); return;
    }
    if (S.doc.bloco) { $("abaGabarito").hidden = false; reg("ingestão", `Ementa publicada removida do texto (${paginas(S.doc.bloco)}) e guardada para comparação`); }
    $("atualNome").textContent = nome;
    extrair(pr);
  }

  async function extrair(pr) {
    pr = pr || progresso();
    pr.linha("Pedindo a ficha do caso ao Claude (leva de 30 segundos a 2 minutos)");
    let bruta;
    try {
      bruta = await chamar("extracao_ficha", {
        modalidades: N.MODALIDADES.join(", "), resultados: N.RESULTADOS.join(", "), providencias: N.PROVIDENCIAS.join(", "),
        voto_paginado: votoPaginado(),
      }, { signal: pr.signal });
    } catch (e) { pr.fim(); return falha(e, () => extrair()); }
    const ficha = sanear(bruta);
    if (!ficha) { pr.fim(); return falha({ code: "formato", detalhe: " Faltou o processo ou o julgamento." }, () => extrair()); }
    pr.linha("Conferindo cada trecho citado contra a página de origem");
    const problemas = N.conferirFicha(ficha, new N.TextoPaginado(Object.fromEntries(S.doc.paginas.map((p) => [p.numero, p.texto]))));
    const total = [...N.evidencias(ficha)].length;
    const div = problemas.filter((p) => p.status === "pagina_divergente").length, nao = problemas.filter((p) => p.status === "nao_confirmada").length;
    reg("verificação", `${total} evidências: ${total - div - nao} confirmadas, ${div} em outra página, ${nao} não localizadas`);
    S.ficha = ficha; S.problemas = problemas;
    pr.fim();
    const ocs = ficha.ocorrencias;
    bot(`<h3>Ficha do caso</h3>${fichaHTML(ficha)}` +
      (nao ? `<p class="nota"><span class="ev nao">${nao} trecho(s) não localizado(s) no voto</span> estão marcados; o que eles sustentam deve ser conferido.</p>` : "") +
      (S.doc.bloco ? `<p class="nota">O voto já trazia uma ementa (${paginas(S.doc.bloco)}). Ela não foi enviada ao Claude e fica na aba Publicada, para comparar no final.</p>` : ""));
    if (ficha.votacao && ficha.votacao.relator_vencido) bot(`<div class="alerta alta"><b>Relator vencido</b>Os fundamentos devem vir do voto vencedor (art. 6º, III). Confira se ele está no arquivo enviado.</div>`);
    if (!ocs.length) { bot(`<div class="erro"><b>Não encontrei pontos decididos com fundamentação própria.</b>Sem eles não há como seguir. Confira o arquivo ou tente de novo.</div>`); sit("Parado na ficha"); return; }
    S.ctx.unica = ocs.length === 1;
    disparar("CONCLUIR");
    if (S.ctx.unica) { S.ponto = ocs[0]; bot(`<p>Há um único ponto decidido: <b>${esc(ocs[0].titulo)}</b>. Sigo direto para a tese.</p>`); reg("atalho", "Ocorrência única: etapa de escolha do ponto pulada"); propoeTeses(); }
    else pedePonto(`Encontrei ${ocs.length} pontos decididos. Qual deles entra na ementa primeiro?`);
  }

  /** Confere a forma da ficha e as enumerações fechadas; o que não confere vai para nao_identificado. */
  function sanear(f) {
    if (!f || typeof f !== "object" || !f.processo || !f.julgamento) return null;
    const ni = new Set(Array.isArray(f.nao_identificado) ? f.nao_identificado : []);
    const p = f.processo;
    if (!N.MODALIDADES.includes(p.modalidade)) { if (p.modalidade) reg("verificação", `Modalidade fora da lista descartada: ${p.modalidade}`); p.modalidade = null; ni.add("modalidade"); }
    if (f.especie_recursal && !N.MODALIDADES.includes(f.especie_recursal)) f.especie_recursal = null;
    p.exercicios = Array.isArray(p.exercicios) ? p.exercicios.filter((x) => Number.isInteger(x)) : [];
    const j = f.julgamento;
    const filtra = (lista, validos, nome) => (Array.isArray(lista) ? lista : []).filter((x) => { const ok = validos.includes(x); if (!ok) reg("verificação", `${nome} fora da lista descartado: ${x}`); return ok; });
    j.resultado = filtra(j.resultado, N.RESULTADOS, "Resultado");
    j.providencias = filtra(j.providencias, N.PROVIDENCIAS, "Providência");
    j.por_responsavel = (Array.isArray(j.por_responsavel) ? j.por_responsavel : []).filter((r) => r && N.RESULTADOS.includes(r.resultado));
    const ids = new Set();
    f.ocorrencias = (Array.isArray(f.ocorrencias) ? f.ocorrencias : []).filter((o) => o && o.titulo).map((o, i) => {
      let id = String(o.id || `oc${i + 1}`); if (ids.has(id)) id = `oc${i + 1}_${i}`; ids.add(id);
      return { ...o, id, fundamentos: Array.isArray(o.fundamentos) ? o.fundamentos : [], normas: Array.isArray(o.normas) ? o.normas : [],
        precedentes: Array.isArray(o.precedentes) ? o.precedentes : [], responsaveis: Array.isArray(o.responsaveis) ? o.responsaveis : [], consequencias: o.consequencias || {} };
    });
    f.nao_identificado = [...ni];
    return f;
  }

  function evHTML(ev) {
    if (!ev) return "";
    if (ev.status === "confirmada") return `<span class="pg">p. ${ev.pagina_encontrada}</span><span class="ev ok" title="Trecho conferido no voto">✓</span>`;
    if (ev.status === "pagina_divergente") return `<span class="pg">p. ${ev.pagina_encontrada}</span><span class="ev div" title="O Claude indicou outra página">indicada p. ${esc(ev.pagina)}</span>`;
    return `<span class="ev nao" title="O trecho citado não foi encontrado no voto">não confirmado</span>`;
  }
  function contaEv(oc) {
    const evs = [...N.evidencias({ ocorrencias: [oc] })].map(([, e]) => e);
    const ok = evs.filter((e) => e.status !== "nao_confirmada").length;
    return evs.length ? `${ok}/${evs.length}${ok < evs.length ? ' <span class="ev nao">!</span>' : ' <span class="ev ok">✓</span>'}` : "—";
  }
  function fichaHTML(f) {
    const p = f.processo, v = f.votacao, j = f.julgamento;
    const linhas = [
      ["Processo", esc(p.numero || "—") + evHTML(p.evidencia)], ["Modalidade", esc(rotuloMod(p.modalidade)) + (p.tipo ? ", " + esc(rotuloEnum(p.tipo)) : "")],
      ["Órgão julgador", esc(rotuloEnum(p.orgao_julgador) || "—")], ["Relator", esc(p.relator || "—")],
      ["Unidade", esc(p.unidade_jurisdicionada || "—")], ["Exercícios", esc((p.exercicios || []).join(", ") || "—")],
      ["Objeto", esc(p.objeto || "—")],
      ["Votação", v ? (v.unanime ? "unânime" : "por maioria") + (v.relator_vencido ? ", relator vencido" : "") + evHTML(v.evidencia) : "—"],
      ["Resultado", esc(j.resultado.map(rotuloEnum).join(", ") || (p.modalidade === "CONSULTA" ? "consulta conhecida e respondida" : "—")) + evHTML(j.evidencia)],
      ["Providências", esc(j.providencias.map(rotuloEnum).join(", ") || "—")],
    ];
    const ocs = f.ocorrencias.map((o, i) => `<tr><td>${i + 1}</td><td>${esc(o.titulo)}${o.relacionada_ao_merito ? "" : ' <span class="nota">(acessório)</span>'}</td><td>${esc(rotuloEnum(o.consequencias.multa) || "—")}</td><td>${esc(rotuloEnum(o.consequencias.debito) || "—")}</td><td>${contaEv(o)}</td></tr>`).join("");
    return `<table>${linhas.map(([a, b]) => `<tr><th>${a}</th><td>${b}</td></tr>`).join("")}</table>` +
      (ocs ? `<table class="lista-oc"><tr><th>#</th><th style="width:auto">Ponto decidido</th><th>Multa</th><th>Débito</th><th>Trechos</th></tr>${ocs}</table>` : "") +
      (f.nao_identificado.length ? `<p class="nota">Não identificado no voto: ${esc(f.nao_identificado.join(", "))}.</p>` : "");
  }

  // ------------------------------------------------------ 3. ponto
  const restantes = () => S.ficha.ocorrencias.filter((o) => !S.itens.some((x) => x.oc.id === o.id));
  function pedePonto(txt) {
    const r = restantes();
    sit("Aguardando o ponto"); dica("Digite o número do ponto ou pergunte sobre o caso");
    S.tela = "Lista de pontos decididos: " + r.map((o, i) => `${i + 1}. ${o.titulo}`).join("; ");
    bot(`<p>${esc(txt)}</p>` + opcoes(r.map((o) => {
      const ev = o.fundamentos[0] && o.fundamentos[0].evidencia;
      return `<b>${esc(o.titulo)}</b><small>${esc(o.resumo || "")}${ev && ev.pagina_encontrada ? `<span class="pg">p. ${ev.pagina_encontrada}</span>` : ""}${o.relacionada_ao_merito ? "" : " · acessório ao mérito"}</small>`;
    }), (k) => { S.ponto = r[k]; reg("escolha", "Ponto: " + S.ponto.titulo); disparar("ESCOLHER"); propoeTeses(); }) +
      `<div class="chips"><button class="chip">Qual destes pontos sustenta o resultado do julgamento?</button></div>`);
  }

  // ------------------------------------------------------- 4. tese
  function termosProibidos() {
    const p = S.ficha.processo;
    return [...N.nomesDePessoas(S.ficha), p.unidade_jurisdicionada, p.numero].filter(Boolean);
  }
  async function propoeTeses(orientacao) {
    sit("Propondo teses"); dica("Propondo teses…");
    const pr = progresso();
    pr.linha("Pedindo ao Claude quatro redações, da regra geral à mais completa");
    const oc = S.ponto;
    const normas = [...oc.normas, ...oc.precedentes].map((n) => n.citacao).filter(Boolean);
    let r;
    try {
      r = await chamar("propor_teses", {
        ponto: semEvidencias({ titulo: oc.titulo, resumo: oc.resumo, fundamentos: oc.fundamentos, normas: oc.normas, precedentes: oc.precedentes, consequencias: oc.consequencias }),
        normas_permitidas: normas.length ? normas.join("\n") : "(nenhuma: não cite normas nem precedentes)",
        termos_proibidos: termosProibidos().join("\n") || "(nenhum)",
        orientacao: orientacao ? `- Orientação do usuário para esta nova rodada: ${orientacao}\n- As redações anteriores, que devem ser diferentes destas: ${(S.teses || []).map((t) => t.texto).join(" | ")}` : "",
      }, { signal: pr.signal, cache: orientacao ? false : undefined });
    } catch (e) { pr.fim(); return falha(e, () => propoeTeses(orientacao)); }
    if (!r || !Array.isArray(r.teses) && !r.sem_tese) { pr.fim(); return falha({ code: "formato" }, () => propoeTeses(orientacao)); }
    pr.linha("Barrando nomes do caso, valores e normas que não estão no voto");
    S.teses = (r.teses || []).filter((t) => t && t.texto).map((t) => ({ ...t, problemas: N.verificarTese(t.texto, S.ficha, textoVoto()) }));
    S.semTese = r.sem_tese ? r.motivo || "O ponto não firma entendimento aplicável a outros casos." : null;
    const barradas = S.teses.filter((t) => t.problemas.length).length;
    reg("verificação", `${S.teses.length} teses; ${barradas} com problema apontado pelo verificador`);
    pr.fim();
    disparar("CONCLUIR");
    mostrarTeses();
  }
  function mostrarTeses() {
    sit("Aguardando a tese"); dica("Digite o número da tese, \"voltar\" ou pergunte sobre o caso");
    const ts = S.teses;
    const lista = ts.map((t) => `${esc(t.texto)}<span class="mais">Nível ${esc(t.nivel)}${t.acrescentou ? " · " + esc(t.acrescentou) : ""}</span>` +
      (t.problemas.length ? `<span class="aviso-op">Atenção: ${esc(t.problemas.join("; "))}</span>` : ""));
    lista.push(`<b>Dispensar a tese deste ponto</b><small>Portaria Normativa TC nº 322/2026, art. 8º, parágrafo único</small>`);
    lista.push(`<b>Gerar outras redações</b><small>Você pode dar uma orientação, como "mais curta" ou "sem citar a LRF".</small>`);
    S.tela = "Teses propostas: " + ts.map((t, i) => `${i + 1}. ${t.texto}`).join(" ");
    bot((S.semTese ? `<div class="alerta"><b>O Claude sugere dispensar a tese</b>${esc(S.semTese)}</div>` : "") +
      `<p>Redações para o ponto <b>${esc(S.ponto.titulo)}</b>, da mais geral à mais completa:</p>` +
      opcoes(lista, (k) => {
        if (k < ts.length) { S.teseAtual = ts[k].texto; reg("escolha", `Tese ${k + 1} (nível ${ts[k].nivel})`); disparar("ESCOLHER"); buscaTermos(); }
        else if (k === ts.length) { S.teseAtual = null; reg("escolha", "Tese dispensada"); disparar("DISPENSAR_TESE"); buscaTermos(); }
        else { S.aguardandoOrientacao = true; dica("Escreva a orientação, ou \"seguir\" para gerar sem orientação"); bot(`<p>Qual orientação devo seguir? Escreva abaixo, ou "seguir" para gerar sem orientação.</p>`); }
      }) + `<div class="chips"><button class="chip">Por que a tese 4 acrescenta um elemento que as outras não têm?</button></div>`);
  }

  // ------------------------------------------------------ 5. termo
  async function buscaTermos() {
    sit("Sugerindo termos"); dica("Sugerindo termos…");
    const pr = progresso();
    pr.linha("Pedindo ao Claude termos de indexação para o ponto");
    let r;
    try {
      r = await chamar("sugerir_termos_sem_tesauro", { ponto: `${S.ponto.titulo}: ${S.ponto.resumo || ""}`, tese: S.teseAtual || "(tese dispensada)" }, { signal: pr.signal });
    } catch (e) { pr.fim(); return falha(e, () => buscaTermos()); }
    const termos = (r && Array.isArray(r.termos) ? r.termos : []).filter((t) => t && t.rotulo).slice(0, 5)
      .map((t) => ({ rotulo: String(t.rotulo).trim(), generico: String(t.generico || "").trim(), justificativa: String(t.justificativa || "") }));
    const verbos = termos.filter((t) => N.verificar(`EMENTA: CONSULTA. ${t.rotulo.toUpperCase()}.`).some((a) => a.codigo === "E18"));
    reg("verificação", `${termos.length} termos sugeridos, todos marcados fora do tesauro${verbos.length ? `; ${verbos.length} com possível verbo` : ""}`);
    pr.fim();
    disparar("CONCLUIR");
    S.termos = termos;
    mostrarTermos();
  }
  function mostrarTermos() {
    sit("Aguardando o termo"); dica("Digite o número do termo, \"voltar\" ou pergunte sobre o caso");
    const ts = S.termos;
    S.tela = "Termos sugeridos: " + ts.map((t, i) => `${i + 1}. ${t.rotulo}`).join("; ");
    bot(`<p>Termos sugeridos para este ponto. Ao escolher, você confirma o uso como termo fora do tesauro (art. 4º, III).</p>` +
      opcoes(ts.map((t) => `<b>${esc(t.rotulo)}</b><span class="fora">fora do tesauro</span><small>Termo genérico: ${esc(t.generico || "—")} · ${esc(t.justificativa)}</small>`)
        .concat([`<b>Seguir sem termo para este ponto</b><small>O cabeçalho fica só com a modalidade, os termos dos outros pontos e o resultado.</small>`]), (k) => {
        const termo = k < ts.length ? ts[k] : null;
        S.itens.push({ oc: S.ponto, tese: S.teseAtual, termo });
        S.novo = S.ponto.id;
        reg("escolha", termo ? `Termo: ${termo.rotulo} (fora do tesauro, confirmado)` : "Sem termo");
        disparar("ESCOLHER"); monta();
      }) + `<p class="nota">A base do Tesauro de Contas Nacional ainda não está carregada nesta demonstração: os termos são sugestões do Claude e precisam ser conferidos no TCN. Na versão definitiva o Claude só escolhe entre termos que existem na base.</p>`);
  }

  // ----------------------------------------------------- 6. montagem
  async function monta() {
    sit("Montando a ementa"); dica("Montando a ementa…");
    const pr = progresso();
    pr.linha("Pedindo ao Claude o caso em exame e as razões de decidir, a partir da ficha");
    let r;
    try {
      r = await chamar("redacao_caso_razoes", { ficha: semEvidencias(S.ficha), pontos: S.itens.map((x) => x.oc.id) }, { signal: pr.signal });
    } catch (e) { pr.fim(); return falha(e, () => monta()); }
    if (!r || !r.caso_em_exame || !Array.isArray(r.razoes)) { pr.fim(); return falha({ code: "formato" }, () => monta()); }
    pr.linha("Montando cabeçalho, dispositivo, numeração e títulos por código");
    const ordem = new Map(S.itens.map((x, i) => [x.oc.id, i]));
    const razoes = r.razoes.filter((x) => x && x.texto).map((x) => ({ texto: String(x.texto).trim(), oc: x.ocorrencia_id }))
      .sort((a, b) => (ordem.get(a.oc) ?? 99) - (ordem.get(b.oc) ?? 99));
    const disp = N.montarDispositivo(S.ficha);
    S.ementa = {
      cab: N.montarCabecalho(S.ficha, S.itens.filter((x) => x.termo).map((x) => x.termo)),
      caso: [].concat(r.caso_em_exame).map(String).filter((x) => x.trim()),
      razoes, disp,
      teses: S.itens.filter((x) => x.tese).map((x) => ({ texto: x.tese, oc: x.oc.id })),
    };
    reg("código", "Cabeçalho, dispositivo e numeração montados sem modelo" + (disp.a_definir ? "; dispositivo A DEFINIR para esta modalidade" : ""));
    pr.fim();
    aba = "ementa";
    S.ctx.restantes = restantes().length;
    const d = disparar("CONCLUIR");
    if (d === "VERIFICANDO") {
      bot(`<p>A ementa está montada no painel ao lado${S.ctx.unica ? "" : " com todos os pontos"}. Vou fazer a verificação final.</p>`);
      return verifica();
    }
    sit(`Ementa com ${S.itens.length} ponto(s)`); dica("Responda 1 ou 2, ou pergunte sobre o caso");
    S.tela = "Pergunta: adicionar outro ponto?";
    bot(`<p>A ementa foi atualizada no painel ao lado, com o trecho novo destacado. Deseja adicionar outro ponto?</p>` +
      opcoes([`<b>Sim, adicionar outro ponto</b><small>Restam ${S.ctx.restantes}. A ficha é reaproveitada.</small>`, `<b>Não, concluir a ementa</b><small>Segue para a verificação final.</small>`], (k) => {
        reg("escolha", k ? "Concluir" : "Adicionar outro ponto");
        if (k === 0) { disparar("ADICIONAR_OCORRENCIA"); pedePonto("Qual ponto entra agora?"); } else { disparar("ENCERRAR"); verifica(); }
      }));
  }

  function textoEmenta() {
    const E = S.ementa;
    return N.montarEmenta({ cabecalho: E.cab, caso: E.caso, razoes: E.razoes.map((r) => r.texto), dispositivo: E.disp.texto, teses: E.teses.map((t) => t.texto) });
  }
  const termosCabecalho = () => S.itens.filter((x) => x.termo).map((x) => ({ rotulo: x.termo.rotulo, fora_do_tesauro: true, confirmado_pelo_usuario: true }));

  // ---------------------------------------------------------- 7. alerta
  const NOMES_REGRAS = {
    E02: "Cabeçalho em maiúsculas, separado por pontos", E04: "Seções e títulos na ordem da Portaria",
    E05: "Numeração contínua", E06: "Caso em exame começa pelo objeto", E07: "Um fundamento por item",
    E09: "Dispositivo igual ao resultado da ficha", E10: "Teses sem nomes, valores ou número de processo",
    E11: "Teses sem marcas de caso concreto", E12: "Normas da ementa localizadas no voto", E13: "Valores e datas localizados no voto",
    E18: "Cabeçalho só com termos nominais (art. 4º, II)", E20: "Sem nomes de pessoas naturais (art. 10, § 2º)",
  };
  async function verifica() {
    S.novo = null;
    sit("Verificando"); dica("Verificando…");
    const pr = progresso();
    pr.linha("Aplicando as regras da Portaria Normativa TC nº 322/2026 (E01 a E21)");
    const texto = textoEmenta();
    const lint = N.verificar(texto, { ficha: S.ficha, textoVoto: textoVoto(), termosCabecalho: termosCabecalho() });
    const alertas = lint.map((a) => ({ gravidade: a.gravidade, titulo: `${a.codigo} · ${a.mensagem}`, detalhe: a.referencia }));
    if (S.ementa.disp.a_definir) alertas.unshift({ gravidade: "alta", titulo: "Dispositivo sem expressão padronizada", detalhe: "A tabela de expressões para esta modalidade ainda não foi definida (pendência P1). Redija o dispositivo a partir da parte dispositiva do voto." });
    for (const x of S.itens) for (const [c, ev] of N.evidencias({ ocorrencias: [x.oc] })) if (ev.status === "nao_confirmada") alertas.push({ gravidade: "media", titulo: `Trecho não localizado no voto (${x.oc.titulo})`, detalhe: `${caminhoLegivel(c)}: "${String(ev.trecho).slice(0, 140)}"` });
    if (S.ficha.votacao && S.ficha.votacao.relator_vencido) alertas.unshift({ gravidade: "alta", titulo: "Relator vencido", detalhe: "Confira se os fundamentos vieram do voto vencedor (art. 6º, III)." });
    reg("verificação", `Linter: ${lint.length} ponto(s)`);

    pr.linha("Pedindo ao Claude a comparação entre fundamentação e parte dispositiva");
    let modeloOk = true;
    try {
      const r = await chamar("verificacao_final", {
        voto_paginado: votoPaginado(),
        pontos: S.itens.map((x) => semEvidencias({ id: x.oc.id, titulo: x.oc.titulo, resumo: x.oc.resumo, consequencias: x.oc.consequencias })),
        teses: S.ementa.teses.map((t, i) => ({ tese: i + 1, ocorrencia: t.oc, texto: t.texto })),
      }, { signal: pr.signal });
      pr.linha("Conferindo no voto cada trecho que o Claude citou");
      const tp = new N.TextoPaginado(Object.fromEntries(S.doc.paginas.map((p) => [p.numero, p.texto])));
      const existe = (t, p) => t && N.conferirTrecho(String(t), Number(p) || 0, tp).status !== "nao_confirmada";
      let descartadas = 0;
      for (const d of (r && r.divergencias) || []) {
        if (existe(d.trecho_a, d.pagina_a) && existe(d.trecho_b, d.pagina_b)) alertas.unshift({ gravidade: "alta", titulo: d.descricao, detalhe: `"${d.trecho_a}" (p. ${d.pagina_a}) × "${d.trecho_b}" (p. ${d.pagina_b})` });
        else descartadas++;
      }
      for (const a of (r && r.alcance_teses) || []) {
        if (a && (a.situacao === "amplia" || a.situacao === "restringe")) alertas.push({ gravidade: "media", titulo: `A tese ${a.tese} ${a.situacao} o que foi decidido`, detalhe: a.explicacao + (existe(a.trecho, a.pagina) ? ` (Voto, p. ${a.pagina})` : "") });
      }
      reg("verificação", `Comparação pelo Claude: ${((r && r.divergencias) || []).length - descartadas} divergência(s) com trechos conferidos` + (descartadas ? `, ${descartadas} descartada(s) por trecho não localizado` : ""));
    } catch (e) {
      if (e && e.code === "descartado") return;
      modeloOk = false;
      if (e && e.code === "cancelled") reg("aviso", "Comparação pelo Claude interrompida");
    }
    pr.fim();
    S.alertas = alertas;
    disparar("CONCLUIR");
    const altas = alertas.filter((a) => a.gravidade === "alta").length;
    S.ciencia = altas === 0;
    sit(`Ementa concluída, ${S.itens.length} ponto(s)`); dica("Pergunte sobre o caso ou comece uma nova ementa");
    const codigos = new Set(lint.map((a) => a.codigo));
    const atendidas = Object.entries(NOMES_REGRAS).filter(([c]) => !codigos.has(c)).map(([, n]) => `<li>${n}</li>`).join("");
    const d = bot(`<h3>Ementa concluída</h3><p>${alertas.length ? `Confira antes de usar: ${alertas.length} ponto(s).` : "Nenhum ponto a conferir."}</p>` +
      alertas.map((a) => `<div class="alerta ${a.gravidade === "alta" ? "alta" : ""}"><b>${esc(a.titulo)}</b>${a.detalhe ? esc(a.detalhe) : ""}<small>gravidade ${a.gravidade === "media" ? "média" : a.gravidade}</small></div>`).join("") +
      (modeloOk ? "" : `<p class="nota">A comparação entre fundamentação e parte dispositiva pelo Claude não pôde ser feita; as regras por código foram aplicadas.</p>`) +
      `<div class="passou">Regras atendidas<ul>${atendidas}</ul></div>` +
      (altas ? `<label class="ciencia"><input type="checkbox" id="ciente"> Li e conferi os ${altas} ponto(s) de gravidade alta.</label>` : "") +
      (S.doc.bloco ? `<p class="nota">O voto trazia a ementa publicada: compare na aba <b>Publicada</b> do painel.</p>` : "") +
      `<div class="acoes" style="margin-top:18px"><button class="btn" id="copiaFinal" ${altas ? "disabled" : ""}>Copiar a ementa final</button><button class="btn sec" id="exportar">Exportar a conversa</button><button class="btn sec" id="novaFinal">Começar nova ementa</button></div>`);
    const ciente = d.querySelector("#ciente");
    if (ciente) ciente.onchange = () => { S.ciencia = ciente.checked; d.querySelector("#copiaFinal").disabled = !ciente.checked; if (ciente.checked) reg("escolha", "Ciência dos pontos de gravidade alta"); };
    d.querySelector("#copiaFinal").onclick = (e) => copia(e.target);
    d.querySelector("#exportar").onclick = exporta;
    d.querySelector("#novaFinal").onclick = inicio;
    aba = "ementa"; painel();
  }

  // ----------------------------------------------- conversa sobre o caso
  function trechosRelevantes(q, n = 3) {
    const tok = new Set(N.normalizarParaBusca(q).split(" ").filter((t) => t.length > 3));
    return S.doc.paginas.map((p) => {
      const k = N.normalizarParaBusca(p.texto);
      return [p, [...tok].reduce((s, t) => s + (k.split(t).length - 1), 0)];
    }).sort((a, b) => b[1] - a[1]).slice(0, n).sort((a, b) => a[0].numero - b[0].numero)
      .map(([p]) => `[[p. ${p.numero}]]\n${p.texto.slice(0, 7000)}`).join("\n\n");
  }
  async function perguntar(q) {
    eu(q);
    if (!S.ficha || /^(EXTRAINDO|PROPONDO_TESES|BUSCANDO_TERMOS|MONTANDO|VERIFICANDO)$/.test(S.estado)) {
      bot(`<p>${S.ficha ? "Aguarde a etapa atual terminar para perguntar." : "Envie o voto primeiro; depois posso responder perguntas sobre ele."}</p>`); return;
    }
    reg("pergunta", q.slice(0, 80));
    S.eventos.push({ quando: new Date().toISOString(), etapa: S.estado, tipo: "pergunta", texto: q });
    const d = bot(`<p class="resp nota">Pensando…</p>`), alvo = d.querySelector(".resp");
    try {
      const r = await chamar("conversa", {
        etapa: PASSOS[PASSO_DO_ESTADO[S.estado]] || "Ementa", conteudo_em_tela: S.tela || "(nada)",
        ficha: semEvidencias(S.ficha), trechos: trechosRelevantes(q), pergunta: q,
      }, { json: false, cache: false, onText: ({ text }) => { alvo.className = "resp"; alvo.textContent = text; rola(); } });
      alvo.className = "resp"; alvo.textContent = r.text;
      d.querySelector("div").insertAdjacentHTML("beforeend", `<p class="nota">A etapa continua aberta. Escolha uma opção quando quiser.</p>`);
    } catch (e) {
      if (e && e.code === "descartado") return;
      alvo.className = "resp"; alvo.textContent = (e && e.text) || "";
      d.querySelector("div").insertAdjacentHTML("beforeend", `<div class="erro"><b>${esc(ERROS[e && e.code] || "Falha na chamada ao Claude.")}</b></div>`);
    }
  }

  function voltar() {
    if (S.estado === "AGUARDANDO_TESE" && !S.ctx.unica) { pend = null; disparar("VOLTAR"); reg("escolha", "Voltar ao ponto"); S.ponto = null; pedePonto("Qual ponto, então?"); return; }
    if (S.estado === "AGUARDANDO_TERMO") { pend = null; disparar("VOLTAR"); reg("escolha", "Voltar à tese"); mostrarTeses(); return; }
    bot(`<p>${S.estado === "AGUARDANDO_TESE" ? "Este voto tem um único ponto. Para trocar o voto, use Nova ementa." : "Não há etapa anterior para voltar daqui."}</p>`);
  }

  $("form").onsubmit = (e) => {
    e.preventDefault();
    const v = $("txt").value.trim(); if (!v) return; $("txt").value = "";
    const k = N.normalizar(v).replace(/[.!]+$/, "");
    if (S.aguardandoOrientacao) {
      S.aguardandoOrientacao = false; eu(v);
      const orient = k === "seguir" ? "redações diferentes das anteriores" : v;
      reg("escolha", "Gerar outras teses: " + orient.slice(0, 60)); disparar("PEDIR_NOVAS_TESES"); propoeTeses(orient); return;
    }
    if (S.estado === "AGUARDANDO_VOTO") {
      eu(v);
      if (v.length > 200 && $("sigilo") && $("sigilo").checked) { col.lastChild.remove(); receber(v, "Texto colado"); }
      else bot(`<p>Primeiro envie o voto pelos botões acima${v.length > 200 ? " (e marque a confirmação de que ele é fictício ou publicado)" : ""}, ou use o voto fictício de exemplo.</p>`);
      return;
    }
    if (k === "voltar") { eu(v); voltar(); return; }
    if (S.estado === "AGUARDANDO_MAIS_OCORRENCIA" && pend) {
      if (["sim", "s", "adicionar"].includes(k)) { eu(v); escolhe(0); return; }
      if (["nao", "não", "n", "concluir", "encerrar"].includes(k)) { eu(v); escolhe(1); return; }
    }
    if (S.estado === "AGUARDANDO_TESE" && pend && /^dispensar( a)? tese$|^dispensar$/.test(k)) { eu(v); escolhe(S.teses.length); return; }
    const m = k.match(/^(?:op[cç][aã]o|alternativa|n[uú]mero|item)?\s*(\d{1,2})\s*[.)]?$/);
    if (m && pend) { eu(v); if (!escolhe(Number(m[1]) - 1)) bot(`<p>Não há opção ${esc(m[1])}. Escolha de 1 a ${pend.n}.</p>`); return; }
    perguntar(v);
  };

  // --------------------------------------------------------- painel
  function abre(a) { aba = a; painel(); }
  function painel() {
    document.querySelectorAll(".abas [data-aba]").forEach((b) => b.setAttribute("aria-selected", b.dataset.aba === aba));
    const c = $("conteudo");
    if (aba === "ficha") { c.innerHTML = S.ficha ? fichaHTML(S.ficha) : `<p class="nota">A ficha aparece aqui depois da leitura do voto.</p>`; return; }
    if (aba === "registro") {
      c.innerHTML = S.reg.length ? `<div class="reg">${S.reg.map((r) => `<div class="${r[1] === "escolha" ? "escolha" : ""}"><time>${r[0]}</time><em>${esc(r[1])}</em><span>${esc(r[2])}</span></div>`).join("")}</div><p class="nota" style="margin-top:12px">Cada chamada ao Claude, verificação e escolha fica registrada com a versão do prompt.</p>` : `<p class="nota">Nenhum evento ainda.</p>`;
      return;
    }
    if (aba === "gabarito") {
      if (!S.doc || !S.doc.bloco) { c.innerHTML = `<p class="nota">O voto enviado não trazia ementa.</p>`; return; }
      const lint = N.verificar(S.doc.bloco.texto, { textoVoto: textoVoto() });
      c.innerHTML = `<p class="nota">Ementa que já vinha no inteiro teor (${paginas(S.doc.bloco)}). Não foi enviada ao Claude.</p>` +
        `<div class="folha" style="white-space:pre-wrap">${esc(S.doc.bloco.texto)}</div>` +
        `<p class="nota" style="margin-top:14px">Pelas mesmas regras: ${lint.length ? lint.length + " ponto(s) — " + esc(lint.map((a) => a.codigo).join(", ")) : "nenhum ponto a conferir"}.</p>`;
      return;
    }
    if (!S.ementa) { c.innerHTML = `<div class="folha"><p class="falta">A ementa é montada aqui à medida que você escolhe ponto, tese e termo. Seções: cabeçalho, caso em exame, razões de decidir, dispositivo e tese de julgamento.</p></div>`; return; }
    const E = S.ementa, m = (oc) => (oc === S.novo ? ' class="novo"' : "");
    let n = 1;
    c.innerHTML = `<div class="folha"><p class="cab">${esc(E.cab)}</p><h4>I. CASO EM EXAME</h4>${E.caso.map((x) => `<p>${n++}. ${esc(x)}</p>`).join("")}
      <h4>II. RAZÕES DE DECIDIR</h4>${E.razoes.map((r) => `<p>${n++}. <span${m(r.oc)}>${esc(r.texto)}</span></p>`).join("")}
      <h4>III. DISPOSITIVO</h4><p>${n++}. <span${E.disp.a_definir ? ' class="ad"' : ""}>${esc(E.disp.texto)}</span></p>
      ${E.teses.length ? `<h4>IV. TESE DE JULGAMENTO</h4>` + E.teses.map((t) => `<p>${n++}. <span${m(t.oc)}>${esc(t.texto)}</span></p>`).join("") : `<p class="falta">Tese de julgamento dispensada (art. 8º, parágrafo único).</p>`}</div>`;
  }
  document.querySelectorAll(".abas [data-aba]").forEach((b) => (b.onclick = () => abre(b.dataset.aba)));

  function copia(b) {
    const original = b.textContent;
    const aviso = (t) => { b.textContent = t; setTimeout(() => (b.textContent = original), 1600); };
    if (!S.ementa) return aviso("Nada a copiar");
    if (!S.ciencia) return aviso("Marque a ciência dos alertas");
    const t = textoEmenta();
    (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(() => { reg("escolha", "Ementa copiada"); aviso("Ementa copiada"); })
      .catch(() => aviso("Não foi possível copiar"));
  }
  async function exporta() {
    const t = (S.ementa ? textoEmenta() : "(ementa não montada)") +
      "\n\n--- PONTOS A CONFERIR ---\n" + (S.alertas.map((a) => `[${a.gravidade}] ${a.titulo}${a.detalhe ? " — " + a.detalhe : ""}`).join("\n") || "nenhum") +
      "\n\n--- REGISTRO ---\n" + S.reg.map((r) => r.join("  ")).join("\n") +
      "\n\n--- EVENTOS ---\n" + JSON.stringify(S.eventos, null, 1) +
      "\n\n--- FICHA ---\n" + JSON.stringify(S.ficha, null, 1);
    try {
      if (!downloads) throw 0;
      await downloads.save({ filename: "ementa-conversa.txt", data: new Blob([t], { type: "text/plain" }) });
      reg("escolha", "Conversa exportada");
    } catch (e) { bot(`<p>O download não está disponível aqui. Use "Copiar a ementa final".</p>`); }
  }

  $("copiar").onclick = (e) => copia(e.target);
  $("nova").onclick = () => { if (S.ctl) S.ctl.abort(); inicio(); };
  $("arq").onchange = (e) => { const f = e.target.files[0]; if (f) receber(f, f.name); e.target.value = ""; };
  $("tema").onclick = (e) => { const d = document.documentElement, n = d.dataset.theme === "dark" ? "light" : "dark"; d.dataset.theme = n; e.target.textContent = n === "dark" ? "Claro" : "Escuro"; };
  let f = 15.5;
  $("maior").onclick = () => { f = Math.min(19, f + 1); document.documentElement.style.fontSize = f + "px"; };
  $("menor").onclick = () => { f = Math.max(13, f - 1); document.documentElement.style.fontSize = f + "px"; };
  $("abrePainel").onclick = () => $("painel").classList.add("aberto");
  $("fechaPainel").onclick = () => $("painel").classList.remove("aberto");
  inicio();
})();
