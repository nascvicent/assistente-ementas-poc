"""Todo prompt em app/prompts/ carrega pelo gateway e declara as variáveis esperadas."""
import re

import pytest

from app.modelo.gateway import PASTA_PROMPTS, carregar_prompt

VARIAVEIS = {
    "extracao_ficha": {"modalidades", "resultados", "providencias", "voto_paginado"},
    "propor_teses": {"ponto", "normas_permitidas", "termos_proibidos", "orientacao"},
    "sugerir_termos_sem_tesauro": {"ponto", "tese"},
    "redacao_caso_razoes": {"ficha", "pontos"},
    "verificacao_final": {"voto_paginado", "pontos", "teses"},
    "conversa": {"etapa", "conteudo_em_tela", "ficha", "trechos", "pergunta"},
    "corrigir_evidencias": {"itens", "voto_paginado"},
    "prompt_unico_aurorachat": {"texto_integral"},
    "consultas_tesauro": {"ponto", "tese"},
    "ranquear_termos": {"ponto", "tese", "candidatos"},
}


def test_todos_os_prompts_estao_listados():
    assert {p.stem for p in PASTA_PROMPTS.glob("*.md")} == set(VARIAVEIS)


@pytest.mark.parametrize("nome", sorted(VARIAVEIS))
def test_prompt_carrega_e_tem_as_variaveis(nome):
    p = carregar_prompt(nome)
    assert re.fullmatch(r"(A-)?\d+\.\d+(-demo)?", p.versao)
    assert set(re.findall(r"\{\{\s*(\w+)\s*\}\}", p.texto)) == VARIAVEIS[nome]
    assert "Carta Magna" not in p.texto or nome in {"redacao_caso_razoes", "prompt_unico_aurorachat"}
    texto = p.renderizar({v: "x" for v in VARIAVEIS[nome]})
    assert "{{" not in texto
