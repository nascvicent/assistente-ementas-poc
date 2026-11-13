"""Representação do voto já convertido em texto por página."""
import hashlib
from dataclasses import dataclass, field
from enum import StrEnum


class Secao(StrEnum):
    PREAMBULO = "preambulo"
    RELATORIO = "relatorio"
    VOTO = "voto"
    DISPOSITIVO = "dispositivo"
    EMENTA = "ementa"


@dataclass
class Pagina:
    numero: int
    texto: str
    secao: Secao | None = None


@dataclass
class Documento:
    nome: str
    formato: str
    hash_arquivo: str
    paginas: list[Pagina]
    avisos: list[str] = field(default_factory=list)
    paginacao_real: bool = True  # False quando o formato não traz páginas (TXT/DOCX sem quebras)

    def texto_paginado(self) -> str:
        """Texto com marcadores [[p. N]] no início de cada página (convenção do doc 04, Parte B)."""
        return "\n\n".join(f"[[p. {p.numero}]]\n{p.texto}" for p in self.paginas)

    def por_pagina(self) -> dict[int, str]:
        return {p.numero: p.texto for p in self.paginas}

    @property
    def texto(self) -> str:
        return "\n".join(p.texto for p in self.paginas)


def hash_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()
