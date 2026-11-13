"""Detecção de seções do voto e remoção do bloco de ementa já existente.

O inteiro teor costuma trazer a ementa dentro do voto (documento 02, seção 10). Ela
precisa sair do texto antes de qualquer chamada de modelo — senão o sistema só copia
a ementa pronta e a avaliação fica contaminada. O bloco removido é devolvido para
servir de gabarito no conjunto de avaliação.
"""
import re
from dataclasses import dataclass

from app.ingestao.documento import Documento, Pagina, Secao

_INICIO_EMENTA = re.compile(r"^\s*EMENTA\s*:", re.IGNORECASE)
_TITULO_IV = re.compile(r"^\s*IV\s*[.\-–]\s*TESE", re.IGNORECASE)
_ITEM = re.compile(r"^\s*\d+\s*[.)]\s+\S")
_FIM_EMENTA = re.compile(
    r"^\s*(AC[ÓO]RD[ÃA]O\b|ACORDAM\b|VISTOS\b|RESULTADO DO JULGAMENTO|[ÉE] (O|COMO) VOTO|RELAT[ÓO]RIO\b|"
    r"VOTO( DO RELATOR| DO CONSELHEIRO)?\s*$|FUNDAMENTA[ÇC][ÃA]O\b|CONCLUS[ÃA]O\b|DECIS[ÃA]O\b|"
    r"RECIFE\s*,|PRESENTES\b|PARTICIPARAM\b|PROCURADOR)",
    re.IGNORECASE,
)
_MAX_LINHAS_EMENTA = 200

_TITULOS_SECAO = [
    (re.compile(r"^\s*RELAT[ÓO]RIO\b", re.IGNORECASE), Secao.RELATORIO),
    (re.compile(r"^\s*(VOTO\b|FUNDAMENTA[ÇC][ÃA]O\b)", re.IGNORECASE), Secao.VOTO),
    (re.compile(r"^\s*(ANTE O EXPOSTO|DIANTE DO EXPOSTO|CONCLUS[ÃA]O\b|DISPOSITIVO\b|.*VOTO pelo que segue)", re.IGNORECASE), Secao.DISPOSITIVO),
]


@dataclass
class BlocoEmenta:
    texto: str
    pagina_inicial: int
    pagina_final: int


def _linhas(doc: Documento) -> list[tuple[int, str]]:
    return [(p.numero, linha) for p in doc.paginas for linha in p.texto.split("\n")]


def _fim_da_ementa(linhas: list[tuple[int, str]], inicio: int) -> int:
    """Índice (exclusivo) da última linha do bloco de ementa."""
    limite = min(len(linhas), inicio + _MAX_LINHAS_EMENTA)
    viu_iv = False
    ultimo_item_iv = None
    for i in range(inicio + 1, limite):
        linha = linhas[i][1]
        if _FIM_EMENTA.match(linha):
            return i
        if _TITULO_IV.match(linha):
            viu_iv = True
        elif viu_iv and _ITEM.match(linha):
            ultimo_item_iv = i
        elif viu_iv and ultimo_item_iv is not None and not linha.strip():
            return i  # linha em branco depois do último item da tese
    if ultimo_item_iv is not None:
        return ultimo_item_iv + 1
    return limite


def remover_ementa(doc: Documento) -> tuple[Documento, BlocoEmenta | None]:
    linhas = _linhas(doc)
    inicio = next((i for i, (_, l) in enumerate(linhas) if _INICIO_EMENTA.match(l)), None)
    if inicio is None:
        return doc, None
    fim = _fim_da_ementa(linhas, inicio)
    bloco = BlocoEmenta(
        texto="\n".join(l for _, l in linhas[inicio:fim]).strip(),
        pagina_inicial=linhas[inicio][0],
        pagina_final=linhas[fim - 1][0],
    )
    restantes = linhas[:inicio] + linhas[fim:]
    paginas = []
    for p in doc.paginas:
        texto = "\n".join(l for n, l in restantes if n == p.numero).strip()
        paginas.append(Pagina(p.numero, texto, p.secao))
    novo = Documento(doc.nome, doc.formato, doc.hash_arquivo, paginas, list(doc.avisos), doc.paginacao_real)
    novo.avisos.append(f"Bloco de ementa existente removido (p. {bloco.pagina_inicial}–{bloco.pagina_final}).")
    return novo, bloco


def detectar_secoes(doc: Documento) -> Documento:
    """Marca em cada página a seção predominante no início dela (heurística por títulos)."""
    atual = Secao.PREAMBULO
    for p in doc.paginas:
        secao_inicio = atual
        linhas = [l for l in p.texto.split("\n") if l.strip()]
        for i, linha in enumerate(linhas):
            for padrao, secao in _TITULOS_SECAO:
                if padrao.match(linha):
                    atual = secao
                    if i == 0:  # página que abre com o título pertence à nova seção
                        secao_inicio = secao
                    break
        p.secao = secao_inicio if secao_inicio != Secao.PREAMBULO else atual
    return doc
