"""Testes do linter. Os casos de desvio reproduzem, com texto fictício, os padrões
observados no Diário Eletrônico (documento 02, seção 3)."""
from app.dominio.enumeracoes import Gravidade
from app.verificadores.linter_ementa import (
    ContextoLinter, TermoCabecalho, analisar, contar_frases, verificar,
)
from tests.conftest import EMENTA_VALIDA, VOTO_FICTICIO


def codigos(achados):
    return {a.codigo for a in achados}


def voto_texto():
    return "\n".join(VOTO_FICTICIO.values())


# --- análise ---------------------------------------------------------------

def test_analisar_separa_cabecalho_secoes_e_itens():
    e = analisar(EMENTA_VALIDA)
    assert e.segmentos[0] == "AUDITORIA ESPECIAL"
    assert [s.titulo for s in e.secoes] == ["CASO EM EXAME", "RAZÕES DE DECIDIR", "DISPOSITIVO", "TESE DE JULGAMENTO"]
    assert [i.numero for s in e.secoes for i in s.itens] == [1, 2, 3, 4, 5]


def test_ementa_valida_sem_achados():
    assert verificar(EMENTA_VALIDA) == []


def test_ementa_valida_com_contexto_completo(ficha):
    ctx = ContextoLinter(
        ficha=ficha,
        texto_voto=voto_texto(),
        termos_cabecalho=[TermoCabecalho("VACINAÇÃO", "t10"), TermoCabecalho("ARMAZENAMENTO DE IMUNOBIOLÓGICOS", fora_do_tesauro=True, confirmado_pelo_usuario=True)],
        rotulos_tesauro={"Vacinação", "Saúde"},
    )
    assert verificar(EMENTA_VALIDA, ctx) == []


def test_contar_frases_ignora_abreviacoes():
    assert contar_frases("Conforme o art. 75 da Lei nº 14.133/2021, a dispensa exige justificativa.") == 1
    assert contar_frases("Primeira frase. Segunda frase. Terceira. Quarta.") == 4


# --- E01 / E02 / E03 ------------------------------------------------------

def test_e01_sem_prefixo():
    assert "E01" in codigos(verificar(EMENTA_VALIDA.replace("EMENTA: ", "", 1)))


def test_e02_minusculas_e_travessao():
    texto = EMENTA_VALIDA.replace("AUDITORIA ESPECIAL. CONFORMIDADE.", "AUDITORIA ESPECIAL – Conformidade.")
    msgs = [a.mensagem for a in verificar(texto) if a.codigo == "E02"]
    assert any("maiúsculas" in m for m in msgs)
    assert any("travessão" in m for m in msgs)


def test_e02_sem_ponto_final():
    texto = EMENTA_VALIDA.replace("REGULARIDADE COM RESSALVAS.\n", "REGULARIDADE COM RESSALVAS\n")
    assert "E02" in codigos(verificar(texto))


def test_e03_modalidade_desconhecida():
    texto = EMENTA_VALIDA.replace("AUDITORIA ESPECIAL. CONFORMIDADE.", "SAÚDE PÚBLICA. CONFORMIDADE.")
    assert "E03" in codigos(verificar(texto))


def test_e03_modalidade_diferente_da_ficha(ficha):
    texto = EMENTA_VALIDA.replace("AUDITORIA ESPECIAL.", "MEDIDA CAUTELAR.")
    assert "E03" in codigos(verificar(texto, ContextoLinter(ficha=ficha)))


# --- E04 / E05 -------------------------------------------------------------

def test_e04_questao_em_discussao_e_dispositivo_e_tese():
    texto = """EMENTA: CONSULTA. CONTRATAÇÃO DIRETA. RESPOSTA.
I. CASO EM EXAME
1. Consulta sobre contratação direta.
II. QUESTÃO EM DISCUSSÃO
2. Saber se é possível.
III. RAZÕES DE DECIDIR
3. É possível.
IV. DISPOSITIVO E TESE
4. Consulta respondida.
"""
    msgs = [a.mensagem for a in verificar(texto) if a.codigo == "E04"]
    assert any("Questão em discussão" in m for m in msgs)
    assert any("separadas" in m for m in msgs)


def test_e04_titulo_tese_curto_e_baixa():
    texto = EMENTA_VALIDA.replace("IV. TESE DE JULGAMENTO", "IV. TESE")
    e04 = [a for a in verificar(texto) if a.codigo == "E04"]
    assert len(e04) == 1 and e04[0].gravidade is Gravidade.BAIXA


def test_e04_tese_dispensavel():
    texto = EMENTA_VALIDA.split("IV. TESE")[0]
    assert "E04" not in codigos(verificar(texto))


