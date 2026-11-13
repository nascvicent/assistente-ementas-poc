from app.esquemas.ficha import Evidencia, StatusEvidencia
from app.verificadores.evidencia import (
    TextoPaginado, conferir, conferir_ficha, conferir_trecho, mensagem_para_nova_tentativa,
)
from tests.conftest import VOTO_FICTICIO

TEXTO = TextoPaginado(VOTO_FICTICIO)


def test_trecho_literal_confirmado():
    r = conferir_trecho("em desacordo com a RDC ANVISA nº 197/2017", 2, TEXTO)
    assert r.status is StatusEvidencia.CONFIRMADA


def test_tolera_hifenizacao_quebra_de_linha_caixa_e_aspas():
    assert conferir_trecho("adotou providências corretivas durante a auditoria", 2, TEXTO).status is StatusEvidencia.CONFIRMADA
    assert conferir_trecho("JULGAR REGULAR COM RESSALVAS", 3, TEXTO).status is StatusEvidencia.CONFIRMADA
    t = TextoPaginado({1: "o chamado “princípio da\nmotivação” foi violado"})
    assert conferir_trecho('chamado "princípio da motivação" foi', 1, t).status is StatusEvidencia.CONFIRMADA


def test_pagina_divergente():
    r = conferir_trecho("geladeiras domésticas", 1, TEXTO)
    assert r.status is StatusEvidencia.PAGINA_DIVERGENTE and r.pagina_encontrada == 2


def test_trecho_que_atravessa_paginas():
    t = TextoPaginado({1: "A irregularidade foi", 2: "comprovada pela equipe."})
    assert conferir_trecho("irregularidade foi comprovada", 1, t).status is StatusEvidencia.CONFIRMADA


def test_trecho_inventado_ou_parafraseado():
    assert conferir_trecho("geladeiras residenciais", 2, TEXTO).status is StatusEvidencia.NAO_CONFIRMADA
    assert conferir_trecho("   ", 2, TEXTO).status is StatusEvidencia.NAO_CONFIRMADA


def test_conferir_preenche_status():
    ev = conferir(Evidencia(trecho="geladeiras domésticas", pagina=2), TEXTO)
    assert ev.status is StatusEvidencia.CONFIRMADA and ev.pagina_encontrada == 2


def test_conferir_ficha(ficha):
    ficha.ocorrencias[0].normas[0].evidencia.trecho = "Lei nº 14.133/2021"  # inventado
    conferida, problemas = conferir_ficha(ficha, TEXTO)
    assert [p.caminho for p in problemas] == ["ocorrencias[oc1].normas[0]"]
    assert conferida.julgamento.evidencia.status is StatusEvidencia.CONFIRMADA
    assert ficha.julgamento.evidencia.status is StatusEvidencia.NAO_VERIFICADA  # original intacto
    assert "normas[0]" in mensagem_para_nova_tentativa(problemas)
