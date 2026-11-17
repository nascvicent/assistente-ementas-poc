import subprocess
import sys
from pathlib import Path

import pytest

from app.tesauro.carga import carregar, gerar_relatorio, ler_snapshot
from app.tesauro.indice import IndiceTesauro, validar_ids
from app.tesauro.skos import id_do_uri, ler

FIXTURE = Path(__file__).parent / "fixtures" / "tesauro_ficticio.ttl"
RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def termos():
    return ler(str(FIXTURE), "turtle")


@pytest.fixture(scope="module")
def indice(termos):
    return IndiceTesauro(termos)


def test_id_do_uri():
    assert id_do_uri("https://tesauros.exemplo/contas/?tema=123") == "123"
    assert id_do_uri("http://exemplo.invalid/conceito/abc#") == "abc"


def test_leitura_skos(termos):
    assert len(termos) == 11
    vac = termos["3"]
    assert vac.rotulo == "Vacinação"
    assert vac.alternativos == ["Imunização"]
    assert vac.tg == ["2"] and vac.te == ["4"]
    assert termos["11"].rotulo == "Concurso público"  # ignora rótulo em inglês
    assert "Public competition" not in termos["11"].alternativos


def test_busca_lexical_por_nota_de_escopo_e_plural(indice):
    ids = [i for i, _ in indice.busca_lexical("armazenamento de vacinas em geladeiras")]
    assert ids[0] == "4"  # Rede de frio, pela nota de escopo
    # "vacinas" × "Vacinação" não casa lexicalmente; o genérico entra pela expansão TG.
    assert "3" in {c.id for c in indice.candidatos("armazenamento de vacinas em geladeiras")}


def test_busca_por_remissiva(indice):
    ids = [i for i, _ in indice.busca_lexical("contratação sem licitação")]
    assert ids[0] == "6"


def test_por_rotulo_resolve_use(indice):
    assert indice.por_rotulo("IMUNIZAÇÃO").id == "3"
    assert indice.por_rotulo("Vacinacao").id == "3"
    assert indice.por_rotulo("Inexistente") is None


def test_candidatos_expandem_termo_generico(indice):
    cands = {c.id: c for c in indice.candidatos("rede de frio")}
    assert cands["4"].origem == "lexical"
    assert cands["3"].origem in {"lexical", "expansao_tg"}
    assert cands["4"].tg_rotulo == "Vacinação"


def test_candidatos_com_busca_vetorial(termos):
    idx = IndiceTesauro(termos, busca_vetorial=lambda q, k: [("10", 0.9), ("999", 0.8)])
    ids = {c.id for c in idx.candidatos("ingresso no serviço público")}
    assert "10" in ids and "999" not in ids


def test_validar_ids_conjunto_fechado(indice):
    cands = indice.candidatos("dispensa de licitação")
    v = validar_ids(["7", "inventado", "7", "6", "999"], cands)
    assert v.aceitos == ["7", "6"]
    assert v.rejeitados == ["inventado", "999"]


def test_validar_ids_limite(indice):
    cands = indice.candidatos("licitação contratação dispensa inexigibilidade administração")
    v = validar_ids([c.id for c in cands], cands, limite=5)
    assert len(v.aceitos) == 5


def test_ordem_amplo_especifico(indice):
    assert indice.ordenar_amplo_especifico(["4", "2", "3"]) == ["2", "3", "4"]
    assert indice.ancestrais("4") == ["3", "2", "1"]


def test_relatorio_detecta_quebras_ciclos_e_diferencas(termos):
    import copy
    t = copy.deepcopy(termos)
    t["2"].tg = ["4"]          # ciclo 2 → 4 → 3 → 2
    t["5"].tr = ["999"]        # relação quebrada
    anterior = {i: x.para_dict() for i, x in termos.items() if i != "11"}
    anterior["9"]["rotulo"] = "Pessoal (antigo)"
    anterior["50"] = {"id": "50", "uri": "", "rotulo": "Removido", "alternativos": [], "nota_escopo": None, "tg": [], "te": [], "tr": []}
    rel = gerar_relatorio(t, "teste", "v1", anterior)
    assert rel.relacoes_quebradas == ["5 → 999"]
    assert rel.ciclos
    assert rel.novos == ["11"] and rel.removidos == ["50"] and "9" in rel.alterados


