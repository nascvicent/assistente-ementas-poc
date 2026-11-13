"""Leitura de exportação SKOS (TemaTres) do Tesauro de Contas Nacional.

Fonte oficial ainda a confirmar (pendência P4 / decisão D2). O leitor aceita qualquer
serialização que o rdflib entenda (RDF/XML, Turtle…), de arquivo ou URL.
"""
import re
from dataclasses import dataclass, field

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

IDIOMA = "pt"


@dataclass
class Termo:
    id: str
    uri: str
    rotulo: str
    alternativos: list[str] = field(default_factory=list)
    nota_escopo: str | None = None
    tg: list[str] = field(default_factory=list)  # termos genéricos (broader)
    te: list[str] = field(default_factory=list)  # termos específicos (narrower)
    tr: list[str] = field(default_factory=list)  # termos relacionados

    def para_dict(self) -> dict:
        return self.__dict__.copy()


def id_do_uri(uri: str) -> str:
    """TemaTres usa '...?tema=123'; nos demais casos, o último segmento do caminho."""
    m = re.search(r"[?&]tema=(\d+)", uri)
    if m:
        return m.group(1)
    return re.split(r"[/#]", uri.rstrip("/#"))[-1]


def _literal_pt(valores: list[Literal]) -> list[str]:
    pt = [str(v) for v in valores if getattr(v, "language", None) in (IDIOMA, None) or str(getattr(v, "language", "")).startswith(IDIOMA)]
    return [v.strip() for v in pt if v.strip()]


def ler_grafo(fonte: str, formato: str | None = None) -> Graph:
    g = Graph()
    g.parse(fonte, format=formato)
    return g


def termos_do_grafo(g: Graph) -> dict[str, Termo]:
    conceitos = set(g.subjects(RDF.type, SKOS.Concept))
    # Algumas exportações omitem rdf:type; incluir quem tem prefLabel.
    conceitos |= {s for s in g.subjects(SKOS.prefLabel, None) if isinstance(s, URIRef)}

    termos: dict[str, Termo] = {}
    for c in conceitos:
        uri = str(c)
        preferidos = _literal_pt(list(g.objects(c, SKOS.prefLabel)))
        if not preferidos:
            continue
        notas = _literal_pt(list(g.objects(c, SKOS.scopeNote)) + list(g.objects(c, SKOS.definition)))
        termos[id_do_uri(uri)] = Termo(
            id=id_do_uri(uri),
            uri=uri,
            rotulo=preferidos[0],
            alternativos=sorted(set(_literal_pt(list(g.objects(c, SKOS.altLabel)))) | set(preferidos[1:])),
            nota_escopo=" ".join(notas) or None,
            tg=sorted(id_do_uri(str(o)) for o in g.objects(c, SKOS.broader)),
            te=sorted(id_do_uri(str(o)) for o in g.objects(c, SKOS.narrower)),
            tr=sorted(id_do_uri(str(o)) for o in g.objects(c, SKOS.related)),
        )

    # Completa relações inversas que a exportação não trouxer.
    for t in termos.values():
        for pai in t.tg:
            if pai in termos and t.id not in termos[pai].te:
                termos[pai].te.append(t.id)
        for filho in t.te:
            if filho in termos and t.id not in termos[filho].tg:
                termos[filho].tg.append(t.id)
    return termos


def ler(fonte: str, formato: str | None = None) -> dict[str, Termo]:
    return termos_do_grafo(ler_grafo(fonte, formato))
