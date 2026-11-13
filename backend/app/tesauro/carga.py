"""Carga do tesauro: SKOS → snapshot JSON (e, opcionalmente, PostgreSQL), com relatório."""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.tesauro.skos import Termo, ler


@dataclass
class RelatorioCarga:
    versao: str
    fonte: str
    total: int
    sem_termo_generico: int
    relacoes_quebradas: list[str] = field(default_factory=list)
    ciclos: list[str] = field(default_factory=list)
    novos: list[str] = field(default_factory=list)
    alterados: list[str] = field(default_factory=list)
    removidos: list[str] = field(default_factory=list)

    def texto(self) -> str:
        linhas = [
            f"Carga do tesauro {self.versao} — fonte: {self.fonte}",
            f"Termos preferidos: {self.total} (sem termo genérico: {self.sem_termo_generico})",
            f"Relações apontando para termo inexistente: {len(self.relacoes_quebradas)}",
            f"Ciclos de hierarquia: {len(self.ciclos)}",
        ]
        if self.novos or self.alterados or self.removidos:
            linhas.append(f"Em relação à carga anterior: {len(self.novos)} novos, {len(self.alterados)} alterados, {len(self.removidos)} removidos")
        return "\n".join(linhas)


def _comparavel(t: dict) -> dict:
    return {k: (sorted(v) if isinstance(v, list) else v) for k, v in t.items() if k != "uri"}


def gerar_relatorio(termos: dict[str, Termo], fonte: str, versao: str, anterior: dict[str, dict] | None = None) -> RelatorioCarga:
    quebradas = [
        f"{t.id} → {alvo}"
        for t in termos.values()
        for alvo in t.tg + t.te + t.tr
        if alvo not in termos
    ]
    ciclos = []
    for t in termos.values():
        cadeia = [t.id]
        atual = t
        while atual.tg and atual.tg[0] in termos:
            proximo = atual.tg[0]
            if proximo in cadeia:
                ciclos.append(" → ".join(cadeia + [proximo]))
                break
            cadeia.append(proximo)
            atual = termos[proximo]
    rel = RelatorioCarga(
        versao=versao,
        fonte=fonte,
        total=len(termos),
        sem_termo_generico=sum(1 for t in termos.values() if not t.tg),
        relacoes_quebradas=quebradas,
        ciclos=sorted(set(ciclos)),
    )
    if anterior is not None:
        atuais = {i: t.para_dict() for i, t in termos.items()}
        rel.novos = sorted(set(atuais) - set(anterior))
        rel.removidos = sorted(set(anterior) - set(atuais))
        rel.alterados = sorted(i for i in set(atuais) & set(anterior) if _comparavel(atuais[i]) != _comparavel(anterior[i]))
    return rel


def salvar_snapshot(termos: dict[str, Termo], caminho: Path, versao: str, fonte: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({
        "versao": versao,
        "fonte": fonte,
        "termos": {i: t.para_dict() for i, t in sorted(termos.items())},
    }, ensure_ascii=False, indent=1), encoding="utf-8")


def ler_snapshot(caminho: Path) -> tuple[str, dict[str, Termo]]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return dados["versao"], {i: Termo(**t) for i, t in dados["termos"].items()}


def gravar_postgres(termos: dict[str, Termo], database_url: str, versao: str) -> None:
    """Substitui o conteúdo de tesauro_termo/tesauro_relacao numa transação."""
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM tesauro_relacao"))
        conn.execute(text("DELETE FROM tesauro_termo"))
        conn.execute(
            text("INSERT INTO tesauro_termo (id, uri, rotulo_preferido, rotulos_alternativos, nota_escopo, versao_carga) "
                 "VALUES (:id, :uri, :rotulo, :alternativos, :nota, :versao)"),
            [{"id": t.id, "uri": t.uri, "rotulo": t.rotulo, "alternativos": t.alternativos, "nota": t.nota_escopo, "versao": versao}
             for t in termos.values()],
        )
        relacoes = [
            {"termo": t.id, "tipo": tipo, "rel": alvo}
            for t in termos.values()
            for tipo, alvos in (("TG", t.tg), ("TE", t.te), ("TR", t.tr))
            for alvo in alvos
        ]
        if relacoes:
            conn.execute(
                text("INSERT INTO tesauro_relacao (termo_id, tipo, termo_relacionado_id) VALUES (:termo, :tipo, :rel) ON CONFLICT DO NOTHING"),
                relacoes,
            )


def carregar(fonte: str, saida: Path | None = None, database_url: str | None = None, formato: str | None = None) -> RelatorioCarga:
    versao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    termos = ler(fonte, formato)
    anterior = None
    if saida and saida.exists():
        _, antigos = ler_snapshot(saida)
        anterior = {i: t.para_dict() for i, t in antigos.items()}
    relatorio = gerar_relatorio(termos, fonte, versao, anterior)
    if saida:
        salvar_snapshot(termos, saida, versao, fonte)
    if database_url:
        gravar_postgres(termos, database_url, versao)
    return relatorio
