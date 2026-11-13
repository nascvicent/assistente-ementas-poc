"""Normalização de texto compartilhada pelos verificadores."""
import re
import unicodedata

_ASPAS = str.maketrans({
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
    "‘": "'", "’": "'", "‚": "'", "´": "'", "`": "'",
    "–": "-", "—": "-", "‒": "-", "−": "-",
    " ": " ", " ": " ", " ": " ",
    "°": "º",
})

_HIFEN_QUEBRA = re.compile(r"(\w)-\s*\n\s*(\w)")
_SOFT_HYPHEN = "­"


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def normalizar(texto: str, *, tirar_acento: bool = False) -> str:
    """Forma canônica para comparação tolerante.

    - unifica aspas, travessões e espaços especiais;
    - junta palavras hifenizadas na quebra de linha;
    - colapsa espaços e quebras; minúsculas.
    """
    t = unicodedata.normalize("NFKC", texto).replace(_SOFT_HYPHEN, "")
    t = t.translate(_ASPAS)
    t = _HIFEN_QUEBRA.sub(r"\1\2", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    if tirar_acento:
        t = sem_acento(t)
    return t


def normalizar_para_busca(texto: str) -> str:
    """Mais agressiva: sem acento e sem pontuação (exceto dígitos com separadores)."""
    t = normalizar(texto, tirar_acento=True)
    t = re.sub(r"[\"'()\[\]{};:!?]", " ", t)
    t = re.sub(r"(?<!\d)[.,](?!\d)", " ", t)
    return re.sub(r"\s+", " ", t).strip()
