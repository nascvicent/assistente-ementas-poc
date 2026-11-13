"""Ingestão do voto: arquivo → Documento (texto por página, sem o bloco de ementa)."""
from pathlib import Path

from app.ingestao.documento import Documento, Pagina, hash_bytes
from app.ingestao.limpeza import limpar
from app.ingestao.secoes import BlocoEmenta, detectar_secoes, remover_ementa

FORMATOS = {".pdf": "pdf", ".docx": "docx", ".odt": "odt", ".txt": "txt"}


class FormatoNaoSuportado(ValueError):
    pass


def _paginas_txt(dados: bytes) -> tuple[list[str], list[str], bool]:
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
    if "\f" in texto:
        return texto.split("\f"), [], True
    return [texto], ["TXT sem marcas de página: o texto foi tratado como página única; as citações usarão p. 1."], False


def carregar_bytes(dados: bytes, nome: str) -> tuple[Documento, BlocoEmenta | None]:
    formato = FORMATOS.get(Path(nome).suffix.lower())
    if formato is None:
        raise FormatoNaoSuportado(f"Formato não suportado: {nome}. Use PDF, DOCX, ODT ou TXT.")

    paginacao_real = True
    if formato == "pdf":
        from app.ingestao import pdf
        brutas, avisos = pdf.extrair_paginas(dados)
    elif formato == "docx":
        from app.ingestao import docx
        brutas, avisos, paginacao_real = docx.extrair_paginas(dados)
    elif formato == "odt":
        from app.ingestao import odt
        brutas, avisos, paginacao_real = odt.extrair_paginas(dados)
    else:
        brutas, avisos, paginacao_real = _paginas_txt(dados)

    textos = limpar(brutas)
    doc = Documento(
        nome=nome,
        formato=formato,
        hash_arquivo=hash_bytes(dados),
        paginas=[Pagina(i + 1, t) for i, t in enumerate(textos)],
        avisos=avisos,
        paginacao_real=paginacao_real,
    )
    doc, bloco = remover_ementa(doc)
    return detectar_secoes(doc), bloco


def carregar_arquivo(caminho: str | Path) -> tuple[Documento, BlocoEmenta | None]:
    caminho = Path(caminho)
    return carregar_bytes(caminho.read_bytes(), caminho.name)


def carregar_texto(texto: str, nome: str = "colado.txt") -> tuple[Documento, BlocoEmenta | None]:
    """Texto colado pelo usuário."""
    return carregar_bytes(texto.encode("utf-8"), nome)
