"""Fixtures compartilhadas. Todos os dados são FICTÍCIOS."""
import pytest

from app.dominio.enumeracoes import Modalidade, OrgaoJulgador, Providencia, Resultado, SituacaoConsequencia
from app.esquemas.ficha import (
    Citacao, Consequencias, Evidencia, Ficha, Fundamento, Julgamento, Ocorrencia, Processo, Votacao,
)

EMENTA_VALIDA = """EMENTA: AUDITORIA ESPECIAL. CONFORMIDADE. SAÚDE. VACINAÇÃO. ARMAZENAMENTO DE IMUNOBIOLÓGICOS. REGULARIDADE COM RESSALVAS.
I. CASO EM EXAME
1. Auditoria Especial de Conformidade realizada na Secretaria de Saúde de município fictício, nos exercícios de 2023 a 2025, para avaliar a rede de frio de imunobiológicos.
II. RAZÕES DE DECIDIR
2. O armazenamento de vacinas em refrigeradores domésticos contraria a RDC ANVISA nº 197/2017.
3. A adoção de providências corretivas no curso da auditoria afasta a aplicação de multa.
III. DISPOSITIVO
4. Julgamento pela regularidade com ressalvas do objeto da Auditoria Especial, com expedição de determinações.
IV. TESE DE JULGAMENTO
5. O armazenamento de vacinas em refrigeradores domésticos viola as normas sanitárias da rede de frio.
"""

VOTO_FICTICIO = {
    1: "RELATÓRIO\nTrata-se de auditoria especial de conformidade realizada na Secretaria de Saúde do Município de Vila Serena, exercícios de 2023 a 2025.",
    2: "VOTO\nA equipe constatou o uso de geladeiras domésticas para armazenamento de vacinas, em desacordo com a RDC ANVISA nº 197/2017. "
       "O gestor, Fulano de Tal, adotou providências corre-\ntivas durante a auditoria, o que afasta a aplicação de multa.",
    3: "Ante o exposto, VOTO pelo que segue: JULGAR regular com ressalvas o objeto da presente Auditoria Especial, com determinações.",
}


def ev(trecho: str, pagina: int) -> Evidencia:
    return Evidencia(trecho=trecho, pagina=pagina)


@pytest.fixture
def ficha() -> Ficha:
    return Ficha(
        processo=Processo(
            numero="99000001-0",
            modalidade=Modalidade.AUDITORIA_ESPECIAL,
            tipo="CONFORMIDADE",
            orgao_julgador=OrgaoJulgador.PRIMEIRA_CAMARA,
            relator="Beltrana de Souza",
            unidade_jurisdicionada="Vila Serena",
            exercicios=[2023, 2025],
        ),
        votacao=Votacao(unanime=True, evidencia=ev("JULGAR regular com ressalvas", 3)),
        ocorrencias=[
            Ocorrencia(
                id="oc1",
                titulo="USO DE GELADEIRAS DOMÉSTICAS PARA ARMAZENAMENTO DE VACINAS",
                resumo="Vacinas armazenadas em refrigeradores domésticos.",
                fundamentos=[Fundamento(texto="Contraria norma sanitária.", evidencia=ev("uso de geladeiras domésticas para armazenamento de vacinas", 2))],
                normas=[Citacao(citacao="RDC ANVISA nº 197/2017", evidencia=ev("RDC ANVISA nº 197/2017", 2))],
                consequencias=Consequencias(multa=SituacaoConsequencia.NAO_APLICADA, evidencia=ev("providências corretivas durante a auditoria", 2)),
                responsaveis=["Fulano de Tal"],
            )
        ],
        julgamento=Julgamento(
            resultado=[Resultado.REGULAR_COM_RESSALVAS],
            providencias=[Providencia.DETERMINACOES],
            evidencia=ev("JULGAR regular com ressalvas o objeto da presente Auditoria Especial", 3),
        ),
    )