def test_e05_numeracao_duplicada():
    # Desvio observado em admissão de pessoal: "1. 1.", "2. 2."
    texto = EMENTA_VALIDA.replace("1. Auditoria", "1. 1. Auditoria").replace("2. O armazenamento", "2. 2. O armazenamento")
    e05 = [a for a in verificar(texto) if a.codigo == "E05"]
    assert len(e05) == 2


def test_e05_numeracao_reiniciada_por_secao():
    texto = EMENTA_VALIDA.replace("2. O armazenamento", "1. O armazenamento").replace("3. A adoção", "2. A adoção")
    assert "E05" in codigos(verificar(texto))


def test_e05_teses_como_letras_dentro_de_item():
    texto = EMENTA_VALIDA.replace(
        "5. O armazenamento de vacinas em refrigeradores domésticos viola as normas sanitárias da rede de frio.",
        "5. Teses:\na. Primeira tese.\nb. Segunda tese.",
    )
    e = analisar(texto)
    assert e.secoes[3].itens[0].texto.startswith("Teses: a. Primeira")


# --- E06 / E07 --------------------------------------------------------------

def test_e06_trata_se_de():
    texto = EMENTA_VALIDA.replace("1. Auditoria Especial", "1. Trata-se de Auditoria Especial")
    assert "E06" in codigos(verificar(texto))


def test_e07_varios_fundamentos_no_mesmo_item():
    # Desvio observado em cautelar: probabilidade do direito, perigo da demora e proporcionalidade num item.
    texto = EMENTA_VALIDA.replace(
        "2. O armazenamento de vacinas em refrigeradores domésticos contraria a RDC ANVISA nº 197/2017.",
        "2. Há probabilidade do direito. Há perigo da demora. A medida é proporcional. O interesse público prevalece.",
    )
    assert "E07" in codigos(verificar(texto))


# --- E08 / E09 --------------------------------------------------------------

def test_e08_expressao_nao_padronizada():
    texto = EMENTA_VALIDA.replace("Julgamento pela regularidade com ressalvas", "Aprovou-se a auditoria com ressalvas")
    assert "E08" in codigos(verificar(texto))


def test_e08_modalidade_a_definir_nao_avalia():
    texto = EMENTA_VALIDA.replace("AUDITORIA ESPECIAL.", "CONSULTA.").replace("Julgamento pela regularidade com ressalvas", "Resposta ao consulente")
    assert "E08" not in codigos(verificar(texto))


def test_e09_dispositivo_divergente_da_ficha(ficha):
    texto = EMENTA_VALIDA.replace("regularidade com ressalvas do objeto", "irregularidade do objeto")
    msgs = [a.mensagem for a in verificar(texto, ContextoLinter(ficha=ficha)) if a.codigo == "E09"]
    assert any("REGULAR_COM_RESSALVAS" in m and "não aparece" in m for m in msgs)
    assert any("IRREGULAR" in m for m in msgs)


# --- E10 / E11 --------------------------------------------------------------

def test_e10_tese_com_municipio_valor_e_processo(ficha):
    texto = EMENTA_VALIDA.replace(
        "5. O armazenamento",
        "5. Em Vila Serena, no Processo nº 99000001-0, o gasto de R$ 1.000,00 com o armazenamento",
    )
    e10 = [a for a in verificar(texto, ContextoLinter(ficha=ficha)) if a.codigo == "E10"]
    assert len(e10) >= 3


def test_e11_marcas_de_caso_concreto():
    # Desvio observado em cautelar: "em análise preliminar"
    texto = EMENTA_VALIDA.replace("5. O armazenamento", "5. Em análise preliminar, no caso, o armazenamento")
    e11 = [a for a in verificar(texto) if a.codigo == "E11"]
    assert len(e11) == 2


# --- E12 / E13 --------------------------------------------------------------

def test_e12_norma_inexistente_no_voto():
    texto = EMENTA_VALIDA.replace("contraria a RDC ANVISA nº 197/2017", "contraria a Lei nº 14.133/2021, art. 75")
    e12 = [a for a in verificar(texto, ContextoLinter(texto_voto=voto_texto())) if a.codigo == "E12"]
    assert [a.referencia for a in e12] == ["Lei nº 14.133/2021"]


def test_e12_norma_com_grafia_diferente_no_voto():
    voto = "Aplica-se a Lei Federal nº 14133, de 1º de abril de 2021."
    texto = EMENTA_VALIDA.replace("a RDC ANVISA nº 197/2017", "a Lei nº 14.133/2021")
    assert "E12" not in codigos(verificar(texto, ContextoLinter(texto_voto=voto)))


