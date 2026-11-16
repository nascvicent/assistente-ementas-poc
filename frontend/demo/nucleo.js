/* Núcleo determinístico em JavaScript — porte de backend/app (Python).
 *
 * Normalização, limpeza do texto, remoção do bloco de ementa, conferência de
 * evidência, linter E01–E21, dispositivo e cabeçalho montados por código.
 * A paridade com o Python é testada em backend/tests/test_paridade_js.py:
 * mudou uma regra lá, mude aqui (e vice-versa).
 *
 * Roda no navegador (window.Nucleo) e no Node (module.exports), sem dependências.
 */
(function (raiz) {
  "use strict";

  // ------------------------------------------------------------------ texto
  const ASPAS = {
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‘": "'", "’": "'", "‚": "'", "´": "'", "`": "'",
    "–": "-", "—": "-", "‒": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "°": "º",
  };
  const RE_ASPAS = new RegExp("[" + Object.keys(ASPAS).join("") + "]", "g");

  function semAcento(t) {
    return t.normalize("NFD").replace(/\p{Mn}/gu, "");
  }

  function normalizar(texto, tirarAcento = false) {
    let t = texto.normalize("NFKC").replace(/­/g, "");
    t = t.replace(RE_ASPAS, (c) => ASPAS[c]);
    t = t.replace(/([\p{L}\p{N}_])-\s*\n\s*([\p{L}\p{N}_])/gu, "$1$2");
    t = t.replace(/\s+/g, " ").trim().toLowerCase();
    return tirarAcento ? semAcento(t) : t;
  }

  function normalizarParaBusca(texto) {
    let t = normalizar(texto, true);
    t = t.replace(/["'()[\]{};:!?]/g, " ");
    t = t.replace(/(?<!\d)[.,](?!\d)/g, " ");
    return t.replace(/\s+/g, " ").trim();
  }

  const chave = (t) => normalizar(t, true);
  const semMilhar = (t) => t.replace(/(?<=\d)\.(?=\d{3}\b)/g, "");
  const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // ------------------------------------------------------------- limpeza
  const LINHAS_BORDA = 3;
  const assinatura = (l) => l.trim().toLowerCase().replace(/\s+/g, " ").replace(/\d+/g, "#");

  function removerCabecalhoRodape(paginas, proporcaoMinima = 0.5) {
    if (paginas.length < 3) return paginas;
    const contagem = new Map();
    for (const texto of paginas) {
      const linhas = texto.split("\n").filter((l) => l.trim());
      const bordas = new Set([...linhas.slice(0, LINHAS_BORDA), ...linhas.slice(-LINHAS_BORDA)].map(assinatura));
      for (const b of bordas) contagem.set(b, (contagem.get(b) || 0) + 1);
    }
    const limite = Math.max(2, Math.floor(paginas.length * proporcaoMinima + 0.5));
    const repetidas = new Set([...contagem].filter(([a, n]) => n >= limite && a).map(([a]) => a));
    return paginas.map((texto) => {
      const linhas = texto.split("\n");
      const naoVazias = linhas.map((l, i) => (l.trim() ? i : -1)).filter((i) => i >= 0);
      const borda = new Set([...naoVazias.slice(0, LINHAS_BORDA), ...naoVazias.slice(-LINHAS_BORDA)]);
      return linhas.filter((l, i) => !(borda.has(i) && repetidas.has(assinatura(l)))).join("\n").trim();
    });
  }

  const juntarHifenizacao = (t) => t.replace(/([\p{L}\p{N}_])[-­]\n\s*([a-zà-ÿ])/gu, "$1$2");

  function limpar(paginas) {
    return removerCabecalhoRodape(paginas).map((p) => juntarHifenizacao(p).trim());
  }

  // ------------------------------------------------- remoção da ementa
  const INICIO_EMENTA = /^\s*EMENTA\s*:/i;
  const TITULO_IV = /^\s*IV\s*[.\-–]\s*TESE/i;
  const ITEM = /^\s*\d+\s*[.)]\s+\S/;
  const FIM_EMENTA = /^\s*(AC[ÓO]RD[ÃA]O\b|ACORDAM\b|VISTOS\b|RESULTADO DO JULGAMENTO|[ÉE] (O|COMO) VOTO|RELAT[ÓO]RIO\b|VOTO( DO RELATOR| DO CONSELHEIRO)?\s*$|FUNDAMENTA[ÇC][ÃA]O\b|CONCLUS[ÃA]O\b|DECIS[ÃA]O\b|RECIFE\s*,|PRESENTES\b|PARTICIPARAM\b|PROCURADOR)/i;
  const MAX_LINHAS_EMENTA = 200;

  function fimDaEmenta(linhas, inicio) {
    const limite = Math.min(linhas.length, inicio + MAX_LINHAS_EMENTA);
    let viuIV = false, ultimoItemIV = null;
    for (let i = inicio + 1; i < limite; i++) {
      const l = linhas[i][1];
      if (FIM_EMENTA.test(l)) return i;
      if (TITULO_IV.test(l)) viuIV = true;
      else if (viuIV && ITEM.test(l)) ultimoItemIV = i;
      else if (viuIV && ultimoItemIV !== null && !l.trim()) return i;
    }
    return ultimoItemIV !== null ? ultimoItemIV + 1 : limite;
  }

  /** paginas: [{numero, texto}] → {paginas, bloco: {texto, pagina_inicial, pagina_final} | null} */
  function removerEmenta(paginas) {
    const linhas = paginas.flatMap((p) => p.texto.split("\n").map((l) => [p.numero, l]));
    const inicio = linhas.findIndex(([, l]) => INICIO_EMENTA.test(l));
    if (inicio < 0) return { paginas, bloco: null };
    const fim = fimDaEmenta(linhas, inicio);
    const bloco = {
      texto: linhas.slice(inicio, fim).map(([, l]) => l).join("\n").trim(),
      pagina_inicial: linhas[inicio][0],
      pagina_final: linhas[fim - 1][0],
    };
    const restantes = [...linhas.slice(0, inicio), ...linhas.slice(fim)];
    return {
      paginas: paginas.map((p) => ({ ...p, texto: restantes.filter(([n]) => n === p.numero).map(([, l]) => l).join("\n").trim() })),
      bloco,
    };
  }

  const TITULOS_SECAO = [
    [/^\s*RELAT[ÓO]RIO\b/i, "relatorio"],
    [/^\s*(VOTO\b|FUNDAMENTA[ÇC][ÃA]O\b)/i, "voto"],
    [/^\s*(ANTE O EXPOSTO|DIANTE DO EXPOSTO|CONCLUS[ÃA]O\b|DISPOSITIVO\b|.*VOTO pelo que segue)/i, "dispositivo"],
  ];

  function detectarSecoes(paginas) {
    let atual = "preambulo";
    return paginas.map((p) => {
      let inicio = atual;
      const linhas = p.texto.split("\n").filter((l) => l.trim());
      linhas.forEach((linha, i) => {
        for (const [re, secao] of TITULOS_SECAO) {
          if (re.test(linha)) { atual = secao; if (i === 0) inicio = secao; break; }
        }
      });
      return { ...p, secao: inicio !== "preambulo" ? inicio : atual };
    });
  }

  // --------------------------------------------------------- evidência
  class TextoPaginado {
    constructor(paginas) { // {numero: texto}
      this.p = new Map(Object.entries(paginas).map(([n, t]) => [Number(n), normalizar(t)]));
    }
    tem(n) { return this.p.has(n); }
    pagina(n) { return this.p.get(n) || ""; }
    numeros() { return [...this.p.keys()].sort((a, b) => a - b); }
  }

  function atravessa(alvo, n, t) {
    if (!t.tem(n) || !t.tem(n + 1) || t.pagina(n + 1).includes(alvo)) return false;
    return (t.pagina(n) + " " + t.pagina(n + 1)).includes(alvo);
  }

  function conferirTrecho(trecho, pagina, texto) {
    const alvo = normalizar(trecho || "");
    if (!alvo) return { status: "nao_confirmada", pagina_encontrada: null };
    if (texto.pagina(pagina).includes(alvo)) return { status: "confirmada", pagina_encontrada: pagina };
    if (atravessa(alvo, pagina, texto)) return { status: "confirmada", pagina_encontrada: pagina };
    for (const n of texto.numeros()) if (n !== pagina && texto.pagina(n).includes(alvo)) return { status: "pagina_divergente", pagina_encontrada: n };
    for (const n of texto.numeros()) if (n !== pagina && atravessa(alvo, n, texto)) return { status: "pagina_divergente", pagina_encontrada: n };
    return { status: "nao_confirmada", pagina_encontrada: null };
  }

  // ------------------------------------------------------- ficha (JSON)
  function* evidencias(f) {
    if (f.processo && f.processo.evidencia) yield ["processo", f.processo.evidencia];
    if (f.votacao && f.votacao.evidencia) yield ["votacao", f.votacao.evidencia];
    for (const oc of f.ocorrencias || []) {
      for (const [i, x] of (oc.fundamentos || []).entries()) if (x.evidencia) yield [`ocorrencias[${oc.id}].fundamentos[${i}]`, x.evidencia];
      for (const [i, x] of (oc.normas || []).entries()) if (x.evidencia) yield [`ocorrencias[${oc.id}].normas[${i}]`, x.evidencia];
      for (const [i, x] of (oc.precedentes || []).entries()) if (x.evidencia) yield [`ocorrencias[${oc.id}].precedentes[${i}]`, x.evidencia];
      if (oc.consequencias && oc.consequencias.evidencia) yield [`ocorrencias[${oc.id}].consequencias`, oc.consequencias.evidencia];
    }
    if (f.julgamento && f.julgamento.evidencia) yield ["julgamento", f.julgamento.evidencia];
  }

  /** Confere todas as evidências no lugar; devolve a lista de problemas. */
  function conferirFicha(f, texto) {
    const problemas = [];
    for (const [caminho, ev] of evidencias(f)) {
      const r = conferirTrecho(ev.trecho, Number(ev.pagina), texto);
      ev.status = r.status;
      ev.pagina_encontrada = r.pagina_encontrada;
      if (r.status !== "confirmada") problemas.push({ caminho, trecho: ev.trecho, pagina_indicada: ev.pagina, ...r });
    }
    return problemas;
  }

  function nomesDePessoas(f) {
    const nomes = new Set();
    if (f.processo && f.processo.relator) nomes.add(f.processo.relator);
    if (f.votacao && f.votacao.redator_voto_vencedor) nomes.add(f.votacao.redator_voto_vencedor);
    for (const oc of f.ocorrencias || []) for (const r of oc.responsaveis || []) nomes.add(r);
    for (const r of (f.julgamento && f.julgamento.por_responsavel) || []) nomes.add(r.responsavel);
    return [...nomes].map((n) => (n || "").trim()).filter(Boolean);
  }

  // ------------------------------------------------------------ domínio
  const ROTULOS_MODALIDADE = {
    AUDITORIA_ESPECIAL: ["AUDITORIA ESPECIAL"],
    PRESTACAO_CONTAS_GOVERNO: ["PRESTAÇÃO DE CONTAS DE GOVERNO", "PRESTAÇÃO DE CONTAS", "CONTAS DE GOVERNO"],
    PRESTACAO_CONTAS_GESTAO: ["PRESTAÇÃO DE CONTAS DE GESTÃO", "PRESTAÇÃO DE CONTAS", "CONTAS DE GESTÃO"],
    TOMADA_CONTAS_ESPECIAL: ["TOMADA DE CONTAS ESPECIAL"],
    MEDIDA_CAUTELAR: ["MEDIDA CAUTELAR"],
    ADMISSAO_PESSOAL: ["ADMISSÃO DE PESSOAL"],
    APOSENTADORIA: ["APOSENTADORIA"],
    PENSAO: ["PENSÃO"],
    DENUNCIA: ["DENÚNCIA"],
    REPRESENTACAO: ["REPRESENTAÇÃO"],
    CONSULTA: ["CONSULTA"],
    GESTAO_FISCAL: ["GESTÃO FISCAL", "PROCESSO DE GESTÃO FISCAL"],
    TERMO_AJUSTE_GESTAO: ["TERMO DE AJUSTE DE GESTÃO"],
    RECURSO_ORDINARIO: ["RECURSO ORDINÁRIO"],
    AGRAVO: ["AGRAVO"],
    EMBARGOS_DECLARACAO: ["EMBARGOS DE DECLARAÇÃO"],
    PEDIDO_RESCISAO: ["PEDIDO DE RESCISÃO"],
  };
  const MODALIDADES = Object.keys(ROTULOS_MODALIDADE);
  const RESULTADOS = ["REGULAR", "REGULAR_COM_RESSALVAS", "IRREGULAR", "APROVACAO", "APROVACAO_COM_RESSALVAS", "REJEICAO",
    "LEGAL", "ILEGAL", "CAUTELAR_CONCEDIDA", "CAUTELAR_NAO_CONCEDIDA", "NAO_CONHECIDO", "PROVIDO", "PARCIALMENTE_PROVIDO",
    "NAO_PROVIDO", "ACOLHIDOS", "REJEITADOS", "PROCEDENTE", "IMPROCEDENTE", "ARQUIVAMENTO"];
  const PROVIDENCIAS = ["DETERMINACOES", "RECOMENDACOES", "CIENCIA", "MULTA", "DEBITO", "REMESSA_MP", "REGISTRO", "NEGATIVA_REGISTRO"];

  const modalidadePorRotulo = (r) => MODALIDADES.filter((m) => ROTULOS_MODALIDADE[m].includes(r.trim().toUpperCase()));

  const PADROES_RESULTADO = [
    ["REGULAR_COM_RESSALVAS", /\bregular(idade|es)? com ressalvas?\b/],
    ["IRREGULAR", /\birregular(idade|es)?\b/],
    ["REGULAR", /\bregular(idade|es)?\b(?! com ressalva)/],
    ["APROVACAO_COM_RESSALVAS", /\baprova(cao|das?) com ressalvas?\b/],
    ["APROVACAO", /\baprova(cao|das?)\b(?! com ressalva)/],
    ["REJEICAO", /\brejei(cao|tadas?)\b/],
    ["ILEGAL", /\bilegal(idade)?\b/],
    ["LEGAL", /(?<!i)\blegal(idade)?\b/],
    ["CAUTELAR_NAO_CONCEDIDA", /\bnao concess[aã]o\b|\bnao concedida\b|\bindeferi(mento|da)\b/],
    ["CAUTELAR_CONCEDIDA", /(?<!nao )\bconcess[aã]o\b|(?<!nao )\bconcedida\b/],
    ["NAO_CONHECIDO", /\bnao conhecid[oa]s?\b/],
    ["PARCIALMENTE_PROVIDO", /\bparcialmente provid[oa]s?\b|\bprovimento parcial\b/],
    ["NAO_PROVIDO", /\bnao provid[oa]s?\b|\bdesprovid[oa]s?\b|\bdesprovimento\b|\bnegad[oa] provimento\b/],
    ["PROVIDO", /(?<!parcialmente )(?<!nao )\bprovid[oa]s?\b/],
    ["ACOLHIDOS", /\bacolhid[oa]s?\b/],
    ["REJEITADOS", /\brejeitad[oa]s?\b/],
    ["IMPROCEDENTE", /\bimprocede(nte|ncia)s?\b/],
    ["PROCEDENTE", /(?<!im)\bprocede(nte|ncia)s?\b/],
    ["ARQUIVAMENTO", /\barquivamento\b|\barquivad[oa]\b/],
  ];

  const EXPRESSOES_POR_MODALIDADE = {
    AUDITORIA_ESPECIAL: [/julgamento pela (ir)?regularidade/],
    PRESTACAO_CONTAS_GOVERNO: [/parecer previo pela (aprovacao|rejeicao)/],
    PRESTACAO_CONTAS_GESTAO: [/contas julgadas (ir)?regulares/, /julgamento pela (ir)?regularidade/],
    MEDIDA_CAUTELAR: [/homolog\w* (d[ao] )?(nao )?concess/, /referend\w*/],
    ADMISSAO_PESSOAL: [/(i)?legalidade/, /registro/],
    APOSENTADORIA: [/(i)?legalidade/, /registro/],
    PENSAO: [/(i)?legalidade/, /registro/],
    RECURSO_ORDINARIO: [/recurso (nao )?conhecido/],
    AGRAVO: [/(recurso|agravo) (nao )?conhecido/],
    EMBARGOS_DECLARACAO: [/embargos (nao )?(conhecidos|acolhidos|rejeitados)/],
    CONSULTA: null, DENUNCIA: null, REPRESENTACAO: null, TOMADA_CONTAS_ESPECIAL: null,
    TERMO_AJUSTE_GESTAO: null, PEDIDO_RESCISAO: null, GESTAO_FISCAL: null,
  };

  function resultadosNoTexto(t) {
    const achados = new Set(PADROES_RESULTADO.filter(([, re]) => re.test(t)).map(([r]) => r));
    if (achados.has("REGULAR_COM_RESSALVAS")) achados.delete("REGULAR");
    if (achados.has("APROVACAO_COM_RESSALVAS")) achados.delete("APROVACAO");
    return achados;
  }

  // ------------------------------------------------------------- linter
  const TITULO_CASO = "CASO EM EXAME", TITULO_RAZOES = "RAZÕES DE DECIDIR", TITULO_DISPOSITIVO = "DISPOSITIVO";
  const CONFIG = { tituloTesePreferido: "TESE DE JULGAMENTO", titulosTeseAceitos: ["TESE DE JULGAMENTO", "TESE"], maxSegmentos: 8, maxFrases: 3 };

  const RE_TITULO_SECAO = /^\s*(?<numeral>I{1,3}|IV|V|VI)\s*[.\-–]\s*(?<titulo>[A-ZÀ-Ý][A-ZÀ-Ý ]+?)\s*:?\s*$/gm;
  const RE_ITEM = /^\s*(?<numero>\d+)\s*[.)]\s+(?<resto>.*)$/;
  const RE_NUMERO_DUPLICADO = /^\s*(\d+)\s*\.\s+(\d+)\s*\.\s/;

  function analisar(texto) {
    texto = texto.replace(/\r\n/g, "\n").trim();
    const temPrefixo = texto.startsWith("EMENTA:");
    const corpo = temPrefixo ? texto.slice("EMENTA:".length) : texto;
    const titulos = [...corpo.matchAll(RE_TITULO_SECAO)];
    let cabecalho = titulos.length ? corpo.slice(0, titulos[0].index) : corpo;
    cabecalho = cabecalho.replace(/\s+/g, " ").trim();
    const secoes = titulos.map((m, i) => {
      const fim = i + 1 < titulos.length ? titulos[i + 1].index : corpo.length;
      const secao = { numeral: m.groups.numeral, titulo: m.groups.titulo.replace(/\s+/g, " ").trim(), itens: [], textoSolto: "" };
      let atual = null; const soltos = [];
      for (const linha of corpo.slice(m.index + m[0].length, fim).split("\n")) {
        if (!linha.trim()) continue;
        const mi = linha.match(RE_ITEM);
        if (mi) {
          const dup = RE_NUMERO_DUPLICADO.test(linha);
          let resto = mi.groups.resto;
          if (dup) resto = resto.replace(/^\d+\s*\.\s+/, "");
          atual = { numero: Number(mi.groups.numero), texto: resto.trim(), dup };
          secao.itens.push(atual);
        } else if (atual) atual.texto = `${atual.texto} ${linha.trim()}`;
        else soltos.push(linha.trim());
      }
      secao.textoSolto = soltos.join(" ");
      return secao;
    });
    const textoSecao = (s) => [s.textoSolto, ...s.itens.map((i) => i.texto)].join(" ").trim();
    const cab = cabecalho.trim().replace(/\.+$/, "").trim();
    const segmentos = cab ? cab.split(/\.\s+/).map((s) => s.trim()).filter(Boolean) : [];
    const secao = (t) => { const ts = Array.isArray(t) ? t : [t]; return secoes.find((s) => ts.includes(s.titulo)) || null; };
    return { texto, temPrefixo, cabecalho, secoes, segmentos, secao, textoSecao };
  }

  const ABREV = "(?:art|arts|inc|incs|al|p|pp|fl|fls|n|nº|sr|sra|dr|dra|ex|min|cons|proc|res|aux|v|cf|c\\.c|etc|lc|ec)";
  function contarFrases(texto) {
    const protegido = texto.replace(new RegExp(`(?<![\\p{L}\\p{N}_])(${ABREV})\\.`, "giu"), "$1<P>");
    return protegido.split(/(?<=[.!?])\s+(?=[A-ZÀ-Ý"“(])/).filter((p) => p.trim()).length;
  }

  const INICIOS_VEDADOS = ["trata-se de", "trata-se do", "trata-se da", "cuida-se de", "cuida-se do", "cuida-se da", "cuidam os autos"];
  const MARCAS_CASO_CONCRETO = ["no caso", "na especie", "nos autos", "em analise preliminar", "neste momento processual", "no presente caso", "in casu"];
  const PALAVRAS_VETADAS = ["carta magna", "lei maior", "carta politica", "mandamus", "data venia", "data maxima venia",
    "excelso pretorio", "pretorio excelso", "in casu", "ex vi", "parquet"];
  const VERBOS_CONJUGADOS = new Set(["E", "SAO", "FOI", "FORAM", "SERA", "SERAO", "DEVE", "DEVEM", "PODE", "PODEM", "HA", "HOUVE",
    "CONFIGURA", "CONFIGURAM", "CARACTERIZA", "CARACTERIZAM", "ENSEJA", "ENSEJAM", "CONSTITUI",
    "CONSTITUEM", "AFASTA", "AFASTAM", "IMPLICA", "IMPLICAM", "EXIGE", "EXIGEM", "VEDA", "PERMITE",
    "AUTORIZA", "DETERMINA", "JULGA", "APLICA", "ESTA", "ESTAO", "TEM", "POSSUI", "CABE", "COMPETE",
    "INCIDE", "INCIDEM", "OBSERVA", "OBSERVOU", "DEIXOU", "DEIXARAM", "REALIZOU", "UTILIZOU"]);
  const CONECTIVOS = new Set(["QUE", "QUANDO", "PORQUE", "EMBORA", "CASO", "SE"]);
  const ADJETIVOS_VALORATIVOS = ["gravissim", "flagrante", "absurd", "escandalos", "lamentavel", "inadmissivel", "inaceitavel",
    "vergonhos", "gritante", "temerari", "descalabro", "estarrecedor", "abominavel"];

  const RE_NORMA = /(?<tipo>Lei\s+Complementar|Lei\s+Org[aâ]nica|Lei|LC|Decreto-Lei|Decreto|Resolu[cç][aã]o(?:\s+TC)?|Portaria(?:\s+Normativa)?(?:\s+TC)?|Instru[cç][aã]o\s+Normativa|Emenda\s+Constitucional|EC|S[uú]mula(?:\s+Vinculante)?|RDC(?:\s+ANVISA)?)(?:\s+(?:Federal|Estadual|Municipal))?\s*(?:n\s*[º°o.]\s*|n\.\s*º\s*|nº\s*)?(?<num>\d[\d.]*\d|\d)(?:\s*\/\s*(?<ano>\d{2,4}))?/gi;
  const NORMAS_DE_SISTEMA = new Set(["portaria|322"]);
  const RE_VALOR = /R\$\s*(?<v>\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)/g;
  const RE_PERCENTUAL = /(?<v>\d+(?:[.,]\d+)?)\s*%/g;
  const RE_DATA = /\b(?<d>\d{1,2})\/(?<m>\d{1,2})\/(?<a>\d{4})\b/g;
  const RE_PROCESSO = /\b\d{7,8}-\d\b|\bprocesso\s+(?:tc[e]?(?:-pe)?\s+)?n[º°o.]/i;
  const RE_NUMERO_MAL = /\b(Lei|Decreto|Resolu[cç][aã]o|Portaria|S[uú]mula|Instru[cç][aã]o Normativa)(?![\p{L}\p{N}_])[^\n.;]{0,25}?(?<![\p{L}\p{N}_])(?<forma>n\.(?!\s*º)|n°|no\.?|nr\.?|n\.o|num\.|número)\s*\d/giu;
  const RE_ANO_2 = /\b(?:Lei|Decreto|Resolu[cç][aã]o|Portaria|S[uú]mula|LC|EC)(?![\p{L}\p{N}_])[^\n;]{0,25}?\d[\d.]*\s*\/\s*\d{2}\b(?!\d)/giu;

  function tipoBase(tipo) {
    const t = semAcento(tipo.toLowerCase());
    if (t.startsWith("lei complementar") || t === "lc") return "lei complementar|lc";
    for (const base of ["lei organica", "decreto-lei", "decreto", "resolucao", "portaria", "instrucao normativa",
      "emenda constitucional|ec", "sumula", "rdc", "lei"]) {
      if (base.split("|").some((b) => t.startsWith(b))) return base;
    }
    if (t === "ec") return "emenda constitucional|ec";
    return t;
  }

  const A = (codigo, gravidade, mensagem, referencia = null) => ({ codigo, gravidade, mensagem, referencia });

  function modalidadeDe(e, ctx) {
    if (ctx.modalidade) return ctx.modalidade;
    if (ctx.ficha) return ctx.ficha.especie_recursal || ctx.ficha.processo.modalidade;
    if (e.segmentos.length) { const c = modalidadePorRotulo(e.segmentos[0]); if (c.length === 1) return c[0]; }
    return null;
  }

  const GRUPOS_EXCLUSIVOS = [
    ["REGULAR", "REGULAR_COM_RESSALVAS", "IRREGULAR"], ["APROVACAO", "APROVACAO_COM_RESSALVAS", "REJEICAO"],
    ["LEGAL", "ILEGAL"], ["CAUTELAR_CONCEDIDA", "CAUTELAR_NAO_CONCEDIDA"],
    ["PROVIDO", "PARCIALMENTE_PROVIDO", "NAO_PROVIDO", "NAO_CONHECIDO"], ["ACOLHIDOS", "REJEITADOS"], ["PROCEDENTE", "IMPROCEDENTE"],
  ];

  function verificar(texto, ctx = {}, cfg = CONFIG) {
    const e = analisar(texto);
    const r = [];
    const corpo = e.secoes.map(e.textoSecao).join(" ");
    const tese = e.secao(cfg.titulosTeseAceitos);

    // E01
    if (!e.temPrefixo) r.push(A("E01", "alta", 'A ementa deve começar com "EMENTA: ".'));
    else if (!e.texto.startsWith("EMENTA: ")) r.push(A("E01", "alta", 'Falta espaço depois de "EMENTA:".'));
    // E02
    const cab = e.cabecalho;
    if (!cab) r.push(A("E02", "alta", "Cabeçalho vazio."));
    else {
      const letras = cab.replace(/[^A-Za-zÀ-ÿ]/g, "");
      if (letras !== letras.toUpperCase()) {
        const minusc = (cab.match(/[A-Za-zÀ-ÿ]+/g) || []).filter((p) => p !== p.toUpperCase()).slice(0, 5);
        r.push(A("E02", "alta", "Cabeçalho deve estar todo em maiúsculas.", minusc.join(", ")));
      }
      if (/\s[–—-]\s/.test(cab)) r.push(A("E02", "alta", "Segmentos do cabeçalho devem ser separados por ponto, não por travessão ou hífen."));
      if (!cab.endsWith(".")) r.push(A("E02", "alta", "Cabeçalho deve terminar com ponto final."));
      if (/\.(?=[A-ZÀ-Ý])/.test(cab) || /[;,]\s*$/.test(cab)) r.push(A("E02", "alta", 'Segmentos devem ser separados por ". " (ponto e espaço).'));
    }
    // E03
    if (e.segmentos.length) {
      const p = e.segmentos[0], cand = modalidadePorRotulo(p);
      const esperada = ctx.modalidade || (ctx.ficha && (ctx.ficha.especie_recursal || ctx.ficha.processo.modalidade));
      if (!cand.length) r.push(A("E03", "alta", "O primeiro segmento do cabeçalho não é uma modalidade processual reconhecida.", p));
      else if (esperada && !cand.includes(esperada)) r.push(A("E03", "alta", `Modalidade do cabeçalho (${p}) difere da modalidade do processo (${esperada}).`, p));
    }
    // E04
    for (const s of e.secoes) {
      if (s.titulo.includes("QUESTÃO EM DISCUSSÃO") || s.titulo.includes("QUESTAO EM DISCUSSAO")) r.push(A("E04", "alta", 'A ementa do TCE-PE não tem a seção "Questão em discussão".', `${s.numeral}. ${s.titulo}`));
      if (s.titulo === "DISPOSITIVO E TESE") r.push(A("E04", "alta", "Dispositivo e tese devem ficar em seções separadas (III e IV).", `${s.numeral}. ${s.titulo}`));
    }
    const esperado = [["I", TITULO_CASO], ["II", TITULO_RAZOES], ["III", TITULO_DISPOSITIVO]];
    const enc = e.secoes.map((s) => [s.numeral, s.titulo]);
    if (JSON.stringify(enc.slice(0, 3)) !== JSON.stringify(esperado)) {
      r.push(A("E04", "alta", "Seções devem ser: I. CASO EM EXAME; II. RAZÕES DE DECIDIR; III. DISPOSITIVO; IV. " + cfg.tituloTesePreferido + ".",
        enc.map(([n, t]) => `${n}. ${t}`).join("; ") || "nenhuma seção encontrada"));
    } else {
      const resto = e.secoes.slice(3);
      if (resto.length > 1) r.push(A("E04", "alta", "Há seções além da IV.", resto.map((s) => `${s.numeral}. ${s.titulo}`).join("; ")));
      if (resto.length) {
        const iv = resto[0];
        if (iv.numeral !== "IV" || !cfg.titulosTeseAceitos.includes(iv.titulo)) r.push(A("E04", "alta", `A seção IV deve ser "IV. ${cfg.tituloTesePreferido}".`, `${iv.numeral}. ${iv.titulo}`));
        else if (iv.titulo !== cfg.tituloTesePreferido) r.push(A("E04", "baixa", `Título da seção IV fora do padrão: usar "${cfg.tituloTesePreferido}" (a confirmar com a Diretoria de Julgamento).`, iv.titulo));
      }
    }
    // E05
    const numeros = e.secoes.flatMap((s) => s.itens.map((i) => i.numero));
    for (const s of e.secoes) for (const i of s.itens) if (i.dup) r.push(A("E05", "alta", `Numeração duplicada no item ${i.numero} (ex.: "${i.numero}. ${i.numero}.").`, `${s.numeral}. ${s.titulo}`));
    if (numeros.length && numeros.some((n, k) => n !== k + 1)) r.push(A("E05", "alta", "Itens devem ser numerados em sequência contínua (1, 2, 3…) do início ao fim, atravessando as seções.", numeros.join(" ")));
    for (const s of e.secoes) if (!s.itens.length && s.textoSolto) r.push(A("E05", "alta", "Seção sem item numerado.", `${s.numeral}. ${s.titulo}`));
    // E06
    const caso = e.secao(TITULO_CASO);
    if (caso && e.textoSecao(caso)) {
      for (const item of caso.itens.length ? caso.itens : [{ numero: 0, texto: e.textoSecao(caso) }]) {
        const ini = chave(item.texto);
        const v = INICIOS_VEDADOS.find((x) => ini.startsWith(x));
        if (v) r.push(A("E06", "media", `Caso em exame não deve começar com "${v[0].toUpperCase() + v.slice(1)}": comece pelo objeto do processo.`, item.texto.slice(0, 60)));
      }
    }
    // E07
    const razoes = e.secao(TITULO_RAZOES);
    if (razoes) for (const i of razoes.itens) { const n = contarFrases(i.texto); if (n > cfg.maxFrases) r.push(A("E07", "media", `Item ${i.numero} das razões tem ${n} frases (máximo ${cfg.maxFrases}); provavelmente reúne mais de um fundamento.`, i.texto.slice(0, 60))); }
    // E08
    const disp = e.secao(TITULO_DISPOSITIVO), mod = modalidadeDe(e, ctx);
    if (disp && mod) {
      const exps = EXPRESSOES_POR_MODALIDADE[mod];
      if (exps && !exps.some((re) => re.test(chave(e.textoSecao(disp))))) r.push(A("E08", "alta", `Dispositivo não usa expressão padronizada para ${mod} (tabela provisória, pendência P1).`, e.textoSecao(disp).slice(0, 80)));
    }
    // E09
    if (disp && ctx.ficha) {
      const j = ctx.ficha.julgamento || {};
      const esperados = new Set([...(j.resultado || []), ...(j.por_responsavel || []).map((x) => x.resultado)]);
      const achados = resultadosNoTexto(chave(e.textoSecao(disp)));
      for (const x of [...esperados].filter((x) => !achados.has(x)).sort()) r.push(A("E09", "alta", `Resultado do julgamento (${x}) não aparece no dispositivo.`, e.textoSecao(disp).slice(0, 80)));
      for (const g of GRUPOS_EXCLUSIVOS) {
        const esp = g.filter((x) => esperados.has(x));
        if (esp.length) for (const x of g.filter((x) => achados.has(x) && !esperados.has(x)).sort()) r.push(A("E09", "alta", `Dispositivo menciona ${x}, que não é o resultado registrado na Ficha (${esp.sort().join(", ")}).`, e.textoSecao(disp).slice(0, 80)));
      }
    }
    // E10 / E11
    if (tese) {
      const proibidos = [];
      if (ctx.ficha) {
        for (const n of nomesDePessoas(ctx.ficha)) proibidos.push(n);
        if (ctx.ficha.processo.unidade_jurisdicionada) proibidos.push(ctx.ficha.processo.unidade_jurisdicionada);
        if (ctx.ficha.processo.numero) proibidos.push(ctx.ficha.processo.numero);
      }
      for (const item of tese.itens) {
        const k = chave(item.texto);
        if (k.includes("r$")) r.push(A("E10", "alta", `Tese ${item.numero} cita valor em reais; a tese deve ser abstrata.`, item.texto.slice(0, 60)));
        if (RE_PROCESSO.test(item.texto)) r.push(A("E10", "alta", `Tese ${item.numero} cita número de processo.`, item.texto.slice(0, 60)));
        for (const p of new Set(proibidos)) { const kp = chave(p); if (kp && new RegExp(`\\b${escapar(kp)}\\b`).test(k)) r.push(A("E10", "alta", `Tese ${item.numero} cita nome próprio do caso.`, p)); }
      }
      for (const item of tese.itens) {
        const k = chave(item.texto);
        for (const m of MARCAS_CASO_CONCRETO) if (new RegExp(`\\b${escapar(m)}\\b`).test(k)) r.push(A("E11", "media", `Tese ${item.numero} contém marca de caso concreto ("${m}").`, item.texto.slice(0, 60)));
      }
    }
    // E12
    if (ctx.textoVoto) {
      const voto = semMilhar(chave(ctx.textoVoto));
      const vistos = new Set();
      for (const m of corpo.matchAll(RE_NORMA)) {
        const base = tipoBase(m.groups.tipo), num = m.groups.num.replace(/\./g, ""), k = base.split("|")[0] + "|" + num;
        if (vistos.has(k) || NORMAS_DE_SISTEMA.has(k)) continue;
        vistos.add(k);
        if (!new RegExp(`\\b(?:${base})\\b[^0-9]{0,40}?\\b${num}\\b`).test(voto)) r.push(A("E12", "alta", "Norma citada na ementa não foi localizada no voto.", m[0].trim()));
      }
      // E13
      const v = ctx.textoVoto.replace(/\s+/g, " "), vc = v.replace(/ /g, "");
      for (const m of corpo.matchAll(RE_VALOR)) if (!v.includes(m.groups.v) && !semMilhar(v).includes(semMilhar(m.groups.v))) r.push(A("E13", "alta", "Valor não localizado no voto.", m[0]));
      for (const m of corpo.matchAll(RE_PERCENTUAL)) if (!vc.includes(m.groups.v + "%")) r.push(A("E13", "alta", "Percentual não localizado no voto.", m[0]));
      for (const m of corpo.matchAll(RE_DATA)) {
        const d = Number(m.groups.d), me = Number(m.groups.m), a = m.groups.a, p2 = (x) => String(x).padStart(2, "0");
        if (![m[0], `${p2(d)}/${p2(me)}/${a}`, `${d}/${me}/${a}`].some((x) => v.includes(x))) r.push(A("E13", "alta", "Data não localizada no voto.", m[0]));
      }
    }
    // E14 / E21
    if (ctx.termosCabecalho && ctx.termosCabecalho.length) {
      const segs = new Set(e.segmentos.map((s) => s.toUpperCase()));
      const rot = ctx.rotulosTesauro ? new Set([...ctx.rotulosTesauro].map((x) => x.toUpperCase())) : null;
      for (const t of ctx.termosCabecalho) {
        if (t.fora_do_tesauro) { if (!t.confirmado_pelo_usuario) r.push(A("E21", "media", "Termo fora do tesauro ainda não confirmado pelo usuário (art. 4º, III).", t.rotulo)); continue; }
        if (rot && !rot.has(t.rotulo.toUpperCase())) r.push(A("E14", "alta", "Termo marcado como do tesauro não existe no TCN com este rótulo.", t.rotulo));
        if (!segs.has(t.rotulo.toUpperCase())) r.push(A("E14", "alta", "Termo do tesauro não aparece no cabeçalho com o rótulo exato.", t.rotulo));
      }
    }
    // E15
    for (const m of corpo.matchAll(RE_NUMERO_MAL)) r.push(A("E15", "baixa", 'Use "nº" na citação de normas.', m[0]));
    for (const m of corpo.matchAll(RE_ANO_2)) r.push(A("E15", "baixa", "Ano da norma deve ter quatro dígitos.", m[0]));
    // E16
    const kt = chave(e.texto);
    for (const p of PALAVRAS_VETADAS) if (new RegExp(`\\b${escapar(p)}\\b`).test(kt)) r.push(A("E16", "baixa", `Expressão vetada: "${p}" (use linguagem simples; ex.: "Constituição Federal").`, p));
    // E17
    if (e.segmentos.length > cfg.maxSegmentos) r.push(A("E17", "baixa", `Cabeçalho com ${e.segmentos.length} segmentos (sugestão: até ${cfg.maxSegmentos}).`));
    // E18
    for (const seg of e.segmentos) {
      const palavras = new Set(semAcento(seg.toUpperCase()).match(/[A-Z]+/g) || []);
      if ([...palavras].some((p) => VERBOS_CONJUGADOS.has(p) || CONECTIVOS.has(p))) r.push(A("E18", "alta", "Segmento do cabeçalho parece conter verbo ou oração; use só termos nominais (art. 4º, II).", seg));
    }
    // E19
    if (caso) { const k = chave(e.textoSecao(caso)); for (const rad of ADJETIVOS_VALORATIVOS) if (new RegExp(`\\b${rad}`).test(k)) r.push(A("E19", "baixa", "Caso em exame com adjetivo valorativo; a redação deve ser impessoal e sem juízo de valor.", rad)); }
    // E20
    if (ctx.ficha) for (const n of nomesDePessoas(ctx.ficha).sort()) if (new RegExp(`\\b${escapar(chave(n))}\\b`).test(kt)) r.push(A("E20", "alta", "Nome de pessoa natural na ementa (art. 10, § 2º).", n));

    const ordem = { alta: 0, media: 1, baixa: 2 };
    return r.map((a, i) => [a, i]).sort((x, y) => ordem[x[0].gravidade] - ordem[y[0].gravidade] || (x[0].codigo < y[0].codigo ? -1 : x[0].codigo > y[0].codigo ? 1 : x[1] - y[1])).map(([a]) => a);
  }

  // -------------------------------------------- montagem por código
  // PROVISÓRIO (pendência P1): expressões inferidas do Diário e do protótipo.
  const ROTULO_RESULTADO_CABECALHO = {
    REGULAR: "REGULARIDADE", REGULAR_COM_RESSALVAS: "REGULARIDADE COM RESSALVAS", IRREGULAR: "IRREGULARIDADE",
    APROVACAO: "APROVAÇÃO", APROVACAO_COM_RESSALVAS: "APROVAÇÃO COM RESSALVAS", REJEICAO: "REJEIÇÃO",
    LEGAL: "LEGALIDADE", ILEGAL: "ILEGALIDADE", CAUTELAR_CONCEDIDA: "CONCESSÃO", CAUTELAR_NAO_CONCEDIDA: "NÃO CONCESSÃO",
    NAO_CONHECIDO: "NÃO CONHECIMENTO", PROVIDO: "PROVIMENTO", PARCIALMENTE_PROVIDO: "PROVIMENTO PARCIAL",
    NAO_PROVIDO: "DESPROVIMENTO", ACOLHIDOS: "ACOLHIMENTO", REJEITADOS: "REJEIÇÃO", PROCEDENTE: "PROCEDÊNCIA",
    IMPROCEDENTE: "IMPROCEDÊNCIA", ARQUIVAMENTO: "ARQUIVAMENTO",
  };
  const PROVIDENCIA_TEXTO = {
    DETERMINACOES: "expedição de determinações", RECOMENDACOES: "expedição de recomendações", CIENCIA: "ciência",
    MULTA: "aplicação de multa", DEBITO: "imputação de débito", REMESSA_MP: "remessa ao Ministério Público",
    REGISTRO: "concessão de registro", NEGATIVA_REGISTRO: "negativa de registro",
  };
  const RECURSOS = ["RECURSO_ORDINARIO", "AGRAVO", "PEDIDO_RESCISAO"];

  function fraseResultado(mod, res) {
    const T = {
      AUDITORIA_ESPECIAL: { REGULAR: "Julgamento pela regularidade do objeto da Auditoria Especial", REGULAR_COM_RESSALVAS: "Julgamento pela regularidade com ressalvas do objeto da Auditoria Especial", IRREGULAR: "Julgamento pela irregularidade do objeto da Auditoria Especial" },
      PRESTACAO_CONTAS_GOVERNO: { APROVACAO: "Parecer Prévio pela aprovação das contas", APROVACAO_COM_RESSALVAS: "Parecer Prévio pela aprovação com ressalvas das contas", REJEICAO: "Parecer Prévio pela rejeição das contas" },
      PRESTACAO_CONTAS_GESTAO: { REGULAR: "Contas julgadas regulares", REGULAR_COM_RESSALVAS: "Contas julgadas regulares com ressalvas", IRREGULAR: "Contas julgadas irregulares" },
      MEDIDA_CAUTELAR: { CAUTELAR_CONCEDIDA: "Homologação da concessão da medida cautelar", CAUTELAR_NAO_CONCEDIDA: "Homologação da não concessão da medida cautelar" },
      EMBARGOS_DECLARACAO: { ACOLHIDOS: "Embargos de declaração conhecidos e acolhidos", REJEITADOS: "Embargos de declaração conhecidos e rejeitados", NAO_CONHECIDO: "Embargos de declaração não conhecidos" },
      CONSULTA: { _: "Consulta conhecida e respondida", NAO_CONHECIDO: "Consulta não conhecida" },
    };
    for (const m of ["ADMISSAO_PESSOAL", "APOSENTADORIA", "PENSAO"]) T[m] = { LEGAL: "Legalidade dos atos, com concessão de registro", ILEGAL: "Ilegalidade dos atos, com negativa de registro" };
    for (const m of RECURSOS) T[m] = { NAO_CONHECIDO: "Recurso não conhecido", PROVIDO: "Recurso conhecido e provido", PARCIALMENTE_PROVIDO: "Recurso conhecido e parcialmente provido", NAO_PROVIDO: "Recurso conhecido e não provido" };
    const t = T[mod];
    if (!t) return null;
    return t[res] || (res === undefined ? t._ : null) || null;
  }

  /** Dispositivo a partir de ficha.julgamento. Devolve {texto, a_definir}. */
  function montarDispositivo(ficha) {
    const mod = ficha.especie_recursal || ficha.processo.modalidade;
    const j = ficha.julgamento || { resultado: [] };
    const frases = (j.resultado && j.resultado.length ? j.resultado : [undefined]).map((r) => fraseResultado(mod, r));
    if (frases.some((f) => !f)) {
      const rot = (j.resultado || []).map((r) => (ROTULO_RESULTADO_CABECALHO[r] || r).toLowerCase()).join(", ");
      return { texto: `[A DEFINIR: expressão padronizada do dispositivo para ${mod}${rot ? ` (${rot})` : ""}]`, a_definir: true };
    }
    let texto = [...new Set(frases)].join("; ");
    const prov = (j.providencias || []).filter((p) => PROVIDENCIA_TEXTO[p] && !(["REGISTRO", "NEGATIVA_REGISTRO"].includes(p) && /registro/.test(texto)));
    if (prov.length) {
      const partes = prov.map((p) => PROVIDENCIA_TEXTO[p]);
      texto += ", com " + (partes.length > 1 ? partes.slice(0, -1).join(", ") + " e " + partes.at(-1) : partes[0]);
    }
    return { texto: texto + ".", a_definir: false };
  }

  /** Cabeçalho: MODALIDADE. TERMOS (genérico antes do específico, sem repetir). RESULTADO. */
  function montarCabecalho(ficha, termos, maxSegmentos = CONFIG.maxSegmentos) {
    const mod = ficha.especie_recursal || ficha.processo.modalidade;
    const segs = [ROTULOS_MODALIDADE[mod] ? ROTULOS_MODALIDADE[mod][0] : mod ? String(mod).replace(/_/g, " ") : "[MODALIDADE A DEFINIR]"];
    const j = ficha.julgamento || {};
    const resultado = (j.resultado || []).map((r) => ROTULO_RESULTADO_CABECALHO[r]).filter(Boolean);
    if (mod === "CONSULTA" && !resultado.length) resultado.push("CONHECIMENTO", "RESPOSTA");
    const vagas = Math.max(1, maxSegmentos - segs.length - resultado.length);
    const vistos = new Set(segs);
    const meio = [];
    for (const t of termos) for (const r of [t.generico, t.rotulo]) {
      const u = (r || "").trim().toUpperCase().replace(/\.+$/, "");
      if (u && !vistos.has(u)) { vistos.add(u); meio.push(u); }
    }
    return "EMENTA: " + [...segs, ...meio.slice(0, vagas), ...resultado].join(". ") + ".";
  }

  /** Ementa completa: numeração contínua e títulos por código. */
  function montarEmenta({ cabecalho, caso, razoes, dispositivo, teses }) {
    let n = 1;
    const linhas = [cabecalho, "", "I. CASO EM EXAME", ...[].concat(caso).map((c) => `${n++}. ${c}`), "", "II. RAZÕES DE DECIDIR",
      ...razoes.map((r) => `${n++}. ${r}`), "", "III. DISPOSITIVO", `${n++}. ${dispositivo}`];
    if (teses.length) linhas.push("", "IV. TESE DE JULGAMENTO", ...teses.map((t) => `${n++}. ${t}`));
    return linhas.join("\n");
  }

  // Verificador das teses (doc 01, §6.2): nomes do caso e normas fora da ficha.
  function verificarTese(tese, ficha, textoVoto) {
    const k = chave(tese), problemas = [];
    const proibidos = [...nomesDePessoas(ficha), ficha.processo.unidade_jurisdicionada, ficha.processo.numero].filter(Boolean);
    for (const p of new Set(proibidos)) if (new RegExp(`\\b${escapar(chave(p))}\\b`).test(k)) problemas.push(`cita "${p}"`);
    if (k.includes("r$")) problemas.push("cita valor em reais");
    for (const m of MARCAS_CASO_CONCRETO) if (new RegExp(`\\b${escapar(m)}\\b`).test(k)) problemas.push(`usa "${m}"`);
    if (textoVoto) {
      const voto = semMilhar(chave(textoVoto));
      for (const m of tese.matchAll(RE_NORMA)) {
        const base = tipoBase(m.groups.tipo), num = m.groups.num.replace(/\./g, "");
        if (!new RegExp(`\\b(?:${base})\\b[^0-9]{0,40}?\\b${num}\\b`).test(voto)) problemas.push(`norma não localizada no voto: ${m[0].trim()}`);
      }
    }
    return problemas;
  }

  const api = {
    semAcento, normalizar, normalizarParaBusca, limpar, removerCabecalhoRodape, juntarHifenizacao,
    removerEmenta, detectarSecoes, TextoPaginado, conferirTrecho, conferirFicha, evidencias, nomesDePessoas,
    MODALIDADES, RESULTADOS, PROVIDENCIAS, ROTULOS_MODALIDADE, modalidadePorRotulo, resultadosNoTexto,
    analisar, contarFrases, verificar, montarDispositivo, montarCabecalho, montarEmenta, verificarTese, CONFIG,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Nucleo = api;
})(typeof self !== "undefined" ? self : this);
