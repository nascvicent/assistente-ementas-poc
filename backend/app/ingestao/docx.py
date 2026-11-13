"""DOCX → texto por página.

DOCX não guarda paginação. Usa as quebras gravadas pelo Word (lastRenderedPageBreak)
e, na falta delas, as quebras de página explícitas. Sem nenhuma, tudo vira página 1.
"""
import io

import docx as python_docx
from docx.oxml.ns import qn


def _texto_paragrafo(p) -> tuple[list[str], int]:
    """Divide o parágrafo nas quebras de página. Devolve (pedaços, nº de quebras)."""
    pedacos, atual, quebras = [], [], 0
    for el in p.iter():
        if el.tag == qn("w:t"):
            atual.append(el.text or "")
        elif el.tag == qn("w:tab"):
            atual.append("\t")
        elif el.tag == qn("w:br") and el.get(qn("w:type")) == "page" or el.tag == qn("w:lastRenderedPageBreak"):
            pedacos.append("".join(atual))
            atual, quebras = [], quebras + 1
    pedacos.append("".join(atual))
    return pedacos, quebras


def extrair_paginas(dados: bytes) -> tuple[list[str], list[str], bool]:
    doc = python_docx.Document(io.BytesIO(dados))
    paginas: list[list[str]] = [[]]
    houve_quebra = False
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            pedacos, quebras = _texto_paragrafo(el)
            paginas[-1].append(pedacos[0])
            for pedaco in pedacos[1:]:
                paginas.append([pedaco])
            houve_quebra |= quebras > 0
        elif el.tag == qn("w:tbl"):
            for linha in el.iter(qn("w:tr")):
                celulas = ["".join(t.text or "" for t in c.iter(qn("w:t"))) for c in linha.iter(qn("w:tc"))]
                paginas[-1].append(" | ".join(celulas))
    textos = ["\n".join(p).strip() for p in paginas]
    textos = [t for t in textos if t] or [""]
    avisos = [] if houve_quebra else ["DOCX sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."]
    return textos, avisos, houve_quebra
