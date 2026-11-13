"""Ficha do caso — saída da etapa 2 (documento 01, seção 5.1).

Regras:
- todo item factual carrega `evidencia` (trecho literal + página), conferida por código;
- campos de domínio são enumerações fechadas;
- o que não tiver evidência conferida vai para `nao_identificado`, nunca é inferido.
"""
from enum import StrEnum
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field

from app.dominio.enumeracoes import (
    Alteracao,
    FonteFundamento,
    Modalidade,
    OrgaoJulgador,
    Providencia,
    Resultado,
    SituacaoConsequencia,
)


class StatusEvidencia(StrEnum):
    NAO_VERIFICADA = "nao_verificada"
    CONFIRMADA = "confirmada"
    PAGINA_DIVERGENTE = "pagina_divergente"  # trecho existe, mas em outra página
    NAO_CONFIRMADA = "nao_confirmada"


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Evidencia(Base):
    trecho: str = Field(min_length=1, description="Fragmento literal do voto")
    pagina: int = Field(ge=1)
    status: StatusEvidencia = StatusEvidencia.NAO_VERIFICADA
    pagina_encontrada: int | None = None


class Processo(Base):
    numero: str | None = None
    modalidade: Modalidade
    tipo: str | None = None
    orgao_julgador: OrgaoJulgador | None = None
    relator: str | None = None
    unidade_jurisdicionada: str | None = None
    exercicios: list[int] = []
    evidencia: Evidencia | None = None


class Votacao(Base):
    unanime: bool
    relator_vencido: bool = False
    redator_voto_vencedor: str | None = None
    evidencia: Evidencia


class Fundamento(Base):
    texto: str
    fonte: FonteFundamento = FonteFundamento.VOTO
    evidencia: Evidencia


class Citacao(Base):
    citacao: str
    evidencia: Evidencia


class Consequencias(Base):
    multa: SituacaoConsequencia | None = None
    debito: SituacaoConsequencia | None = None
    alteracao_multa: Alteracao | None = None
    alteracao_debito: Alteracao | None = None
    evidencia: Evidencia | None = None


class Ocorrencia(Base):
    """Ponto decidido: irregularidade, item de resposta a consulta, requisito de cautelar…"""
    id: str
    titulo: str
    resumo: str
    relacionada_ao_merito: bool = True
    fundamentos: list[Fundamento] = []
    normas: list[Citacao] = []
    precedentes: list[Citacao] = []
    consequencias: Consequencias | None = None
    responsaveis: list[str] = []


class ResultadoPorResponsavel(Base):
    responsavel: str
    resultado: Resultado
    providencias: list[Providencia] = []


class Julgamento(Base):
    resultado: list[Resultado] = Field(min_length=1)
    providencias: list[Providencia] = []
    por_responsavel: list[ResultadoPorResponsavel] = []
    evidencia: Evidencia


class Ficha(Base):
    processo: Processo
    especie_recursal: Modalidade | None = None
    votacao: Votacao | None = None
    ocorrencias: list[Ocorrencia] = []
    julgamento: Julgamento
    nao_identificado: list[str] = []

    # --- utilidades -----------------------------------------------------------

    def evidencias(self) -> Iterator[tuple[str, Evidencia]]:
        """Percorre todas as evidências com um caminho legível (para relatórios)."""
        if self.processo.evidencia:
            yield "processo", self.processo.evidencia
        if self.votacao:
            yield "votacao", self.votacao.evidencia
        for oc in self.ocorrencias:
            for i, f in enumerate(oc.fundamentos):
                yield f"ocorrencias[{oc.id}].fundamentos[{i}]", f.evidencia
            for i, n in enumerate(oc.normas):
                yield f"ocorrencias[{oc.id}].normas[{i}]", n.evidencia
            for i, p in enumerate(oc.precedentes):
                yield f"ocorrencias[{oc.id}].precedentes[{i}]", p.evidencia
            if oc.consequencias and oc.consequencias.evidencia:
                yield f"ocorrencias[{oc.id}].consequencias", oc.consequencias.evidencia
        yield "julgamento", self.julgamento.evidencia

    def nomes_de_pessoas(self) -> set[str]:
        """Nomes de pessoas naturais conhecidos pela Ficha (vedados na ementa, art. 10, § 2º)."""
        nomes: set[str] = set()
        if self.processo.relator:
            nomes.add(self.processo.relator)
        if self.votacao and self.votacao.redator_voto_vencedor:
            nomes.add(self.votacao.redator_voto_vencedor)
        for oc in self.ocorrencias:
            nomes.update(oc.responsaveis)
        for r in self.julgamento.por_responsavel:
            nomes.add(r.responsavel)
        return {n.strip() for n in nomes if n and n.strip()}

    def normas_citadas(self) -> list[str]:
        return [n.citacao for oc in self.ocorrencias for n in oc.normas]
