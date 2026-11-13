import pytest

from app.harness.estados import Acao, ContextoFluxo, Estado, MaquinaFluxo, TransicaoInvalida
from app.harness.roteador import TipoEntrada, classificar


def maquina(**ctx) -> MaquinaFluxo:
    return MaquinaFluxo(contexto=ContextoFluxo(**ctx))


def percorrer(m: MaquinaFluxo, acoes: list[Acao]) -> list[Estado]:
    return [m.disparar(a) for a in acoes]


def test_fluxo_completo_com_laco():
    m = maquina(ocorrencias_restantes=1)
    estados = percorrer(m, [
        Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER,
        Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ADICIONAR_OCORRENCIA,
    ])
    assert estados[-2] is Estado.AGUARDANDO_MAIS_OCORRENCIA
    assert estados[-1] is Estado.AGUARDANDO_OCORRENCIA
    m.contexto.ocorrencias_restantes = None
    percorrer(m, [Acao.ESCOLHER, Acao.CONCLUIR, Acao.DISPENSAR_TESE, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR])
    assert m.estado is Estado.AGUARDANDO_MAIS_OCORRENCIA
    percorrer(m, [Acao.ENCERRAR, Acao.CONCLUIR])
    assert m.estado is Estado.CONCLUIDA and m.estado.final


def test_atalho_ocorrencia_unica_pula_etapa_3_e_laco():
    m = maquina(ocorrencia_unica=True)
    assert percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR]) == [Estado.EXTRAINDO, Estado.PROPONDO_TESES]
    percorrer(m, [Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER])
    assert m.disparar(Acao.CONCLUIR) is Estado.VERIFICANDO


def test_sem_ocorrencias_restantes_vai_direto_a_verificacao():
    m = maquina(ocorrencias_restantes=0)
    percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER])
    assert m.disparar(Acao.CONCLUIR) is Estado.VERIFICANDO


def test_pergunta_nao_avanca():
    m = maquina()
    percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR])
    assert m.disparar(Acao.PERGUNTAR) is Estado.AGUARDANDO_TESE


def test_pergunta_nao_aceita_durante_processamento():
    m = maquina()
    m.disparar(Acao.ENVIAR_VOTO)
    with pytest.raises(TransicaoInvalida):
        m.disparar(Acao.PERGUNTAR)


def test_falha_devolve_ao_ultimo_estado_de_espera():
    m = maquina()
    percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER])
    assert m.estado is Estado.BUSCANDO_TERMOS
    assert m.disparar(Acao.FALHAR) is Estado.AGUARDANDO_TESE
    m2 = maquina()
    m2.disparar(Acao.ENVIAR_VOTO)
    assert m2.disparar(Acao.FALHAR) is Estado.AGUARDANDO_VOTO


def test_falha_nao_aceita_em_estado_de_espera():
    with pytest.raises(TransicaoInvalida):
        maquina().disparar(Acao.FALHAR)


def test_pedir_novas_teses():
    m = maquina()
    percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR])
    assert m.disparar(Acao.PEDIR_NOVAS_TESES) is Estado.PROPONDO_TESES


@pytest.mark.parametrize("ocorrencia_unica,esperado", [(False, Estado.AGUARDANDO_OCORRENCIA), (True, Estado.AGUARDANDO_VOTO)])
def test_voltar(ocorrencia_unica, esperado):
    m = maquina(ocorrencia_unica=ocorrencia_unica)
    acoes = [Acao.ENVIAR_VOTO, Acao.CONCLUIR] + ([] if ocorrencia_unica else [Acao.ESCOLHER]) + [Acao.CONCLUIR]
    percorrer(m, acoes)
    assert m.estado is Estado.AGUARDANDO_TESE
    assert m.disparar(Acao.VOLTAR) is esperado


def test_voltar_do_termo_e_da_pergunta_final():
    m = maquina()
    percorrer(m, [Acao.ENVIAR_VOTO, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR])
    assert m.disparar(Acao.VOLTAR) is Estado.AGUARDANDO_TESE
    percorrer(m, [Acao.ESCOLHER, Acao.CONCLUIR, Acao.ESCOLHER, Acao.CONCLUIR])
    assert m.disparar(Acao.VOLTAR) is Estado.AGUARDANDO_TERMO