def test_carga_snapshot_e_script(tmp_path):
    saida = tmp_path / "tesauro.json"
    rel = carregar(str(FIXTURE), saida, formato="turtle")
    assert rel.total == 11 and saida.exists()
    versao, termos = ler_snapshot(saida)
    assert termos["3"].rotulo == "Vacinação"

    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "carregar_tesauro.py"), str(FIXTURE), "--saida", str(saida), "--formato", "turtle"],
        capture_output=True, text=True, check=True,
    )
    assert "Termos preferidos: 11" in r.stdout
    assert "0 novos, 0 alterados, 0 removidos" not in r.stdout  # sem diferenças, a linha não aparece


# --- exportação JSON do TemaTres (formato do TCN do IRB) ---------------------

from app.tesauro import tematres_json
from app.tesauro.indice import semelhanca_token

FIXTURE_JSON = Path(__file__).parent / "fixtures" / "tcn_tematres_ficticio.json"


def test_le_exportacao_tematres():
    termos, info = tematres_json.ler(FIXTURE_JSON)
    assert len(termos) == 9 and not info.completo and info.pendentes == ["30"]
    assert termos["1"].meta and not termos["10"].meta
    assert termos["11"].tg == ["10", "1"]  # genérico não-meta primeiro
    assert termos["11"].uri == "https://exemplo.invalid/vocab/index.php?tema=11"
    assert "99" not in termos and termos["30"].te == []  # relação para termo ausente é ignorada


def test_semelhanca_por_prefixo():
    assert semelhanca_token("vacina", "vacina") == 1
    assert semelhanca_token("vacina", "vacinacao") > 0
    assert semelhanca_token("licitacao", "licitacoe") > 0
    assert semelhanca_token("lei", "leilao") == 0  # curto demais
    assert semelhanca_token("contrato", "contabil") == 0


def test_busca_no_tcn_ignora_metatermos_e_casa_prefixo():
    termos, _ = tematres_json.ler(FIXTURE_JSON)
    idx = IndiceTesauro(termos)
    ids = [i for i, _ in idx.busca_lexical("vacinação em salas de vacina")]
    assert ids[0] == "21"
    assert "2" not in [i for i, _ in idx.busca_lexical("saúde")]  # metatermo fora
    cands = {c.id: c for c in idx.candidatos("dispensa de licitação")}
    assert "11" in cands and "1" not in cands  # expansão não traz metatermo
    assert cands["11"].tg_rotulo == "Licitação"
    assert idx.ordenar_amplo_especifico(["21", "22", "20"]) == ["22", "20", "21"]


def test_carga_da_exportacao_json(tmp_path):
    rel = carregar(str(FIXTURE_JSON), tmp_path / "t.json")
    assert rel.total == 9 and rel.metatermos == 2 and rel.varios_genericos == 1
    assert any("incompleta" in a for a in rel.avisos)
    assert "AVISO: exportação incompleta" in rel.texto()
    _, termos = ler_snapshot(tmp_path / "t.json")
    assert termos["1"].meta is True


def test_modificadores_nao_indexam_sozinhos():
    import copy
    termos, _ = tematres_json.ler(FIXTURE_JSON)
    termos = copy.deepcopy(termos)
    from app.tesauro.skos import Termo
    termos["3"] = Termo("3", "", "Especificador / Modificador", meta=True)
    termos["40"] = Termo("40", "", "cancelamento", tg=["3"])
    termos["10"].tg.append("3")  # Licitação também é modificador, mas tem outra categoria
    idx = IndiceTesauro(termos)
    assert not idx.indexavel("40") and idx.indexavel("10")
    assert "40" not in [i for i, _ in idx.busca_lexical("cancelamento de licitação")]
