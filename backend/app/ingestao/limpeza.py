"""Limpeza do texto extraído: cabeçalhos/rodapés repetidos e hifenização."""
import re
from collections import Counter

_HIFEN = re.compile(r"(\w)[-­]\n\s*([a-zà-ÿ])")
_LINHAS_BORDA = 3


def _assinatura(linha: str) -> str:
    """Linha com dígitos genéricos, para reconhecer 'Página 3 de 24' e afins."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", linha.strip().lower()))


def remover_cabecalho_rodape(paginas: list[str], proporcao_minima: float = 0.5) -> list[str]:
    """Remove linhas que se repetem no topo ou no pé da maioria das páginas."""
    if len(paginas) < 3:
        return paginas

    contagem: Counter[str] = Counter()
    for texto in paginas:
        linhas = [l for l in texto.split("\n") if l.strip()]
        bordas = set(map(_assinatura, linhas[:_LINHAS_BORDA] + linhas[-_LINHAS_BORDA:]))
        contagem.update(bordas)

    limite = max(2, int(len(paginas) * proporcao_minima + 0.5))
    repetidas = {a for a, n in contagem.items() if n >= limite and a}

    resultado = []
    for texto in paginas:
        linhas = texto.split("\n")
        nao_vazias = [i for i, l in enumerate(linhas) if l.strip()]
        borda = set(nao_vazias[:_LINHAS_BORDA] + nao_vazias[-_LINHAS_BORDA:])
        mantidas = [l for i, l in enumerate(linhas) if not (i in borda and _assinatura(l) in repetidas)]
        resultado.append("\n".join(mantidas).strip())
    return resultado


def juntar_hifenizacao(texto: str) -> str:
    """'provi-\\ndências' → 'providências' (só quando a continuação começa em minúscula)."""
    return _HIFEN.sub(r"\1\2", texto)


def limpar(paginas: list[str]) -> list[str]:
    paginas = remover_cabecalho_rodape(paginas)
    return [juntar_hifenizacao(p).strip() for p in paginas]
