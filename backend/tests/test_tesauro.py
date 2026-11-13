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
