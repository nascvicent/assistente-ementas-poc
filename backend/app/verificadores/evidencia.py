"""Conferência de evidências da Ficha contra o texto do voto (doc 01, princípio 4 e seção 6.1).

Cada evidência é um trecho literal + página. O trecho é comparado de forma
normalizada (quebras de linha, hifenização, aspas, caixa) com a página indicada.
Se não estiver lá, procura-se na junção com a página seguinte (trecho que atravessa
a quebra de página) e, por fim, em todo o documento (página divergente).
"""
from dataclasses import dataclass

from app.esquemas.ficha import Evidencia, Ficha, StatusEvidencia
from app.verificadores.normalizacao import normalizar


@dataclass(frozen=True)
class ResultadoEvidencia:
    status: StatusEvidencia
    pagina_encontrada: int | None = None


class TextoPaginado:
    """Páginas já normalizadas, indexadas a partir de 1."""

    def __init__(self, paginas: dict[int, str]):
        self._paginas = {n: normalizar(t) for n, t in paginas.items()}

    def __contains__(self, pagina: int) -> bool:
        return pagina in self._paginas

    def pagina(self, n: int) -> str:
        return self._paginas.get(n, "")

    def numeros(self) -> list[int]:
        return sorted(self._paginas)


def conferir_trecho(trecho: str, pagina: int, texto: TextoPaginado) -> ResultadoEvidencia:
    alvo = normalizar(trecho)
    if not alvo:
        return ResultadoEvidencia(StatusEvidencia.NAO_CONFIRMADA)

    if alvo in texto.pagina(pagina):
        return ResultadoEvidencia(StatusEvidencia.CONFIRMADA, pagina)

    # Trecho que começa na página indicada e termina na seguinte.
    if _atravessa(alvo, pagina, texto):
        return ResultadoEvidencia(StatusEvidencia.CONFIRMADA, pagina)

    for n in texto.numeros():
        if n != pagina and alvo in texto.pagina(n):
            return ResultadoEvidencia(StatusEvidencia.PAGINA_DIVERGENTE, n)
    for n in texto.numeros():
        if n != pagina and _atravessa(alvo, n, texto):
            return ResultadoEvidencia(StatusEvidencia.PAGINA_DIVERGENTE, n)

    return ResultadoEvidencia(StatusEvidencia.NAO_CONFIRMADA)


def _atravessa(alvo: str, n: int, texto: TextoPaginado) -> bool:
    """O trecho começa na página n e termina na n+1 (não está inteiro em nenhuma das duas)."""
    if n not in texto or (n + 1) not in texto or alvo in texto.pagina(n + 1):
        return False
    return alvo in texto.pagina(n) + " " + texto.pagina(n + 1)


def conferir(evidencia: Evidencia, texto: TextoPaginado) -> Evidencia:
    """Devolve cópia da evidência com status e página encontrada preenchidos."""
    r = conferir_trecho(evidencia.trecho, evidencia.pagina, texto)
    return evidencia.model_copy(update={"status": r.status, "pagina_encontrada": r.pagina_encontrada})


@dataclass(frozen=True)
class ProblemaEvidencia:
    caminho: str
    trecho: str
    pagina_indicada: int
    status: StatusEvidencia
    pagina_encontrada: int | None


def conferir_ficha(ficha: Ficha, texto: TextoPaginado) -> tuple[Ficha, list[ProblemaEvidencia]]:
    """Confere todas as evidências; devolve a Ficha com status gravado e a lista de problemas.

    O chamador decide o que fazer com os problemas (nova tentativa com o erro apontado
    ou marcar o item como "não confirmado" — doc 01, seção 6.1).
    """
    ficha = ficha.model_copy(deep=True)
    problemas: list[ProblemaEvidencia] = []
    for caminho, ev in ficha.evidencias():
        r = conferir_trecho(ev.trecho, ev.pagina, texto)
        ev.status = r.status
        ev.pagina_encontrada = r.pagina_encontrada
        if r.status is not StatusEvidencia.CONFIRMADA:
            problemas.append(ProblemaEvidencia(caminho, ev.trecho, ev.pagina, r.status, r.pagina_encontrada))
    return ficha, problemas


def mensagem_para_nova_tentativa(problemas: list[ProblemaEvidencia]) -> str:
    """Texto a anexar ao prompt de extração na nova tentativa."""
    linhas = ["Os trechos abaixo não foram encontrados literalmente no texto. Copie-os exatamente ou remova o item:"]
    for p in problemas:
        onde = f" (encontrado na p. {p.pagina_encontrada})" if p.pagina_encontrada else ""
        linhas.append(f"- {p.caminho}, p. {p.pagina_indicada}{onde}: \"{p.trecho[:120]}\"")
    return "\n".join(linhas)
