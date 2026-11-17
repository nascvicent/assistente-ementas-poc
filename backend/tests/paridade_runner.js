// Executor do teste de paridade: lê casos em JSON pela entrada padrão e devolve
// o resultado do núcleo JavaScript (frontend/demo/nucleo.js).
const path = require("path");
const N = require(path.resolve(__dirname, "../../frontend/demo/nucleo.js"));
const AV = require(path.resolve(__dirname, "../../frontend/demo/avaliacao.js"));
const TS = require(path.resolve(__dirname, "../../frontend/demo/tesauro.js"));
const indices = new Map();

let entrada = "";
process.stdin.on("data", (d) => (entrada += d));
process.stdin.on("end", () => {
  const casos = JSON.parse(entrada);
  const saida = casos.map((c) => {
    switch (c.op) {
      case "linter":
        return N.verificar(c.texto, c.ctx || {}).map((a) => [a.codigo, a.gravidade, a.referencia]);
      case "evidencia":
        return N.conferirTrecho(c.trecho, c.pagina, new N.TextoPaginado(c.paginas));
      case "remover_ementa": {
        const r = N.removerEmenta(c.paginas);
        return { bloco: r.bloco, paginas: r.paginas.map((p) => p.texto) };
      }
      case "limpar":
        return N.limpar(c.paginas);
      case "frases":
        return N.contarFrases(c.texto);
      case "montar": {
        const disp = N.montarDispositivo(c.ficha);
        const cab = N.montarCabecalho(c.ficha, c.termos);
        return { dispositivo: disp, ementa: N.montarEmenta({ cabecalho: cab, caso: c.caso, razoes: c.razoes, dispositivo: disp.texto, teses: c.teses }) };
      }
      case "montar_ref":
        return N.montarReferencias(c.ficha, c.ids);
      case "comparar":
        return AV.comparar(c.gerada, c.referencia, {});
      case "texto_livre":
        return AV.extrairDoTextoLivre(c.texto);
      case "tesauro": {
        if (!indices.has(c.chave)) indices.set(c.chave, new TS.Indice(c.dados));
        const ix = indices.get(c.chave);
        return {
          busca: ix.buscaLexical(c.consulta, 15).map(([id, s]) => [id, Math.round(s * 1e6) / 1e6]),
          candidatos: ix.candidatos(c.consulta, 15).map((x) => [x.id, x.origem, x.tg_rotulo]),
          ordem: ix.ordenarAmploEspecifico(c.ordenar || []),
        };
      }
      case "tese":
        return N.verificarTese(c.tese, c.ficha, c.textoVoto);
      default:
        throw new Error("op desconhecida " + c.op);
    }
  });
  process.stdout.write(JSON.stringify(saida));
});
