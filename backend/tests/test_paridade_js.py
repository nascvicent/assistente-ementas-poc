"""Paridade entre o núcleo Python (backend/app) e o porte JavaScript (frontend/demo/nucleo.js).

A demonstração online roda o núcleo em JavaScript. Para os dois não divergirem,
todos os casos do teste do linter são reexecutados nos dois lados e comparados,
além de casos de evidência, limpeza e remoção da ementa.
"""
import inspect
import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

import tests.test_linter_ementa as casos_linter
from app.dominio.enumeracoes import Modalidade, Resultado
from app.ingestao.documento import Documento, Pagina
from app.ingestao.limpeza import limpar
from app.ingestao.secoes import remover_ementa
from app.verificadores import linter_ementa
from app.verificadores.evidencia import TextoPaginado, conferir_trecho
from tests.conftest import VOTO_FICTICIO, criar_ficha
from tests.test_ingestao import VOTO_COM_EMENTA

RUNNER = Path(__file__).parent / "paridade_runner.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node não instalado")


def rodar_js(casos: list[dict]) -> list:
    r = subprocess.run(["node", str(RUNNER)], input=json.dumps(casos), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def ctx_json(ctx) -> dict:
    if ctx is None:
        return {}
    return {
        "modalidade": ctx.modalidade,
        "ficha": ctx.ficha.model_dump(mode="json") if ctx.ficha else None,
        "textoVoto": ctx.texto_voto,
        "termosCabecalho": [asdict(t) for t in ctx.termos_cabecalho] if ctx.termos_cabecalho else None,
        "rotulosTesauro": sorted(ctx.rotulos_tesauro) if ctx.rotulos_tesauro is not None else None,
    }


def coletar_chamadas_do_linter() -> list[tuple[str, object]]:
    """Executa os testes do linter gravando cada (texto, contexto) passado a verificar()."""
    gravadas = []
    original = casos_linter.verificar

    def gravar(texto, contexto=None, config=None):
        gravadas.append((texto, contexto))
        return original(texto, contexto, config)

    casos_linter.verificar = gravar
    try:
        for nome, fn in inspect.getmembers(casos_linter, inspect.isfunction):
            if not nome.startswith("test_"):
                continue
            params = inspect.signature(fn).parameters
            fn(**({"ficha": criar_ficha()} if "ficha" in params else {}))
    finally:
        casos_linter.verificar = original
    return gravadas


def test_linter_mesmos_achados():
    chamadas = coletar_chamadas_do_linter()
    assert len(chamadas) > 30
    esperado = [
        [[a.codigo, str(a.gravidade), a.referencia] for a in linter_ementa.verificar(t, c)]
        for t, c in chamadas
    ]
    obtido = rodar_js([{"op": "linter", "texto": t, "ctx": ctx_json(c)} for t, c in chamadas])
    for (texto, _), e, o in zip(chamadas, esperado, obtido):
        assert o == e, f"divergência no texto:\n{texto[:300]}"


def test_evidencia():
    casos = [
        ("em desacordo com a RDC ANVISA nº 197/2017", 2), ("adotou providências corretivas durante a auditoria", 2),
        ("JULGAR REGULAR COM RESSALVAS", 3), ("geladeiras domésticas", 1), ("geladeiras residenciais", 2),
        ("Município de Vila Serena, exercícios de 2023 a 2025. VOTO A equipe", 1),
    ]
    paginas = {str(k): v for k, v in VOTO_FICTICIO.items()}
    obtido = rodar_js([{"op": "evidencia", "trecho": t, "pagina": p, "paginas": paginas} for t, p in casos])
    texto = TextoPaginado(VOTO_FICTICIO)
    for (t, p), o in zip(casos, obtido):
        r = conferir_trecho(t, p, texto)
        assert (o["status"], o["pagina_encontrada"]) == (str(r.status), r.pagina_encontrada), t


@pytest.mark.parametrize("texto", [
    VOTO_COM_EMENTA,
    VOTO_COM_EMENTA.replace("III. DISPOSITIVO", "\fIII. DISPOSITIVO"),
    VOTO_COM_EMENTA.split("É o voto.")[0] + "\nTexto que continua depois sem título.",
    "Voto sem ementa nenhuma.\fSegunda página.",
])
def test_remover_ementa(texto):
    paginas = texto.split("\f")
    doc = Documento("x", "txt", "h", [Pagina(i + 1, t) for i, t in enumerate(paginas)])
    novo, bloco = remover_ementa(doc)
    obtido = rodar_js([{"op": "remover_ementa", "paginas": [{"numero": i + 1, "texto": t} for i, t in enumerate(paginas)]}])[0]
    assert obtido["paginas"] == [p.texto for p in novo.paginas]
    assert obtido["bloco"] == (None if bloco is None else asdict(bloco))


def test_limpeza_e_frases():
    paginas = [f"TRIBUNAL FICTÍCIO\nLinha {c} da pági-\nna com provi-\ndências.\nPágina {i} de 3" for i, c in enumerate("abc", 1)]
    frases = ["Conforme o art. 75 da Lei nº 14.133/2021, a dispensa exige justificativa.",
              "Primeira frase. Segunda frase. Terceira. Quarta.", "Ver inc. II. Depois o § 1º. Fim."]
    obtido = rodar_js([{"op": "limpar", "paginas": paginas}] + [{"op": "frases", "texto": f} for f in frases])
    assert obtido[0] == limpar(paginas)
    assert obtido[1:] == [linter_ementa.contar_frases(f) for f in frases]


# --- montagem por código (só existe no JS por enquanto; conferida pelo linter Python) ---

def _montar(ficha, termos, teses):
    return rodar_js([{
        "op": "montar", "ficha": ficha.model_dump(mode="json"), "termos": termos,
        "caso": "Auditoria Especial de Conformidade realizada na Secretaria de Saúde de município, nos exercícios de 2023 a 2025.",
        "razoes": ["O armazenamento de vacinas em refrigeradores domésticos contraria a RDC ANVISA nº 197/2017."],
        "teses": teses,
    }])[0]


def test_montagem_passa_no_linter_python():
    ficha = criar_ficha()
    termos = [{"rotulo": "Rede de frio", "generico": "Vacinação"}, {"rotulo": "Vacinação", "generico": "Saúde"}]
    r = _montar(ficha, termos, ["O armazenamento de vacinas em refrigeradores domésticos viola as normas sanitárias da rede de frio."])
    assert r["dispositivo"] == {"texto": "Julgamento pela regularidade com ressalvas do objeto da Auditoria Especial, com expedição de determinações.", "a_definir": False}
    assert r["ementa"].startswith("EMENTA: AUDITORIA ESPECIAL. VACINAÇÃO. REDE DE FRIO. SAÚDE. REGULARIDADE COM RESSALVAS.")
    ctx = linter_ementa.ContextoLinter(ficha=ficha, texto_voto="\n".join(VOTO_FICTICIO.values()))
    assert linter_ementa.verificar(r["ementa"], ctx) == []


def test_montagem_sem_tese_e_modalidade_a_definir():
    ficha = criar_ficha()
    ficha.processo.modalidade = Modalidade.DENUNCIA
    ficha.julgamento.resultado = [Resultado.PROCEDENTE]
    r = _montar(ficha, [], [])
    assert r["dispositivo"]["a_definir"] and "[A DEFINIR" in r["dispositivo"]["texto"]
    assert "IV." not in r["ementa"]
    assert r["ementa"].startswith("EMENTA: DENÚNCIA. PROCEDÊNCIA.")


def test_cabecalho_limita_segmentos():
    termos = [{"rotulo": f"Termo {i}", "generico": f"Genérico {i}"} for i in range(10)]
    r = _montar(criar_ficha(), termos, [])
    assert linter_ementa.analisar(r["ementa"]).segmentos.__len__() <= 8


def test_verificar_tese():
    ficha = criar_ficha()
    voto = "\n".join(VOTO_FICTICIO.values())
    casos = rodar_js([
        {"op": "tese", "tese": "Em Vila Serena, no caso, a Lei nº 14.133/2021 exige R$ 10,00.", "ficha": ficha.model_dump(mode="json"), "textoVoto": voto},
        {"op": "tese", "tese": "O armazenamento de vacinas deve observar a RDC ANVISA nº 197/2017.", "ficha": ficha.model_dump(mode="json"), "textoVoto": voto},
    ])
    assert len(casos[0]) == 4 and casos[1] == []


def test_montagem_com_referencias_passa_no_linter_python():
    ficha = criar_ficha()
    r = rodar_js([{"op": "montar_ref", "ficha": ficha.model_dump(mode="json"), "ids": ["oc1"]}])[0]
    assert r == ["Referências normativas: RDC ANVISA nº 197/2017."]
    base = _montar(ficha, [], ["O armazenamento de vacinas em refrigeradores domésticos viola as normas sanitárias da rede de frio."])["ementa"]
    texto = base + "\n\n" + "\n".join(r)
    ctx = linter_ementa.ContextoLinter(ficha=ficha, texto_voto="\n".join(VOTO_FICTICIO.values()))
    assert linter_ementa.verificar(texto, ctx) == []


# --- avaliação (frontend/demo/avaliacao.js) --------------------------------

def test_avaliacao_compara_com_a_publicada():
    from tests.conftest import EMENTA_VALIDA
    sem_termo = EMENTA_VALIDA.replace("VACINAÇÃO. ", "")
    trocada = EMENTA_VALIDA.replace("regularidade com ressalvas do objeto", "irregularidade do objeto")
    igual, menos, outra = rodar_js([
        {"op": "comparar", "gerada": EMENTA_VALIDA, "referencia": EMENTA_VALIDA},
        {"op": "comparar", "gerada": sem_termo, "referencia": EMENTA_VALIDA},
        {"op": "comparar", "gerada": trocada, "referencia": EMENTA_VALIDA},
    ])
    assert igual["geral"] == 1 and igual["dispositivo"]["mesmoResultado"]
    assert menos["termos"]["soReferencia"] == ["VACINAÇÃO"] and menos["secoes"]["caso"] == 1 and menos["secoes"]["cabecalho"] < 1
    assert not outra["dispositivo"]["mesmoResultado"]


def test_avaliacao_extrai_ementa_do_texto_livre():
    r = rodar_js([{"op": "texto_livre", "texto": "Segue:\n\n**EMENTA:** CONSULTA. X.\nI. CASO EM EXAME\n1. a.\n\nPARA CONFERIR\na) nada a registrar"}])[0]
    assert r == {"ementa": "EMENTA: CONSULTA. X.\nI. CASO EM EXAME\n1. a.", "paraConferir": "a) nada a registrar"}


# --- tesauro (frontend/demo/tesauro.js × app/tesauro/indice.py) ------------

def _compacto(termos):
    return {"versao": "t", "fonte": "t", "avisos": [],
            "termos": [[t.id, t.rotulo, 1 if t.meta else 0, t.tg, t.alternativos] for t in termos.values()]}


def _comparar_tesauro(termos, chave, consultas, ordenar=()):
    from app.tesauro.indice import IndiceTesauro
    idx = IndiceTesauro(termos)
    dados = _compacto(termos)
    obtido = rodar_js([{"op": "tesauro", "chave": chave, "dados": dados, "consulta": q, "ordenar": list(ordenar)} for q in consultas])
    for q, o in zip(consultas, obtido):
        assert o["busca"] == [[i, round(s, 6)] for i, s in idx.busca_lexical(q, 15)], q
        assert o["candidatos"] == [[c.id, c.origem, c.tg_rotulo] for c in idx.candidatos(q, 15)], q
        assert o["ordem"] == idx.ordenar_amplo_especifico(list(ordenar))


def test_tesauro_paridade_fixture():
    from app.tesauro import tematres_json
    termos, _ = tematres_json.ler(Path(__file__).parent / "fixtures" / "tcn_tematres_ficticio.json")
    _comparar_tesauro(termos, "fixture", ["dispensa de licitação", "vacinação em salas de vacina", "saúde", "contratação", "x"], ["21", "22", "20"])


TCN = Path(__file__).resolve().parents[2] / "frontend" / "demo" / "dados" / "tcn.json"


@pytest.mark.skipif(not TCN.exists(), reason="snapshot do TCN ausente")
def test_tesauro_paridade_tcn():
    from app.tesauro.carga import ler_snapshot
    _, termos = ler_snapshot(TCN)
    consultas = ["dispensa de licitação emergencial", "cancelamento de restos a pagar FUNDEB", "acumulação de cargos públicos",
                 "repasse de duodécimo à câmara municipal", "contratação temporária de pessoal sem concurso", "nepotismo",
                 "armazenamento de vacinas", "obra pública superfaturamento", "previdência própria aposentadoria"]
    _comparar_tesauro(termos, "tcn", consultas, ["764", "248", "15"])


def test_normaliza_formato_do_prompt_do_aurorachat():
    saida = ("AUDITORIA ESPECIAL. SAÚDE. REGULARIDADE COM RESSALVAS.\n\nI. CASO EM EXAME\n\nAuditoria especial de conformidade na rede municipal.\n\n"
             "II. RAZÕES DE DECIDIR\n\nO uso de geladeiras domésticas contraria a RDC ANVISA nº 197/2017, art. 75.\n\nA correção afasta a multa.\n\n"
             "III. DISPOSITIVO\n\nJulgamento pela regularidade com ressalvas do objeto da Auditoria Especial.\n\nIV. TESE DE JULGAMENTO\n\n"
             "“1. Vacinas exigem equipamento exclusivo, nos termos do art. 75. 2. A correção tempestiva afasta a multa.”\n\n"
             "Dispositivos relevantes citados: RDC ANVISA nº 197/2017.")
    r = rodar_js([{"op": "normalizar", "texto": saida}])[0]
    e = linter_ementa.analisar(r["texto"])
    assert [i.numero for s in e.secoes for i in s.itens] == [1, 2, 3, 4, 5, 6]
    assert e.secoes[3].itens[0].texto.endswith("art. 75.")
    assert "teses em bloco entre aspas" in r["ajustes"] and "cabeçalho sem “EMENTA:”" in r["ajustes"]
    assert linter_ementa.verificar(r["texto"]) == []
