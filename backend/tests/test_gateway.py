import pytest
from pydantic import BaseModel

from app.modelo.gateway import ErroSaidaModelo, GatewayModelo, PromptVersionado, ProvedorFalso, carregar_prompt


class Saida(BaseModel):
    ids: list[str]


PROMPT = PromptVersionado("teste", "0.1", "Escolha em {{candidatos}} para: {{ponto}}")


def test_renderiza_e_valida():
    eventos = []
    prov = ProvedorFalso([{"ids": ["7"]}])
    r = GatewayModelo(prov, registrar=eventos.append).gerar(PROMPT, {"candidatos": ["7", "8"], "ponto": "dispensa"}, Saida)
    assert r.saida.ids == ["7"] and r.tentativas == 1 and r.versao_prompt == "0.1"
    assert prov.recebidos[0] == 'Escolha em ["7", "8"] para: dispensa'
    assert eventos[0]["tipo"] == "chamada_modelo" and eventos[0]["versao_prompt"] == "teste@0.1"


def test_aceita_bloco_json():
    r = GatewayModelo(ProvedorFalso(['```json\n{"ids": []}\n```'])).gerar(PROMPT, {"candidatos": [], "ponto": ""}, Saida)
    assert r.saida.ids == []


def test_nova_tentativa_com_erro_apontado():
    eventos = []
    prov = ProvedorFalso(["texto livre", {"ids": ["1"]}])
    r = GatewayModelo(prov, registrar=eventos.append).gerar(PROMPT, {"candidatos": [], "ponto": ""}, Saida)
    assert r.tentativas == 2
    assert "não seguiu o esquema" in prov.recebidos[1]
    assert [e["tipo"] for e in eventos] == ["erro", "chamada_modelo"]


def test_falha_apos_tentativas():
    with pytest.raises(ErroSaidaModelo):
        GatewayModelo(ProvedorFalso(["x", "y"])).gerar(PROMPT, {"candidatos": [], "ponto": ""}, Saida)


def test_variavel_ausente():
    with pytest.raises(KeyError):
        PROMPT.renderizar({"ponto": "x"})


def test_carregar_prompt(tmp_path):
    (tmp_path / "p.md").write_text("versao: 1.2\n\nOlá {{nome}}", encoding="utf-8")
    p = carregar_prompt("p", tmp_path)
    assert p.versao == "1.2" and p.renderizar({"nome": "x"}) == "Olá x"
    (tmp_path / "q.md").write_text("sem versão", encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_prompt("q", tmp_path)
