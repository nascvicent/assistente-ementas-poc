/* Avaliação por código (documento 01, seção 9): compara uma ementa com outra
 * (a publicada, quando o inteiro teor a traz) e resume o linter de cada uma.
 * Roda no navegador (window.Avaliacao) e no Node (module.exports).
 */
(function (raiz) {
  "use strict";
  const N = typeof module !== "undefined" && module.exports ? require("./nucleo.js") : raiz.Nucleo;

  const palavras = (t) => N.normalizarParaBusca(t || "").split(" ").filter(Boolean);

  /** Semelhança por palavras: 1 − distância de edição / tamanho da maior (0 a 1). */
  function semelhanca(a, b) {
    const x = palavras(a), y = palavras(b);
    if (!x.length && !y.length) return 1;
    if (!x.length || !y.length) return 0;
    let ant = Array.from({ length: y.length + 1 }, (_, j) => j);
    for (let i = 1; i <= x.length; i++) {
      const cur = [i];
      for (let j = 1; j <= y.length; j++) cur[j] = Math.min(ant[j] + 1, cur[j - 1] + 1, ant[j - 1] + (x[i - 1] === y[j - 1] ? 0 : 1));
      ant = cur;
    }
    return 1 - ant[y.length] / Math.max(x.length, y.length);
  }

  function partes(texto) {
    const e = N.analisar(texto || "");
    const sec = (t) => { const s = e.secao(t); return s ? e.textoSecao(s) : ""; };
    const tese = e.secao(N.CONFIG.titulosTeseAceitos);
    return {
      segmentos: e.segmentos.map((s) => s.toUpperCase()),
      cabecalho: e.cabecalho,
      caso: sec("CASO EM EXAME"),
      razoes: sec("RAZÕES DE DECIDIR"),
      dispositivo: sec("DISPOSITIVO"),
      teses: tese ? tese.itens.map((i) => i.texto) : [],
      itensRazoes: (e.secao("RAZÕES DE DECIDIR") || { itens: [] }).itens.length,
    };
  }

  function resumoLinter(texto, ctx) {
    const a = N.verificar(texto, ctx || {});
    const por = { alta: 0, media: 0, baixa: 0 };
    for (const x of a) por[x.gravidade]++;
    return { total: a.length, ...por, codigos: [...new Set(a.map((x) => x.codigo))].sort(),
      normasSemSuporte: a.filter((x) => x.codigo === "E12").map((x) => x.referencia),
      valoresSemSuporte: a.filter((x) => x.codigo === "E13").map((x) => x.referencia) };
  }

  /** Compara `gerada` com `referencia`. ctx (opcional) é o contexto do linter. */
  function comparar(gerada, referencia, ctx) {
    const g = partes(gerada), r = partes(referencia);
    const segG = new Set(g.segmentos), segR = new Set(r.segmentos);
    const resG = [...N.resultadosNoTexto(N.normalizar(g.dispositivo, true))].sort();
    const resR = [...N.resultadosNoTexto(N.normalizar(r.dispositivo, true))].sort();
    const secoes = {
      cabecalho: semelhanca(g.cabecalho, r.cabecalho),
      caso: semelhanca(g.caso, r.caso),
      razoes: semelhanca(g.razoes, r.razoes),
      dispositivo: semelhanca(g.dispositivo, r.dispositivo),
      teses: semelhanca(g.teses.join(" "), r.teses.join(" ")),
    };
    return {
      geral: semelhanca(gerada, referencia),
      secoes,
      termos: {
        comuns: [...segG].filter((s) => segR.has(s)),
        soGerada: [...segG].filter((s) => !segR.has(s)),
        soReferencia: [...segR].filter((s) => !segG.has(s)),
      },
      dispositivo: { gerada: resG, referencia: resR, mesmoResultado: resG.length > 0 && resG.join() === resR.join() },
      quantidades: { razoesGerada: g.itensRazoes, razoesReferencia: r.itensRazoes, tesesGerada: g.teses.length, tesesReferencia: r.teses.length },
      linterGerada: resumoLinter(gerada, ctx),
      linterReferencia: resumoLinter(referencia, ctx),
    };
  }

  /** Separa a ementa do bloco "PARA CONFERIR" na saída livre do prompt único. */
  function extrairDoTextoLivre(texto) {
    let t = String(texto || "").replace(/\r\n/g, "\n").replace(/\*\*/g, "").replace(/^#+\s*/gm, "").replace(/^```\w*$/gm, "");
    const ini = t.search(/EMENTA\s*:/);
    if (ini > 0) t = t.slice(ini);
    const m = t.search(/^\s*PARA CONFERIR\b/im);
    const ementa = (m >= 0 ? t.slice(0, m) : t).trim();
    const paraConferir = m >= 0 ? t.slice(m).replace(/^\s*PARA CONFERIR\s*:?/i, "").trim() : "";
    return { ementa: ementa.replace(/^EMENTA\s*:\s*/, "EMENTA: "), paraConferir };
  }

  const RE_TITULO = /^\s*(I{1,3}|IV|V|VI)\s*[.\-–]\s*[A-ZÀ-Ý][A-ZÀ-Ý ]+?\s*:?\s*$/;
  const RE_RODAPE = /^\s*(Refer[êe]ncias normativas|Precedentes citados|Dispositivos relevantes citados|Jurisprud[êe]ncia relevante citada)\s*:/i;
  const RE_NUM = /^\s*\d+\s*[.)]\s+/;

  /** Divide "1. A. 2. B." nos itens, procurando só o próximo número esperado (não quebra em "art. 75."). */
  function dividirEmItens(texto) {
    const t = texto.trim();
    if (!/^1\.\s/.test(t)) return [t];
    const itens = []; let ini = 0, esperado = 2;
    for (;;) {
      const re = new RegExp(`(^|\\s)${esperado}\\.\\s`, "g"); re.lastIndex = ini + 2;
      const m = re.exec(t);
      if (!m) break;
      itens.push(t.slice(ini, m.index).trim()); ini = m.index + m[1].length; esperado++;
    }
    itens.push(t.slice(ini).trim());
    return itens.map((x) => x.replace(/^\d+\.\s+/, "").trim()).filter(Boolean);
  }

  /** Põe uma ementa de texto livre no formato publicado, para medir conteúdo e não formato.
   *  Devolve o texto normalizado e a lista de ajustes feitos (que é, ela própria, uma medida). */
  function normalizarFormato(texto) {
    const ajustes = [];
    const linhas = String(texto || "").replace(/\r\n/g, "\n").split("\n").map((l) => l.replace(/\s+$/, ""));
    const iTit = linhas.findIndex((l) => RE_TITULO.test(l));
    if (iTit < 0) return { texto: String(texto || "").trim(), ajustes: ["seções não reconhecidas"] };
    let cab = linhas.slice(0, iTit).join(" ").replace(/\s+/g, " ").trim().replace(/^\[(.*)\]$/, "$1");
    if (!/^EMENTA:/.test(cab)) { ajustes.push("cabeçalho sem \u201cEMENTA:\u201d"); cab = "EMENTA: " + cab.replace(/^EMENTA\s*:?\s*/i, ""); }
    const secoes = [], rodape = [];
    let atual = null;
    for (const l of linhas.slice(iTit)) {
      if (RE_TITULO.test(l)) { atual = { titulo: l.trim().replace(/\s*:$/, ""), linhas: [] }; secoes.push(atual); continue; }
      if (RE_RODAPE.test(l)) { rodape.push(l.trim()); if (/^\s*(Dispositivos|Jurisprud)/i.test(l) && !ajustes.includes("referências com títulos do CNJ")) ajustes.push("referências com títulos do CNJ"); continue; }
      if (l.trim()) atual.linhas.push(l.trim());
    }
    let n = 1, renumerou = false;
    const saida = [cab];
    for (const s of secoes) {
      saida.push(s.titulo);
      let itens;
      const corpo = s.linhas.join(" ");
      if (/^[\u201c"]/.test(corpo)) {
        itens = dividirEmItens(corpo.replace(/^[\u201c"]\s*/, "").replace(/\s*[\u201d"]\s*$/, ""));
        ajustes.push("teses em bloco entre aspas");
      } else if (s.linhas.length && !s.linhas.some((l) => RE_NUM.test(l))) {
        itens = s.linhas; ajustes.push(`itens sem numeração (${s.titulo})`);
      } else {
        itens = [];
        for (const l of s.linhas) { if (RE_NUM.test(l) || !itens.length) itens.push(l); else itens[itens.length - 1] += " " + l; }
        itens = itens.map((x) => { const m = x.match(/^\s*(\d+)\s*[.)]\s+/); if (m && Number(m[1]) !== n + itens.indexOf(x)) renumerou = true; return x.replace(RE_NUM, ""); });
      }
      for (const it of itens) saida.push(`${n++}. ${it}`);
    }
    if (renumerou) ajustes.push("numeração refeita em sequência contínua");
    if (rodape.length) saida.push("", ...rodape);
    return { texto: saida.join("\n"), ajustes };
  }

  const api = { semelhanca, partes, comparar, resumoLinter, extrairDoTextoLivre, normalizarFormato, dividirEmItens };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Avaliacao = api;
})(typeof self !== "undefined" ? self : this);
