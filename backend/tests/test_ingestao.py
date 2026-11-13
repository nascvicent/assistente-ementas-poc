"""Ingestão: arquivos gerados no próprio teste, com texto fictício."""
import io

import pymupdf
import pytest

from app.ingestao import FormatoNaoSuportado, carregar_bytes, carregar_texto
from app.ingestao.documento import Secao
from app.ingestao.limpeza import juntar_hifenizacao, remover_cabecalho_rodape

CABECALHO = "TRIBUNAL DE CONTAS FICTÍCIO"


def _pdf(paginas: list[str]) -> bytes:
    doc = pymupdf.open()
    for texto in paginas:
        pg = doc.new_page()
        pg.insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=10)
    dados = doc.tobytes()
    doc.close()
    return dados


def test_pdf_texto_por_pagina_sem_cabecalho_repetido():
    corpos = [
        "A equipe de auditoria\nvisitou as unidades\nde saúde em março.",
        "Foram encontradas\ngeladeiras domésticas\nem duas salas de vacina.",
        "O gestor apresentou\njustificativas e um\nplano de ação.",
    ]
    paginas = [f"{CABECALHO}\n{c}\nPágina {i} de 3" for i, c in enumerate(corpos, 1)]
    doc, bloco = carregar_bytes(_pdf(paginas), "voto.pdf")
    assert [p.numero for p in doc.paginas] == [1, 2, 3]
    assert "geladeiras domésticas" in doc.paginas[1].texto
    assert CABECALHO not in doc.texto
    assert "Página 2 de 3" not in doc.texto
    assert bloco is None
    assert doc.texto_paginado().startswith("[[p. 1]]\n")


def test_pdf_sem_camada_de_texto():
    doc = pymupdf.open()
    doc.new_page()
    dados = doc.tobytes()
    d, _ = carregar_bytes(dados, "digitalizado.pdf")
    assert any("sem camada de texto" in a for a in d.avisos)


def test_docx_com_quebra_de_pagina():
    import docx
    from docx.enum.text import WD_BREAK

    arq = docx.Document()
    arq.add_paragraph("RELATÓRIO")
    arq.add_paragraph("Primeira página do relatório.")
    arq.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    arq.add_paragraph("VOTO")
    arq.add_paragraph("Segunda página com o voto.")
    buf = io.BytesIO()
    arq.save(buf)
    doc, _ = carregar_bytes(buf.getvalue(), "voto.docx")
    assert len(doc.paginas) == 2
    assert "Segunda página" in doc.paginas[1].texto
    assert doc.paginas[0].secao is Secao.RELATORIO
    assert doc.paginas[1].secao is Secao.VOTO


def test_odt_com_soft_page_break():
    from odf.opendocument import OpenDocumentText
    from odf.text import P, SoftPageBreak

    odt = OpenDocumentText()
    odt.text.addElement(P(text="Página um do voto."))
    odt.text.addElement(SoftPageBreak())
    odt.text.addElement(P(text="Página dois do voto."))
    buf = io.BytesIO()
    odt.write(buf)
    doc, _ = carregar_bytes(buf.getvalue(), "voto.odt")
    assert [p.texto for p in doc.paginas] == ["Página um do voto.", "Página dois do voto."]


def test_txt_com_form_feed_e_sem():
    doc, _ = carregar_texto("pág 1\fpág 2", "voto.txt")
    assert len(doc.paginas) == 2 and doc.paginacao_real
    doc, _ = carregar_texto("texto único")
    assert len(doc.paginas) == 1 and not doc.paginacao_real
    assert any("página única" in a for a in doc.avisos)


def test_formato_nao_suportado():
    with pytest.raises(FormatoNaoSuportado):
        carregar_bytes(b"x", "voto.rtf")


def test_hifenizacao():
    assert juntar_hifenizacao("provi-\ndências corre-\n  tivas") == "providências corretivas"
    assert juntar_hifenizacao("Pernambuco-\nPE") == "Pernambuco-\nPE"  # maiúscula: mantém


def test_cabecalho_rodape_precisa_de_tres_paginas():
    assert remover_cabecalho_rodape(["A\nx", "A\ny"]) == ["A\nx", "A\ny"]


VOTO_COM_EMENTA = """RELATÓRIO
Consulta formulada por gestor de município fictício.
VOTO
Acolho o parecer do Ministério Público de Contas.
EMENTA: CONSULTA. CONTRATAÇÃO DIRETA. CONHECIMENTO. RESPOSTA.
I. CASO EM EXAME
1. Consulta sobre contratação direta.
II. RAZÕES DE DECIDIR
2. A contratação direta exige justificativa.
III. DISPOSITIVO
3. Consulta conhecida e respondida.
IV. TESE DE JULGAMENTO
4. A contratação direta exige justificativa de preço.
É o voto.
Recife, data fictícia."""


def test_remove_bloco_de_ementa_e_devolve_gabarito():
    doc, bloco = carregar_texto(VOTO_COM_EMENTA)
    assert bloco is not None
    assert bloco.texto.startswith("EMENTA: CONSULTA.")
    assert bloco.texto.endswith("justificativa de preço.")
    assert "EMENTA" not in doc.texto
    assert "TESE DE JULGAMENTO" not in doc.texto
    assert "É o voto." in doc.texto and "Acolho o parecer" in doc.texto
    assert any("ementa existente removido" in a for a in doc.avisos)


def test_remove_ementa_sem_marcador_final():
    texto = VOTO_COM_EMENTA.split("É o voto.")[0] + "\nTexto que continua depois sem título."
    doc, bloco = carregar_texto(texto)
    assert bloco.texto.endswith("justificativa de preço.")
    assert "Texto que continua" in doc.texto


def test_remove_ementa_que_atravessa_paginas():
    texto = VOTO_COM_EMENTA.replace("III. DISPOSITIVO", "\fIII. DISPOSITIVO")
    doc, bloco = carregar_texto(texto, "voto.txt")
    assert (bloco.pagina_inicial, bloco.pagina_final) == (1, 2)
    assert "Consulta conhecida" not in doc.texto
    assert "É o voto." in doc.paginas[1].texto