@pytest.mark.parametrize("acao", [Acao.CONCLUIR, Acao.ESCOLHER, Acao.ENCERRAR, Acao.VOLTAR, Acao.DISPENSAR_TESE])
def test_transicoes_invalidas_no_inicio(acao):
    with pytest.raises(TransicaoInvalida):
        maquina().disparar(acao)


def test_estado_de_processamento_nao_aceita_escolha():
    m = maquina()
    m.disparar(Acao.ENVIAR_VOTO)
    with pytest.raises(TransicaoInvalida):
        m.disparar(Acao.ESCOLHER)


def test_cancelar_e_estados_finais():
    m = maquina()
    m.disparar(Acao.ENVIAR_VOTO)
    assert m.disparar(Acao.CANCELAR) is Estado.CANCELADA
    assert m.acoes_permitidas() == []
    with pytest.raises(TransicaoInvalida):
        m.disparar(Acao.CANCELAR)


def test_todo_estado_e_alcancavel_e_todo_nao_final_chega_a_concluida():
    from app.harness.estados import TRANSICOES
    contextos = [ContextoFluxo(), ContextoFluxo(ocorrencia_unica=True), ContextoFluxo(ocorrencias_restantes=0)]
    grafo: dict[Estado, set[Estado]] = {e: set() for e in Estado}
    for (origem, _), destino in TRANSICOES.items():
        for ctx in contextos:
            grafo[origem].add(destino(ctx) if callable(destino) else destino)

    alcancados, fila = {Estado.AGUARDANDO_VOTO}, [Estado.AGUARDANDO_VOTO]
    while fila:
        for d in grafo[fila.pop()]:
            if d not in alcancados:
                alcancados.add(d)
                fila.append(d)
    assert alcancados | {Estado.CANCELADA} == set(Estado)

    for e in Estado:
        if e.final:
            continue
        vistos, fila = {e}, [e]
        while fila:
            for d in grafo[fila.pop()]:
                if d not in vistos:
                    vistos.add(d)
                    fila.append(d)
        assert Estado.CONCLUIDA in vistos, f"{e} não chega a CONCLUIDA"


def test_historico_e_callback():
    eventos = []
    m = MaquinaFluxo(ao_transitar=eventos.append)
    m.disparar(Acao.ENVIAR_VOTO)
    assert len(m.historico) == 1 and eventos[0].para is Estado.EXTRAINDO


# --- roteador ---------------------------------------------------------------

@pytest.mark.parametrize("texto", ["2", " 2. ", "opção 2", "Alternativa 2", "2)"])
def test_roteador_escolha(texto):
    e = classificar(texto, Estado.AGUARDANDO_TESE, n_opcoes=4)
    assert e.tipo is TipoEntrada.ESCOLHA and e.opcao == 2 and e.acao is Acao.ESCOLHER


def test_roteador_opcao_fora_da_lista():
    assert classificar("7", Estado.AGUARDANDO_TESE, 4).tipo is TipoEntrada.OPCAO_INVALIDA


def test_roteador_pergunta():
    e = classificar("Por que a alternativa 4 menciona a LRF?", Estado.AGUARDANDO_TESE, 4)
    assert e.tipo is TipoEntrada.PERGUNTA and e.acao is Acao.PERGUNTAR


def test_roteador_comandos():
    assert classificar("Voltar", Estado.AGUARDANDO_TERMO, 5).acao is Acao.VOLTAR
    assert classificar("cancelar", Estado.AGUARDANDO_TERMO, 5).acao is Acao.CANCELAR
    assert classificar("sim", Estado.AGUARDANDO_MAIS_OCORRENCIA).acao is Acao.ADICIONAR_OCORRENCIA
    assert classificar("Não", Estado.AGUARDANDO_MAIS_OCORRENCIA).acao is Acao.ENCERRAR
    assert classificar("dispensar a tese", Estado.AGUARDANDO_TESE, 4).acao is Acao.DISPENSAR_TESE
    # "sim" fora da pergunta do laço é só uma pergunta/fala comum
    assert classificar("sim", Estado.AGUARDANDO_TERMO, 5).tipo is TipoEntrada.PERGUNTA
