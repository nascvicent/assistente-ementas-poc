"""Expressões padronizadas do dispositivo (documento 02, seção 4.4).

PROVISÓRIO (pendência P1): a Portaria Normativa TC nº 322/2026 (art. 7º) exige
expressões padronizadas por modalidade, mas não traz a lista. A tabela abaixo foi
inferida do Diário Eletrônico e deve ser substituída pela lista da Diretoria de
Julgamento. Modalidades sem tabela ficam como A_DEFINIR e o linter não as avalia.
"""
import re

from app.dominio.enumeracoes import Modalidade, Resultado

A_DEFINIR = None

# Padrões (regex, sem acento, minúsculas) que reconhecem cada resultado no texto do
# dispositivo. Ordem importa: os mais específicos primeiro.
PADROES_RESULTADO: dict[Resultado, str] = {
    Resultado.REGULAR_COM_RESSALVAS: r"\bregular(idade|es)? com ressalvas?\b",
    Resultado.IRREGULAR: r"\birregular(idade|es)?\b",
    Resultado.REGULAR: r"\bregular(idade|es)?\b(?! com ressalva)",
    Resultado.APROVACAO_COM_RESSALVAS: r"\baprova(cao|das?) com ressalvas?\b",
    Resultado.APROVACAO: r"\baprova(cao|das?)\b(?! com ressalva)",
    Resultado.REJEICAO: r"\brejei(cao|tadas?)\b",
    Resultado.ILEGAL: r"\bilegal(idade)?\b",
    Resultado.LEGAL: r"(?<!i)\blegal(idade)?\b",
    Resultado.CAUTELAR_NAO_CONCEDIDA: r"\bnao concess[aã]o\b|\bnao concedida\b|\bindeferi(mento|da)\b",
    Resultado.CAUTELAR_CONCEDIDA: r"(?<!nao )\bconcess[aã]o\b|(?<!nao )\bconcedida\b",
    Resultado.NAO_CONHECIDO: r"\bnao conhecid[oa]s?\b",
    Resultado.PARCIALMENTE_PROVIDO: r"\bparcialmente provid[oa]s?\b|\bprovimento parcial\b",
    Resultado.NAO_PROVIDO: r"\bnao provid[oa]s?\b|\bdesprovid[oa]s?\b|\bdesprovimento\b|\bnegad[oa] provimento\b",
    Resultado.PROVIDO: r"(?<!parcialmente )(?<!nao )\bprovid[oa]s?\b",
    Resultado.ACOLHIDOS: r"\bacolhid[oa]s?\b",
    Resultado.REJEITADOS: r"\brejeitad[oa]s?\b",
    Resultado.IMPROCEDENTE: r"\bimprocede(nte|ncia)s?\b",
    Resultado.PROCEDENTE: r"(?<!im)\bprocede(nte|ncia)s?\b",
    Resultado.ARQUIVAMENTO: r"\barquivamento\b|\barquivad[oa]\b",
}

# Expressões de abertura aceitas por modalidade (regex sobre texto sem acento, minúsculas).
EXPRESSOES_POR_MODALIDADE: dict[Modalidade, list[str] | None] = {
    Modalidade.AUDITORIA_ESPECIAL: [r"julgamento pela (ir)?regularidade"],
    Modalidade.PRESTACAO_CONTAS_GOVERNO: [r"parecer previo pela (aprovacao|rejeicao)"],
    Modalidade.PRESTACAO_CONTAS_GESTAO: [r"contas julgadas (ir)?regulares", r"julgamento pela (ir)?regularidade"],
    Modalidade.MEDIDA_CAUTELAR: [r"homolog\w* (d[ao] )?(nao )?concess", r"referend\w*"],
    Modalidade.ADMISSAO_PESSOAL: [r"(i)?legalidade", r"registro"],
    Modalidade.APOSENTADORIA: [r"(i)?legalidade", r"registro"],
    Modalidade.PENSAO: [r"(i)?legalidade", r"registro"],
    Modalidade.RECURSO_ORDINARIO: [r"recurso (nao )?conhecido"],
    Modalidade.AGRAVO: [r"(recurso|agravo) (nao )?conhecido"],
    Modalidade.EMBARGOS_DECLARACAO: [r"embargos (nao )?(conhecidos|acolhidos|rejeitados)"],
    Modalidade.CONSULTA: A_DEFINIR,
    Modalidade.DENUNCIA: A_DEFINIR,
    Modalidade.REPRESENTACAO: A_DEFINIR,
    Modalidade.TOMADA_CONTAS_ESPECIAL: A_DEFINIR,
    Modalidade.TERMO_AJUSTE_GESTAO: A_DEFINIR,
    Modalidade.PEDIDO_RESCISAO: A_DEFINIR,
    Modalidade.GESTAO_FISCAL: A_DEFINIR,
}


def resultados_no_texto(texto_sem_acento: str) -> set[Resultado]:
    """Resultados reconhecidos no texto (já normalizado: minúsculas e sem acento)."""
    achados: set[Resultado] = set()
    for resultado, padrao in PADROES_RESULTADO.items():
        if re.search(padrao, texto_sem_acento):
            achados.add(resultado)
    # Remove o genérico quando o específico já foi achado.
    if Resultado.REGULAR_COM_RESSALVAS in achados:
        achados.discard(Resultado.REGULAR)
    if Resultado.APROVACAO_COM_RESSALVAS in achados:
        achados.discard(Resultado.APROVACAO)
    return achados
