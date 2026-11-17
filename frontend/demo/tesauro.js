/* Índice local do Tesauro de Contas Nacional — porte de backend/app/tesauro/indice.py.
 *
 * Busca lexical (com casamento por prefixo comum), candidatos com expansão pelo
 * termo genérico, validação de IDs em conjunto fechado e ordem amplo → específico.
 * A paridade com o Python é testada em backend/tests/test_paridade_js.py.
 *
 * Dados (gerados por scripts/gerar_demo.py a partir do snapshot da carga):
 *   {versao, fonte, avisos, termos: [[id, rotulo, meta(0|1), [ids dos genéricos], [alternativos]]]}
 */
(function (raiz) {
  "use strict";
  const N = typeof module !== "undefined" && module.exports ? require("./nucleo.js") : raiz.Nucleo;

  const STOPWORDS = new Set(["a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "sem", "um", "uma", "ao", "aos", "que", "se", "ou", "sobre", "pela", "pelo"]);
  const METATERMOS_MODIFICADORES = new Set(["especificador / modificador"]);
  const PREFIXO_MINIMO = 5, PESO_PREFIXO = 0.6;

  function radical(p) {
    for (const [suf, rep] of [["coes", "cao"], ["oes", "ao"], ["aes", "ao"], ["ais", "al"], ["eis", "el"], ["ns", "m"]]) {
      if (p.endsWith(suf) && p.length > suf.length + 2) return p.slice(0, -suf.length) + rep;
    }
    if (p.endsWith("es") && p.length > 5 && "rsz".includes(p[p.length - 3])) return p.slice(0, -2);
    if (p.endsWith("s") && p.length > 3) return p.slice(0, -1);
    return p;
  }
  const tokens = (t) => (N.normalizarParaBusca(t || "").match(/[a-z0-9]+/g) || []).filter((x) => !STOPWORDS.has(x)).map(radical);

  function semelhancaToken(a, b) {
    if (a === b) return 1;
    if (Math.min(a.length, b.length) < PREFIXO_MINIMO) return 0;
    let comum = 0;
    while (comum < a.length && comum < b.length && a[comum] === b[comum]) comum++;
    return comum === Math.min(a.length, b.length) || comum >= 6 ? PESO_PREFIXO : 0;
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  class Indice {
    constructor(dados) {
      this.versao = dados.versao; this.fonte = dados.fonte; this.avisos = dados.avisos || [];
      this.termos = new Map();
      for (const [id, rotulo, meta, tg, alt] of dados.termos) this.termos.set(id, { id, rotulo, meta: !!meta, tg: tg || [], alternativos: alt || [] });
      this.porRotuloMap = new Map(); this.remissivas = new Map(); this.docs = new Map();
      const df = new Map();
      for (const t of this.termos.values()) {
        this.porRotuloMap.set(N.normalizarParaBusca(t.rotulo), t.id);
        for (const a of t.alternativos) if (!this.remissivas.has(N.normalizarParaBusca(a))) this.remissivas.set(N.normalizarParaBusca(a), t.id);
        const doc = new Map();
        for (const tok of tokens(t.rotulo)) doc.set(tok, (doc.get(tok) || 0) + 3);
        for (const a of t.alternativos) for (const tok of tokens(a)) doc.set(tok, (doc.get(tok) || 0) + 2);
        this.docs.set(t.id, doc);
        for (const tok of doc.keys()) df.set(tok, (df.get(tok) || 0) + 1);
      }
      const n = Math.max(1, this.termos.size);
      this.idf = new Map([...df].map(([tok, f]) => [tok, Math.log(1 + n / f)]));
      const modificadores = new Set([...this.termos.values()].filter((t) => t.meta && METATERMOS_MODIFICADORES.has(t.rotulo.trim().toLowerCase())).map((t) => t.id));
      this.naoIndexaveis = new Set([...this.termos.values()].filter((t) => t.meta || (t.tg.length && t.tg.every((p) => modificadores.has(p)))).map((t) => t.id));
    }
    get tamanho() { return this.termos.size; }
    termo(id) { return this.termos.get(String(id)) || null; }
    indexavel(id) { return this.termos.has(id) && !this.naoIndexaveis.has(id); }
    porRotulo(r) { const k = N.normalizarParaBusca(r); const id = this.porRotuloMap.get(k) || this.remissivas.get(k); return id ? this.termos.get(id) : null; }
    rotulosPreferidos() { return new Set([...this.termos.values()].map((t) => t.rotulo)); }

    buscaLexical(consulta, k = 30, incluirMeta = false) {
      const q = [...new Set(tokens(consulta))].sort(cmp);
      if (!q.length) return [];
      const frase = N.normalizarParaBusca(consulta);
      const res = [];
      for (const [id, doc] of this.docs) {
        if (this.naoIndexaveis.has(id) && !incluirMeta) continue;
        const chaves = [...doc.keys()].sort(cmp);
        let score = 0;
        for (const tq of q) {
          let melhor = 0;
          for (const td of chaves) { const w = semelhancaToken(tq, td); if (w) melhor = Math.max(melhor, doc.get(td) * (this.idf.get(td) || 0) * w); }
          score += melhor;
        }
        if (!score) continue;
        const t = this.termos.get(id);
        if ([t.rotulo, ...t.alternativos].map((r) => N.normalizarParaBusca(r)).some((r) => r && frase.includes(r))) score *= 2;
        res.push([id, score]);
      }
      const r9 = (x) => Math.round(x * 1e9) / 1e9;
      res.sort((a, b) => r9(b[1]) - r9(a[1]) || cmp(this.termos.get(a[0]).rotulo, this.termos.get(b[0]).rotulo) || cmp(a[0], b[0]));
      return res.slice(0, k);
    }

    candidato(id, pontuacao, origem) {
      const t = this.termos.get(id);
      const pai = t.tg.length ? this.termos.get(t.tg[0]) : null;
      return { id, rotulo: t.rotulo, tg_rotulo: pai ? pai.rotulo : null, tg_indexavel: pai ? this.indexavel(pai.id) : false, pontuacao, origem };
    }

    candidatos(consulta, k = 30, expandir = true) {
      const vistos = new Map();
      for (const [id, s] of this.buscaLexical(consulta, k)) vistos.set(id, this.candidato(id, s, "lexical"));
      if (expandir) for (const c of [...vistos.values()]) for (const pai of this.termos.get(c.id).tg) {
        if (this.indexavel(pai) && !vistos.has(pai)) vistos.set(pai, this.candidato(pai, 0, "expansao_tg"));
      }
      return [...vistos.values()];
    }

    /** União dos candidatos de várias consultas, melhor pontuação de cada termo, até `limite`. */
    candidatosDeConsultas(consultas, kPorConsulta = 12, limite = 40) {
      const todos = new Map();
      for (const q of consultas) for (const c of this.candidatos(q, kPorConsulta)) {
        const atual = todos.get(c.id);
        if (!atual || c.pontuacao > atual.pontuacao) todos.set(c.id, c);
      }
      return [...todos.values()].sort((a, b) => b.pontuacao - a.pontuacao || cmp(a.rotulo, b.rotulo)).slice(0, limite);
    }

    ancestrais(id) {
      const cadeia = [], vistos = new Set([id]);
      let t = this.termos.get(id);
      while (t && t.tg.length) {
        const pai = t.tg[0];
        if (vistos.has(pai)) break;
        cadeia.push(pai); vistos.add(pai); t = this.termos.get(pai);
      }
      return cadeia;
    }
    ordenarAmploEspecifico(ids) {
      const u = [...new Set(ids)];
      return u.map((id, i) => [id, this.ancestrais(id).length, i]).sort((a, b) => a[1] - b[1] || a[2] - b[2]).map(([id]) => id);
    }
  }

  /** Passo 5 da seção 6.3 do doc 01: só passam IDs da lista enviada ao modelo. */
  function validarIds(ids, candidatos, limite = 5) {
    const permitidos = new Set(candidatos.map((c) => c.id));
    const aceitos = [], rejeitados = [];
    for (let i of ids) {
      i = String(i).trim();
      if (permitidos.has(i) && !aceitos.includes(i) && aceitos.length < limite) aceitos.push(i);
      else if (!aceitos.includes(i)) rejeitados.push(i);
    }
    return { aceitos, rejeitados };
  }

  const api = { Indice, validarIds, tokens, semelhancaToken };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Tesauro = api;
})(typeof self !== "undefined" ? self : this);
