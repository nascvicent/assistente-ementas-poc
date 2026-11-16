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

  const api = { semelhanca, partes, comparar, resumoLinter, extrairDoTextoLivre };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Avaliacao = api;
})(typeof self !== "undefined" ? self : this);
