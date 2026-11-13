"""Roteador de entrada do usuário: escolha × pergunta × comando.

"Cada resposta fica vinculada à pergunta ativa do fluxo" (doc 01, seção 3): o código
classifica a entrada ANTES de chamar qualquer modelo. Só o que não for opção válida
nem comando vira pergunta sobre o caso — e pergunta não avança a etapa.
"""
import re
from dataclasses import dataclass
from enum import StrEnum

from app.harness.estados import Acao, Estado
from app.verificadores.normalizacao import normalizar


class TipoEntrada(StrEnum):
    ESCOLHA = "escolha"
    COMANDO = "comando"
    PERGUNTA = "pergunta"
    OPCAO_INVALIDA = "opcao_invalida"


@dataclass(frozen=True)
class Entrada:
    tipo: TipoEntrada
    acao: Acao | None = None
    opcao: int | None = None
    texto: str = ""


_RE_NUMERO = re.compile(r"^(?:op[cç][aã]o|alternativa|n[uú]mero|item)?\s*(\d{1,2})\s*[.)]?$")
_COMANDOS_GERAIS = {
    "voltar": Acao.VOLTAR, "voltar etapa": Acao.VOLTAR, "anterior": Acao.VOLTAR,
    "cancelar": Acao.CANCELAR,
}
_SIM = {"sim", "s", "adicionar", "mais uma", "outra", "adicionar outra"}
_NAO = {"nao", "não", "n", "encerrar", "finalizar", "concluir", "nao, encerrar", "não, encerrar"}
_COMANDOS_TESE = {
    "dispensar": Acao.DISPENSAR_TESE, "dispensar a tese": Acao.DISPENSAR_TESE, "dispensar tese": Acao.DISPENSAR_TESE,
    "sem tese": Acao.DISPENSAR_TESE, "novas teses": Acao.PEDIR_NOVAS_TESES, "gerar novas": Acao.PEDIR_NOVAS_TESES,
}


def classificar(texto: str, estado: Estado, n_opcoes: int = 0) -> Entrada:
    bruto = texto.strip()
    t = normalizar(bruto).rstrip(".!")

    if t in _COMANDOS_GERAIS:
        return Entrada(TipoEntrada.COMANDO, _COMANDOS_GERAIS[t], texto=bruto)

    if estado is Estado.AGUARDANDO_MAIS_OCORRENCIA:
        if t in _SIM:
            return Entrada(TipoEntrada.COMANDO, Acao.ADICIONAR_OCORRENCIA, texto=bruto)
        if t in _NAO:
            return Entrada(TipoEntrada.COMANDO, Acao.ENCERRAR, texto=bruto)

    if estado is Estado.AGUARDANDO_TESE and t in _COMANDOS_TESE:
        return Entrada(TipoEntrada.COMANDO, _COMANDOS_TESE[t], texto=bruto)

    m = _RE_NUMERO.match(t)
    if m and n_opcoes:
        n = int(m.group(1))
        if 1 <= n <= n_opcoes:
            return Entrada(TipoEntrada.ESCOLHA, Acao.ESCOLHER, opcao=n, texto=bruto)
        return Entrada(TipoEntrada.OPCAO_INVALIDA, opcao=n, texto=bruto)

    return Entrada(TipoEntrada.PERGUNTA, Acao.PERGUNTAR, texto=bruto)
