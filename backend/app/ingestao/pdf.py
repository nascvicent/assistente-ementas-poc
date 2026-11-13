"""PDF → texto por página (PyMuPDF)."""
import pymupdf

MINIMO_CARACTERES_POR_PAGINA = 20


def extrair_paginas(dados: bytes) -> tuple[list[str], list[str]]:
    """Devolve (textos por página, avisos). Acusa páginas sem camada de texto."""
    avisos: list[str] = []
    with pymupdf.open(stream=dados, filetype="pdf") as doc:
        paginas = [p.get_text("text", sort=True) for p in doc]
    sem_texto = [i + 1 for i, t in enumerate(paginas) if len(t.strip()) < MINIMO_CARACTERES_POR_PAGINA]
    if paginas and len(sem_texto) == len(paginas):
        avisos.append("PDF sem camada de texto (provavelmente digitalizado). É preciso OCR antes de continuar.")
    elif sem_texto:
        avisos.append(f"Páginas sem texto extraível: {', '.join(map(str, sem_texto))}.")
    return paginas, avisos
