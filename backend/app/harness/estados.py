"""Máquina de estados do fluxo (documento 01, seção 3.1).

A ordem das etapas é decidida aqui, nunca pelo modelo (princípio 1).

    AGUARDANDO_VOTO → EXTRAINDO → AGUARDANDO_OCORRENCIA → PROPONDO_TESES
    → AGUARDANDO_TESE → BUSCANDO_TERMOS → AGUARDANDO_TERMO → MONTANDO
    → AGUARDANDO_MAIS_OCORRENCIA ─sim→ AGUARDANDO_OCORRENCIA
                                  └não→ VERIFICANDO → CONCLUIDA

Estados AGUARDANDO_* aceitam: opção válida, pergunta sobre o caso, voltar, cancelar.
Estados de processamento aceitam: concluir ou falhar. Falha devolve ao último estado
de espera, sem perder o trabalho anterior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Callable


class Estado(StrEnum):
    AGUARDANDO_VOTO = "AGUARDANDO_VOTO"
    EXTRAINDO = "EXTRAINDO"
    AGUARDANDO_OCORRENCIA = "AGUARDANDO_OCORRENCIA"
    PROPONDO_TESES = "PROPONDO_TESES"
    AGUARDANDO_TESE = "AGUARDANDO_TESE"
    BUSCANDO_TERMOS = "BUSCANDO_TERMOS"
    AGUARDANDO_TERMO = "AGUARDANDO_TERMO"
    MONTANDO = "MONTANDO"
    AGUARDANDO_MAIS_OCORRENCIA = "AGUARDANDO_MAIS_OCORRENCIA"
    VERIFICANDO = "VERIFICANDO"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"

    @property
    def aguardando_usuario(self) -> bool:
        return self.name.startswith("AGUARDANDO_")

    @property
    def processando(self) -> bool:
        return self in ESTADOS_PROCESSAMENTO

    @property
    def final(self) -> bool:
        return self in (Estado.CONCLUIDA, Estado.CANCELADA)


ESTADOS_PROCESSAMENTO = {
    Estado.EXTRAINDO, Estado.PROPONDO_TESES, Estado.BUSCANDO_TERMOS, Estado.MONTANDO, Estado.VERIFICANDO,
}

# Tempo limite (s) e tentativas por estado de processamento; usados pelo executor de etapas.
TEMPO_LIMITE_S = {
    Estado.EXTRAINDO: 180, Estado.PROPONDO_TESES: 60, Estado.BUSCANDO_TERMOS: 60,
    Estado.MONTANDO: 90, Estado.VERIFICANDO: 120,
}
MAX_TENTATIVAS = 2


class Acao(StrEnum):
    ENVIAR_VOTO = "ENVIAR_VOTO"
    CONCLUIR = "CONCLUIR"              # etapa de processamento terminou bem
    FALHAR = "FALHAR"                  # etapa de processamento esgotou tentativas
    ESCOLHER = "ESCOLHER"              # opção válida em estado de espera
    DISPENSAR_TESE = "DISPENSAR_TESE"  # art. 8º, p.u., da Portaria 322/2026
    PEDIR_NOVAS_TESES = "PEDIR_NOVAS_TESES"
    ADICIONAR_OCORRENCIA = "ADICIONAR_OCORRENCIA"
    ENCERRAR = "ENCERRAR"              # "não" a "adicionar outra ocorrência?"
    PERGUNTAR = "PERGUNTAR"            # conversa sobre o caso: não muda de estado
    VOLTAR = "VOLTAR"
    CANCELAR = "CANCELAR"


@dataclass
class ContextoFluxo:
    """Dados de que as guardas de transição precisam."""
    ocorrencia_unica: bool = False      # atalho para casos simples (pula a etapa 3 e o laço)
    ocorrencias_restantes: int | None = None


class TransicaoInvalida(Exception):
    def __init__(self, estado: Estado, acao: Acao):
        super().__init__(f"Ação {acao} não é aceita no estado {estado}.")
        self.estado, self.acao = estado, acao


Destino = Estado | Callable[[ContextoFluxo], Estado]


def _apos_extracao(ctx: ContextoFluxo) -> Estado:
    return Estado.PROPONDO_TESES if ctx.ocorrencia_unica else Estado.AGUARDANDO_OCORRENCIA


def _apos_montagem(ctx: ContextoFluxo) -> Estado:
    if ctx.ocorrencia_unica or ctx.ocorrencias_restantes == 0:
        return Estado.VERIFICANDO
    return Estado.AGUARDANDO_MAIS_OCORRENCIA


def _voltar_da_tese(ctx: ContextoFluxo) -> Estado:
    return Estado.AGUARDANDO_VOTO if ctx.ocorrencia_unica else Estado.AGUARDANDO_OCORRENCIA


TRANSICOES: dict[tuple[Estado, Acao], Destino] = {
    (Estado.AGUARDANDO_VOTO, Acao.ENVIAR_VOTO): Estado.EXTRAINDO,
    (Estado.EXTRAINDO, Acao.CONCLUIR): _apos_extracao,
    (Estado.AGUARDANDO_OCORRENCIA, Acao.ESCOLHER): Estado.PROPONDO_TESES,
    (Estado.PROPONDO_TESES, Acao.CONCLUIR): Estado.AGUARDANDO_TESE,
    (Estado.AGUARDANDO_TESE, Acao.ESCOLHER): Estado.BUSCANDO_TERMOS,
    (Estado.AGUARDANDO_TESE, Acao.DISPENSAR_TESE): Estado.BUSCANDO_TERMOS,
    (Estado.AGUARDANDO_TESE, Acao.PEDIR_NOVAS_TESES): Estado.PROPONDO_TESES,
    (Estado.BUSCANDO_TERMOS, Acao.CONCLUIR): Estado.AGUARDANDO_TERMO,
    (Estado.AGUARDANDO_TERMO, Acao.ESCOLHER): Estado.MONTANDO,
    (Estado.MONTANDO, Acao.CONCLUIR): _apos_montagem,
    (Estado.AGUARDANDO_MAIS_OCORRENCIA, Acao.ADICIONAR_OCORRENCIA): Estado.AGUARDANDO_OCORRENCIA,
    (Estado.AGUARDANDO_MAIS_OCORRENCIA, Acao.ENCERRAR): Estado.VERIFICANDO,
    (Estado.VERIFICANDO, Acao.CONCLUIR): Estado.CONCLUIDA,
    # voltar uma etapa
    (Estado.AGUARDANDO_OCORRENCIA, Acao.VOLTAR): Estado.AGUARDANDO_VOTO,
    (Estado.AGUARDANDO_TESE, Acao.VOLTAR): _voltar_da_tese,
    (Estado.AGUARDANDO_TERMO, Acao.VOLTAR): Estado.AGUARDANDO_TESE,
    (Estado.AGUARDANDO_MAIS_OCORRENCIA, Acao.VOLTAR): Estado.AGUARDANDO_TERMO,
}


@dataclass(frozen=True)
class Transicao:
    de: Estado
    acao: Acao
    para: Estado
    quando: datetime


@dataclass
class MaquinaFluxo:
    estado: Estado = Estado.AGUARDANDO_VOTO
    contexto: ContextoFluxo = field(default_factory=ContextoFluxo)
    ultimo_estado_espera: Estado = Estado.AGUARDANDO_VOTO
    historico: list[Transicao] = field(default_factory=list)
    ao_transitar: Callable[[Transicao], None] | None = None  # ex.: gravar evento

    def aceita(self, acao: Acao) -> bool:
        return self._destino(acao) is not None

    def acoes_permitidas(self) -> list[Acao]:
        return [a for a in Acao if self.aceita(a)]

    def _destino(self, acao: Acao) -> Estado | None:
        e = self.estado
        if e.final:
            return None
        if acao is Acao.CANCELAR:
            return Estado.CANCELADA
        if acao is Acao.PERGUNTAR:
            return e if e.aguardando_usuario else None
        if acao is Acao.FALHAR:
            return self.ultimo_estado_espera if e.processando else None
        destino = TRANSICOES.get((e, acao))
        if destino is None:
            return None
        return destino(self.contexto) if callable(destino) else destino

    def disparar(self, acao: Acao) -> Estado:
        destino = self._destino(acao)
        if destino is None:
            raise TransicaoInvalida(self.estado, acao)
        t = Transicao(self.estado, acao, destino, datetime.now(timezone.utc))
        if self.estado.aguardando_usuario:
            self.ultimo_estado_espera = self.estado
        self.estado = destino
        if destino.aguardando_usuario:
            self.ultimo_estado_espera = destino
        self.historico.append(t)
        if self.ao_transitar:
            self.ao_transitar(t)
        return destino
