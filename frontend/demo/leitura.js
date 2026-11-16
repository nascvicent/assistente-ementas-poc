/* Leitura do voto no navegador — porte de backend/app/ingestao.
 * PDF (pdf.js, executado na própria página), DOCX e ODT (JSZip), TXT.
 * Depende de window.pdfjsLib, window.pdfjsWorker, window.JSZip e window.Nucleo.
 */
(function (raiz) {
  "use strict";
  const N = raiz.Nucleo;
  const MINIMO_CARACTERES = 20;

  async function lerPdf(buf) {
    const pdf = await raiz.pdfjsLib.getDocument({ data: new Uint8Array(buf), isEvalSupported: false }).promise;
    const paginas = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const conteudo = await (await pdf.getPage(i)).getTextContent();
      let t = "";
      for (const it of conteudo.items) { t += it.str; if (it.hasEOL) t += "\n"; }
      paginas.push(t);
    }
    const avisos = [];
    const vazias = paginas.map((t, i) => (t.trim().length < MINIMO_CARACTERES ? i + 1 : 0)).filter(Boolean);
    if (paginas.length && vazias.length === paginas.length) avisos.push("PDF sem camada de texto (provavelmente digitalizado). É preciso OCR antes de continuar.");
    else if (vazias.length) avisos.push(`Páginas sem texto extraível: ${vazias.join(", ")}.`);
    return { paginas, avisos, paginacaoReal: true };
  }

  const W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  async function lerDocx(buf) {
    const zip = await raiz.JSZip.loadAsync(buf);
    const xml = new DOMParser().parseFromString(await zip.file("word/document.xml").async("string"), "application/xml");
    const corpo = xml.getElementsByTagNameNS(W, "body")[0];
    const paginas = [[]];
    let houveQuebra = false;
    for (const el of corpo.children) {
      if (el.localName === "p") {
        const pedacos = [];
        let atual = "";
        for (const n of el.getElementsByTagNameNS(W, "*")) {
          if (n.localName === "t") atual += n.textContent;
          else if (n.localName === "tab") atual += "\t";
          else if ((n.localName === "br" && n.getAttributeNS(W, "type") === "page") || n.localName === "lastRenderedPageBreak") {
            pedacos.push(atual); atual = ""; houveQuebra = true;
          }
        }
        pedacos.push(atual);
        paginas[paginas.length - 1].push(pedacos[0]);
        for (const p of pedacos.slice(1)) paginas.push([p]);
      } else if (el.localName === "tbl") {
        for (const tr of el.getElementsByTagNameNS(W, "tr")) {
          const celulas = [...tr.getElementsByTagNameNS(W, "tc")].map((tc) => [...tc.getElementsByTagNameNS(W, "t")].map((t) => t.textContent).join(""));
          paginas[paginas.length - 1].push(celulas.join(" | "));
        }
      }
    }
    let textos = paginas.map((p) => p.join("\n").trim()).filter(Boolean);
    if (!textos.length) textos = [""];
    return { paginas: textos, avisos: houveQuebra ? [] : ["DOCX sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."], paginacaoReal: houveQuebra };
  }

  const TXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0";
  const OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0";
  function textoOdt(no) {
    let t = "";
    for (const n of no.childNodes) {
      if (n.nodeType === 3) t += n.nodeValue;
      else if (n.nodeType === 1 && n.namespaceURI === TXT) {
        if (n.localName === "s") t += " ".repeat(Number(n.getAttributeNS(TXT, "c") || 1));
        else if (n.localName === "tab") t += "\t";
        else if (n.localName === "line-break") t += "\n";
        else if (n.localName !== "soft-page-break") t += textoOdt(n);
      } else if (n.nodeType === 1) t += textoOdt(n);
    }
    return t;
  }
  async function lerOdt(buf) {
    const zip = await raiz.JSZip.loadAsync(buf);
    const xml = new DOMParser().parseFromString(await zip.file("content.xml").async("string"), "application/xml");
    const texto = xml.getElementsByTagNameNS(OFFICE, "text")[0];
    const paginas = [[]];
    let houveQuebra = false;
    (function percorrer(no) {
      for (const f of no.children) {
        if (f.namespaceURI === TXT && f.localName === "soft-page-break") { paginas.push([]); houveQuebra = true; }
        else if (f.namespaceURI === TXT && (f.localName === "p" || f.localName === "h")) {
          if ([...f.children].some((c) => c.localName === "soft-page-break")) { paginas.push([]); houveQuebra = true; }
          paginas[paginas.length - 1].push(textoOdt(f));
        } else percorrer(f);
      }
    })(texto);
    let textos = paginas.map((p) => p.join("\n").trim()).filter(Boolean);
    if (!textos.length) textos = [""];
    return { paginas: textos, avisos: houveQuebra ? [] : ["ODT sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."], paginacaoReal: houveQuebra };
  }

  function lerTxt(texto) {
    if (texto.includes("\f")) return { paginas: texto.split("\f"), avisos: [], paginacaoReal: true };
    return { paginas: [texto], avisos: ["TXT sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."], paginacaoReal: false };
  }

  async function hash(buf) {
    const h = await crypto.subtle.digest("SHA-256", buf);
    return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  /** Arquivo (File) ou texto colado → documento pronto para a extração. */
  async function carregar(origem) {
    let nome, bruto, buf;
    if (typeof origem === "string") {
      nome = "texto colado";
      buf = new TextEncoder().encode(origem).buffer;
      bruto = lerTxt(origem);
    } else {
      nome = origem.name;
      buf = await origem.arrayBuffer();
      const ext = (nome.split(".").pop() || "").toLowerCase();
      if (ext === "pdf") bruto = await lerPdf(buf.slice(0));
      else if (ext === "docx") bruto = await lerDocx(buf);
      else if (ext === "odt") bruto = await lerOdt(buf);
      else if (ext === "txt") bruto = lerTxt(new TextDecoder("utf-8").decode(buf));
      else throw new Error(`Formato não suportado: ${nome}. Use PDF, DOCX, ODT ou TXT.`);
    }
    const limpas = N.limpar(bruto.paginas);
    let paginas = limpas.map((t, i) => ({ numero: i + 1, texto: t }));
    const { paginas: semEmenta, bloco } = N.removerEmenta(paginas);
    paginas = N.detectarSecoes(semEmenta);
    const avisos = [...bruto.avisos];
    if (bloco) avisos.push(`Bloco de ementa existente removido (p. ${bloco.pagina_inicial}–${bloco.pagina_final}). Ele não é usado como fonte.`);
    return { nome, hash: await hash(buf), paginas, bloco, avisos, paginacaoReal: bruto.paginacaoReal };
  }

  raiz.Leitura = { carregar };
})(self);