def test_e12_ignora_portaria_de_ementas():
    texto = EMENTA_VALIDA.replace(
        "5. O armazenamento de vacinas em refrigeradores domésticos viola as normas sanitárias da rede de frio.",
        "5. Tese de julgamento dispensada (art. 8º, parágrafo único, da Portaria Normativa TC nº 322/2026).",
    )
    assert "E12" not in codigos(verificar(texto, ContextoLinter(texto_voto=voto_texto())))


def test_e13_valor_percentual_e_data():
    texto = EMENTA_VALIDA.replace("afasta a aplicação de multa", "afasta multa de R$ 1.500,00, apesar de 72,37% de perdas em 05/03/2024")
    refs = {a.referencia for a in verificar(texto, ContextoLinter(texto_voto=voto_texto())) if a.codigo == "E13"}
    assert refs == {"R$ 1.500,00", "72,37%", "05/03/2024"}


def test_e13_valor_presente_no_voto():
    voto = "multa no valor de R$ 1.500,00 em 5/3/2024"
    texto = EMENTA_VALIDA.replace("afasta a aplicação de multa", "afasta multa de R$ 1.500,00 aplicada em 05/03/2024")
    assert "E13" not in codigos(verificar(texto, ContextoLinter(texto_voto=voto)))


# --- E14 / E21 --------------------------------------------------------------

def test_e14_termo_inexistente_no_tesauro():
    ctx = ContextoLinter(termos_cabecalho=[TermoCabecalho("VACINAÇÃO", "t10")], rotulos_tesauro={"Imunização"})
    assert "E14" in codigos(verificar(EMENTA_VALIDA, ctx))


def test_e14_termo_ausente_do_cabecalho():
    ctx = ContextoLinter(termos_cabecalho=[TermoCabecalho("IMUNIZAÇÃO", "t11")], rotulos_tesauro={"Imunização"})
    assert "E14" in codigos(verificar(EMENTA_VALIDA, ctx))


def test_e21_termo_livre_nao_confirmado():
    ctx = ContextoLinter(termos_cabecalho=[TermoCabecalho("ARMAZENAMENTO DE IMUNOBIOLÓGICOS", fora_do_tesauro=True)])
    assert "E21" in codigos(verificar(EMENTA_VALIDA, ctx))


# --- E15 / E16 / E17 / E18 / E19 / E20 --------------------------------------

def test_e15_numero_e_ano_mal_formatados():
    texto = EMENTA_VALIDA.replace("a RDC ANVISA nº 197/2017", "a Lei n. 8.666/93")
    e15 = [a for a in verificar(texto) if a.codigo == "E15"]
    assert len(e15) == 2


def test_e16_carta_magna():
    texto = EMENTA_VALIDA.replace("contraria a RDC", "contraria a Carta Magna e a RDC")
    assert "E16" in codigos(verificar(texto))


def test_e17_cabecalho_longo():
    # Desvio observado em admissão de pessoal: 13+ segmentos.
    cab = ". ".join(["ADMISSÃO DE PESSOAL"] + [f"TERMO {i}" for i in range(12)]) + "."
    texto = EMENTA_VALIDA.replace(EMENTA_VALIDA.split("\n")[0], "EMENTA: " + cab)
    assert "E17" in codigos(verificar(texto))


def test_e18_oracao_no_cabecalho():
    texto = EMENTA_VALIDA.replace("VACINAÇÃO.", "O ARMAZENAMENTO EM GELADEIRA DOMÉSTICA CONFIGURA IRREGULARIDADE.")
    assert "E18" in codigos(verificar(texto))


def test_e19_adjetivo_valorativo():
    texto = EMENTA_VALIDA.replace("para avaliar a rede", "diante de flagrante descaso com a rede")
    assert "E19" in codigos(verificar(texto))


def test_e20_nome_de_pessoa(ficha):
    texto = EMENTA_VALIDA.replace("3. A adoção", "3. A adoção, pelo gestor Fulano de Tal,")
    e20 = [a for a in verificar(texto, ContextoLinter(ficha=ficha)) if a.codigo == "E20"]
    assert [a.referencia for a in e20] == ["Fulano de Tal"]


def test_ordenacao_por_gravidade():
    texto = EMENTA_VALIDA.replace("EMENTA: ", "").replace("contraria a RDC", "contraria a Carta Magna e a RDC")
    achados = verificar(texto)
    assert achados[0].gravidade is Gravidade.ALTA
    assert achados[-1].gravidade is Gravidade.BAIXA
