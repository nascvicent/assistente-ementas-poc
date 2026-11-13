"""Índice local do tesauro: busca, expansão, validação de IDs e ordem amplo → específico.

Implementa os passos 2, 3 e 5 da seção 6.3 do documento 01. A busca vetorial é
plugável (`busca_vetorial`); enquanto o modelo de embeddings não estiver definido
(P5), só a busca lexical roda. Em produção a busca lexical passa para o PostgreSQL
(tsvector, ver scripts/sql/001_schema.sql) com a mesma interface.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Iterable

from app.tesauro.skos import Termo
from app.verificadores.normalizacao import normalizar_para_busca

STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "para", "por", "com", "sem", "um", "uma", "ao", "aos", "que", "se", "ou", "sobre", "pela", "pelo",
}

BuscaVetorial = Callable[[str, int], list[tuple[str, float]]]


def _radical(palavra: str) -> str:
    """Radical simplificado (plural e gênero), suficiente para rótulos curtos."""
    for suf, rep in (("coes", "cao"), ("oes", "ao"), ("aes", "ao"), ("ais", "al"), ("eis", "el"), ("ns", "m")):
        if palavra.endswith(suf) and len(palavra) > len(suf) + 2:
            return palavra[: -len(suf)] + rep
    if palavra.endswith("es") and len(palavra) > 5 and palavra[-3] in "rsz":
        return palavra[:-2]
    if palavra.endswith("s") and len(palavra) > 3:
        return palavra[:-1]
    return palavra


def tokens(texto: str) -> list[str]:
    return [_radical(t) for t in re.findall(r"[a-z0-9]+", normalizar_para_busca(texto)) if t not in STOPWORDS]


@dataclass(frozen=True)
class Candidato:
    id: str
    rotulo: str
    nota_escopo: str | None
    tg_rotulo: str | None
    pontuacao: float
    origem: str  # lexical | vetorial | expansao_tg


class IndiceTesauro:
    def __init__(self, termos: dict[str, Termo], busca_vetorial: BuscaVetorial | None = None):
        self.termos = termos
        self.busca_vetorial = busca_vetorial
        self._por_rotulo: dict[str, str] = {}
        self._remissivas: dict[str, str] = {}  # rótulo não preferido (UP) → id do preferido (USE)
        self._docs: dict[str, Counter] = {}
        df: Counter = Counter()
        for t in termos.values():
            self._por_rotulo[normalizar_para_busca(t.rotulo)] = t.id
            for alt in t.alternativos:
                self._remissivas.setdefault(normalizar_para_busca(alt), t.id)
            doc = Counter()
            for tok in tokens(t.rotulo):
                doc[tok] += 3
            for alt in t.alternativos:
                for tok in tokens(alt):
                    doc[tok] += 2
            for tok in tokens(t.nota_escopo or ""):
                doc[tok] += 1
            self._docs[t.id] = doc
            df.update(set(doc))
        n = max(1, len(termos))
        self._idf = {tok: math.log(1 + n / f) for tok, f in df.items()}

    # --- consulta direta ------------------------------------------------------

    def __contains__(self, termo_id: str) -> bool:
        return termo_id in self.termos

    def por_rotulo(self, rotulo: str) -> Termo | None:
        """Rótulo preferido exato (normalizado) ou remissiva resolvida para o preferido."""
        chave = normalizar_para_busca(rotulo)
        tid = self._por_rotulo.get(chave) or self._remissivas.get(chave)
        return self.termos.get(tid) if tid else None

    def rotulos_preferidos(self) -> set[str]:
        return {t.rotulo for t in self.termos.values()}

    # --- busca -----------------------------------------------------------------

    def busca_lexical(self, consulta: str, k: int = 30) -> list[tuple[str, float]]:
        q = tokens(consulta)
        if not q:
            return []
        frase = normalizar_para_busca(consulta)
        resultados = []
        for tid, doc in self._docs.items():
            score = sum(doc[tok] * self._idf.get(tok, 0) for tok in set(q) if tok in doc)
            if not score:
                continue
            t = self.termos[tid]
            rotulos = [normalizar_para_busca(r) for r in [t.rotulo, *t.alternativos]]
            if any(r and r in frase for r in rotulos):
                score *= 2  # o rótulo inteiro aparece na consulta
            resultados.append((tid, score))
        resultados.sort(key=lambda x: (-x[1], self.termos[x[0]].rotulo))
        return resultados[:k]

    def candidatos(self, consulta: str, k: int = 30, expandir: bool = True) -> list[Candidato]:
        """União lexical + vetorial (top k de cada), com expansão pelo termo genérico."""
        vistos: dict[str, Candidato] = {}
        for tid, s in self.busca_lexical(consulta, k):
            vistos[tid] = self._candidato(tid, s, "lexical")
        if self.busca_vetorial:
            for tid, s in self.busca_vetorial(consulta, k):
                if tid in self.termos and tid not in vistos:
                    vistos[tid] = self._candidato(tid, s, "vetorial")
        if expandir:
            for c in list(vistos.values()):
                for pai in self.termos[c.id].tg:
                    if pai in self.termos and pai not in vistos:
                        vistos[pai] = self._candidato(pai, 0.0, "expansao_tg")
        return list(vistos.values())

    def _candidato(self, tid: str, pontuacao: float, origem: str) -> Candidato:
        t = self.termos[tid]
        pai = self.termos.get(t.tg[0]) if t.tg else None
        return Candidato(t.id, t.rotulo, t.nota_escopo, pai.rotulo if pai else None, pontuacao, origem)

    # --- hierarquia ----------------------------------------------------------

    def ancestrais(self, termo_id: str) -> list[str]:
        """Cadeia de termos genéricos, do imediato ao mais amplo (primeiro TG de cada nível)."""
        cadeia, atual, vistos = [], termo_id, {termo_id}
        while (t := self.termos.get(atual)) and t.tg:
            pai = t.tg[0]
            if pai in vistos:
                break  # ciclo na base
            cadeia.append(pai)
            vistos.add(pai)
            atual = pai
        return cadeia

    def profundidade(self, termo_id: str) -> int:
        return len(self.ancestrais(termo_id))

    def ordenar_amplo_especifico(self, ids: Iterable[str]) -> list[str]:
        """Ordem do cabeçalho (art. 4º, I): termo genérico antes do específico."""
        ids = list(dict.fromkeys(ids))
        return sorted(ids, key=lambda i: (self.profundidade(i), ids.index(i)))


@dataclass(frozen=True)
class ValidacaoIds:
    aceitos: list[str]
    rejeitados: list[str]


def validar_ids(ids: Iterable[str], candidatos: Iterable[Candidato], limite: int = 5) -> ValidacaoIds:
    """Passo 5 da seção 6.3: só passam IDs da lista de candidatos enviada ao modelo."""
    permitidos = {c.id for c in candidatos}
    aceitos, rejeitados = [], []
    for i in ids:
        i = str(i).strip()
        if i in permitidos and i not in aceitos and len(aceitos) < limite:
            aceitos.append(i)
        elif i not in aceitos:
            rejeitados.append(i)
    return ValidacaoIds(aceitos, rejeitados)
