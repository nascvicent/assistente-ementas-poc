"""Enumerações de domínio (documento 02, seção 6).

RASCUNHO: conferir a lista de modalidades com o Regimento Interno e a Lei Orgânica
do TCE-PE antes de fixar (pendência registrada no documento 02).
"""
from enum import StrEnum


class Modalidade(StrEnum):
    AUDITORIA_ESPECIAL = "AUDITORIA_ESPECIAL"
    PRESTACAO_CONTAS_GOVERNO = "PRESTACAO_CONTAS_GOVERNO"
    PRESTACAO_CONTAS_GESTAO = "PRESTACAO_CONTAS_GESTAO"
    TOMADA_CONTAS_ESPECIAL = "TOMADA_CONTAS_ESPECIAL"
    MEDIDA_CAUTELAR = "MEDIDA_CAUTELAR"
    ADMISSAO_PESSOAL = "ADMISSAO_PESSOAL"
    APOSENTADORIA = "APOSENTADORIA"
    PENSAO = "PENSAO"
    DENUNCIA = "DENUNCIA"
    REPRESENTACAO = "REPRESENTACAO"
    CONSULTA = "CONSULTA"
    GESTAO_FISCAL = "GESTAO_FISCAL"
    TERMO_AJUSTE_GESTAO = "TERMO_AJUSTE_GESTAO"
    RECURSO_ORDINARIO = "RECURSO_ORDINARIO"
    AGRAVO = "AGRAVO"
    EMBARGOS_DECLARACAO = "EMBARGOS_DECLARACAO"
    PEDIDO_RESCISAO = "PEDIDO_RESCISAO"


class Resultado(StrEnum):
    REGULAR = "REGULAR"
    REGULAR_COM_RESSALVAS = "REGULAR_COM_RESSALVAS"
    IRREGULAR = "IRREGULAR"
    APROVACAO = "APROVACAO"
    APROVACAO_COM_RESSALVAS = "APROVACAO_COM_RESSALVAS"
    REJEICAO = "REJEICAO"
    LEGAL = "LEGAL"
    ILEGAL = "ILEGAL"
    CAUTELAR_CONCEDIDA = "CAUTELAR_CONCEDIDA"
    CAUTELAR_NAO_CONCEDIDA = "CAUTELAR_NAO_CONCEDIDA"
    NAO_CONHECIDO = "NAO_CONHECIDO"
    PROVIDO = "PROVIDO"
    PARCIALMENTE_PROVIDO = "PARCIALMENTE_PROVIDO"
    NAO_PROVIDO = "NAO_PROVIDO"
    ACOLHIDOS = "ACOLHIDOS"
    REJEITADOS = "REJEITADOS"
    PROCEDENTE = "PROCEDENTE"
    IMPROCEDENTE = "IMPROCEDENTE"
    ARQUIVAMENTO = "ARQUIVAMENTO"


class Providencia(StrEnum):
    DETERMINACOES = "DETERMINACOES"
    RECOMENDACOES = "RECOMENDACOES"
    CIENCIA = "CIENCIA"
    MULTA = "MULTA"
    DEBITO = "DEBITO"
    REMESSA_MP = "REMESSA_MP"
    REGISTRO = "REGISTRO"
    NEGATIVA_REGISTRO = "NEGATIVA_REGISTRO"


class Alteracao(StrEnum):
    """Alteração de multa/débito em grau de recurso."""
    MANUTENCAO = "MANUTENCAO"
    REDUCAO = "REDUCAO"
    EXCLUSAO = "EXCLUSAO"
    MAJORACAO = "MAJORACAO"


class SituacaoConsequencia(StrEnum):
    APLICADA = "APLICADA"
    NAO_APLICADA = "NAO_APLICADA"


class OrgaoJulgador(StrEnum):
    PLENO = "PLENO"
    PRIMEIRA_CAMARA = "PRIMEIRA_CAMARA"
    SEGUNDA_CAMARA = "SEGUNDA_CAMARA"


class FonteFundamento(StrEnum):
    """Origem do fundamento (doc 04, B1): pareceres só contam se adotados pelo voto."""
    VOTO = "voto"
    PARECER_MPC = "parecer_mpc"
    RELATORIO_AUDITORIA = "relatorio_auditoria"


class Gravidade(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


# Rótulo da modalidade no cabeçalho (primeiro segmento). Variantes aceitas pelo linter.
# PROVISÓRIO: inferido do Diário de 13/11/2026; confirmar com a Diretoria de Julgamento.
ROTULOS_MODALIDADE: dict[Modalidade, tuple[str, ...]] = {
    Modalidade.AUDITORIA_ESPECIAL: ("AUDITORIA ESPECIAL",),
    Modalidade.PRESTACAO_CONTAS_GOVERNO: ("PRESTAÇÃO DE CONTAS DE GOVERNO", "PRESTAÇÃO DE CONTAS", "CONTAS DE GOVERNO"),
    Modalidade.PRESTACAO_CONTAS_GESTAO: ("PRESTAÇÃO DE CONTAS DE GESTÃO", "PRESTAÇÃO DE CONTAS", "CONTAS DE GESTÃO"),
    Modalidade.TOMADA_CONTAS_ESPECIAL: ("TOMADA DE CONTAS ESPECIAL",),
    Modalidade.MEDIDA_CAUTELAR: ("MEDIDA CAUTELAR",),
    Modalidade.ADMISSAO_PESSOAL: ("ADMISSÃO DE PESSOAL",),
    Modalidade.APOSENTADORIA: ("APOSENTADORIA",),
    Modalidade.PENSAO: ("PENSÃO",),
    Modalidade.DENUNCIA: ("DENÚNCIA",),
    Modalidade.REPRESENTACAO: ("REPRESENTAÇÃO",),
    Modalidade.CONSULTA: ("CONSULTA",),
    Modalidade.GESTAO_FISCAL: ("GESTÃO FISCAL", "PROCESSO DE GESTÃO FISCAL"),
    Modalidade.TERMO_AJUSTE_GESTAO: ("TERMO DE AJUSTE DE GESTÃO",),
    Modalidade.RECURSO_ORDINARIO: ("RECURSO ORDINÁRIO",),
    Modalidade.AGRAVO: ("AGRAVO",),
    Modalidade.EMBARGOS_DECLARACAO: ("EMBARGOS DE DECLARAÇÃO",),
    Modalidade.PEDIDO_RESCISAO: ("PEDIDO DE RESCISÃO",),
}


def modalidade_por_rotulo(rotulo: str) -> list[Modalidade]:
    """Modalidades cujo rótulo de cabeçalho coincide com `rotulo` (pode haver mais de uma)."""
    r = rotulo.strip().upper()
    return [m for m, rotulos in ROTULOS_MODALIDADE.items() if r in rotulos]
