"""ODT → texto por página, usando as quebras gravadas pelo LibreOffice (text:soft-page-break)."""
import io

from odf import teletype
from odf.namespaces import TEXTNS
from odf.opendocument import load

_P = (TEXTNS, "p")
_H = (TEXTNS, "h")
_QUEBRA = (TEXTNS, "soft-page-break")


def _percorrer(no, paginas: list[list[str]], estado: dict):
    for filho in no.childNodes:
        if filho.nodeType != filho.ELEMENT_NODE:
            continue
        if filho.qname == _QUEBRA:
            paginas.append([])
            estado["quebra"] = True
        elif filho.qname in (_P, _H):
            # Quebra dentro do parágrafo: o parágrafo vai para a página nova.
            if any(getattr(n, "qname", None) == _QUEBRA for n in filho.childNodes):
                paginas.append([])
                estado["quebra"] = True
            paginas[-1].append(teletype.extractText(filho))
        else:
            _percorrer(filho, paginas, estado)


def extrair_paginas(dados: bytes) -> tuple[list[str], list[str], bool]:
    doc = load(io.BytesIO(dados))
    paginas: list[list[str]] = [[]]
    estado = {"quebra": False}
    _percorrer(doc.text, paginas, estado)
    textos = ["\n".join(p).strip() for p in paginas]
    textos = [t for t in textos if t] or [""]
    avisos = [] if estado["quebra"] else ["ODT sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."]
    return textos, avisos, estado["quebra"]
