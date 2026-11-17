"""Leitura da exportação JSON do serviço web do TemaTres (TCN do IRB).

Formato recebido em 17/11/2026, gerado a partir de
https://tesauro.irbcontas.org.br/vocab/services.php percorrendo a árvore:

    {"fonte": "...services.php", "inicio": "...", "exportado": "...", "completo": false,
     "termos":   [{"id": "764", "nome": "Dispensa de licitação", "meta": false, "idioma": null}, ...],
     "relacoes": [{"pai": "15", "filho": "764", "tipo": "NT"}, ...],
     "consultados": ["1", ...],   # termos cujos filhos já foram baixados
     "pendentes":   ["349", ...]} # termos cujos filhos ainda não foram baixados

Esta exportação não traz remissivas (USE/UP), notas de escopo nem termos
relacionados; quando vierem, entram em `alternativos`, `nota_escopo` e `tr`.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.tesauro.skos import Termo


@dataclass
class InfoExportacao:
    fonte: str
    exportado: str | None
    completo: bool
    pendentes: list[str] = field(default_factory=list)


def eh_exportacao_tematres(dados: dict) -> bool:
    return isinstance(dados, dict) and "termos" in dados and "relacoes" in dados


def _url_termo(fonte: str, termo_id: str) -> str:
    base = fonte.rsplit("/", 1)[0] if fonte.endswith(".php") else fonte.rstrip("/")
    return f"{base}/index.php?tema={termo_id}"


def termos_da_exportacao(dados: dict) -> tuple[dict[str, Termo], InfoExportacao]:
    fonte = dados.get("fonte") or ""
    termos: dict[str, Termo] = {}
    for t in dados["termos"]:
        tid = str(t["id"])
        nome = (t.get("nome") or "").strip()
        if not nome:
            continue
        termos[tid] = Termo(
            id=tid,
            uri=_url_termo(fonte, tid),
            rotulo=nome,
            alternativos=sorted({a.strip() for a in t.get("alternativos", []) if a and a.strip()}),
            nota_escopo=(t.get("nota") or None),
            meta=bool(t.get("meta")),
        )
    for r in dados["relacoes"]:
        pai, filho, tipo = str(r["pai"]), str(r["filho"]), (r.get("tipo") or "NT").upper()
        if pai not in termos or filho not in termos:
            continue
        if tipo in ("NT", "TE"):
            if pai not in termos[filho].tg:
                termos[filho].tg.append(pai)
            if filho not in termos[pai].te:
                termos[pai].te.append(filho)
        elif tipo in ("RT", "TR"):
            if filho not in termos[pai].tr:
                termos[pai].tr.append(filho)
            if pai not in termos[filho].tr:
                termos[filho].tr.append(pai)
    for t in termos.values():
        # Genérico não-meta primeiro: é o que aparece no cabeçalho e na expansão.
        t.tg.sort(key=lambda i: (termos[i].meta, termos[i].rotulo, i))
        t.te.sort()
        t.tr.sort()
    info = InfoExportacao(
        fonte=fonte,
        exportado=dados.get("exportado"),
        completo=bool(dados.get("completo")),
        pendentes=[str(p) for p in dados.get("pendentes", [])],
    )
    return termos, info


def ler(caminho: str | Path) -> tuple[dict[str, Termo], InfoExportacao]:
    with open(caminho, encoding="utf-8") as f:
        return termos_da_exportacao(json.load(f))
