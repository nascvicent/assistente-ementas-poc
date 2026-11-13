"""Gateway de modelo (doc 01, seção 4; regra de arquitetura 8).

Nenhuma etapa importa SDK de provedor: todas chamam `GatewayModelo.gerar`, que
- renderiza o prompt versionado (arquivo em app/prompts/);
- envia ao provedor através de um `Provedor` plugável;
- valida a saída contra o esquema Pydantic da etapa (regra 2);
- tenta de novo uma vez, apontando o erro de validação;
- registra a chamada como evento (regra 7).

O provedor real depende da decisão D1/P5. `ProvedorFalso` serve para testes.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

PASTA_PROMPTS = Path(__file__).resolve().parents[1] / "prompts"

T = TypeVar("T", bound=BaseModel)


# --- prompts versionados ------------------------------------------------------

@dataclass(frozen=True)
class PromptVersionado:
    nome: str
    versao: str
    texto: str

    def renderizar(self, variaveis: dict[str, Any]) -> str:
        faltando = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", self.texto)) - set(variaveis)
        if faltando:
            raise KeyError(f"Prompt {self.nome}: variáveis ausentes: {', '.join(sorted(faltando))}")

        def valor(m: re.Match) -> str:
            v = variaveis[m.group(1)]
            return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)

        return re.sub(r"\{\{\s*(\w+)\s*\}\}", valor, self.texto)


def carregar_prompt(nome: str, pasta: Path = PASTA_PROMPTS) -> PromptVersionado:
    """Lê app/prompts/<nome>.md. Primeira linha obrigatória: `versao: X.Y`."""
    bruto = (pasta / f"{nome}.md").read_text(encoding="utf-8")
    m = re.match(r"versao:\s*(\S+)\s*\n", bruto)
    if not m:
        raise ValueError(f"Prompt {nome} sem linha 'versao:' no topo.")
    return PromptVersionado(nome, m.group(1), bruto[m.end():].lstrip("\n"))


# --- provedor -----------------------------------------------------------------

@dataclass
class RespostaProvedor:
    texto: str
    modelo: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


class Provedor(Protocol):
    def completar(self, prompt: str, esquema_json: dict) -> RespostaProvedor: ...


@dataclass
class ProvedorFalso:
    """Devolve respostas pré-definidas, em ordem. Registra os prompts recebidos."""
    respostas: list[str | dict]
    modelo: str = "falso"
    recebidos: list[str] = field(default_factory=list)

    def completar(self, prompt: str, esquema_json: dict) -> RespostaProvedor:
        self.recebidos.append(prompt)
        r = self.respostas.pop(0)
        return RespostaProvedor(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False), self.modelo)


# --- gateway ------------------------------------------------------------------

class ErroSaidaModelo(Exception):
    """A saída não passou no esquema depois de todas as tentativas."""


@dataclass
class ResultadoChamada(Generic[T]):
    saida: T
    modelo: str
    versao_prompt: str
    tentativas: int
    tokens_entrada: int
    tokens_saida: int
    duracao_ms: int


RegistrarEvento = Callable[[dict], None]


def _extrair_json(texto: str) -> str:
    """Aceita JSON puro ou dentro de bloco ```json; nada além disso (sem parsear texto livre)."""
    m = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", texto, re.DOTALL)
    return m.group(1) if m else texto.strip()


@dataclass
class GatewayModelo:
    provedor: Provedor
    registrar: RegistrarEvento | None = None
    max_tentativas: int = 2

    def gerar(self, prompt: PromptVersionado, variaveis: dict[str, Any], esquema: type[T], etapa: str | None = None) -> ResultadoChamada[T]:
        texto_prompt = prompt.renderizar(variaveis)
        esquema_json = esquema.model_json_schema()
        inicio = time.monotonic()
        tokens_in = tokens_out = 0
        erro: str | None = None
        modelo = "?"
        for tentativa in range(1, self.max_tentativas + 1):
            enviado = texto_prompt if erro is None else (
                f"{texto_prompt}\n\nA resposta anterior não seguiu o esquema JSON exigido. Erro:\n{erro}\n"
                "Responda novamente apenas com o JSON válido."
            )
            resp = self.provedor.completar(enviado, esquema_json)
            modelo = resp.modelo
            tokens_in += resp.tokens_entrada
            tokens_out += resp.tokens_saida
            try:
                saida = esquema.model_validate_json(_extrair_json(resp.texto))
            except ValidationError as e:
                erro = str(e)
                self._registrar(etapa or prompt.nome, prompt, modelo, variaveis, None, erro, resp, inicio)
                continue
            resultado = ResultadoChamada(saida, modelo, prompt.versao, tentativa, tokens_in, tokens_out, int((time.monotonic() - inicio) * 1000))
            self._registrar(etapa or prompt.nome, prompt, modelo, variaveis, saida.model_dump(mode="json"), None, resp, inicio)
            return resultado
        raise ErroSaidaModelo(f"{prompt.nome}: saída inválida após {self.max_tentativas} tentativas: {erro}")

    def _registrar(self, etapa, prompt, modelo, entrada, saida, erro, resp, inicio):
        if not self.registrar:
            return
        self.registrar({
            "etapa": etapa,
            "tipo": "chamada_modelo" if erro is None else "erro",
            "entrada": entrada,
            "saida": saida if erro is None else {"erro": erro, "bruto": resp.texto[:2000]},
            "versao_prompt": f"{prompt.nome}@{prompt.versao}",
            "modelo": modelo,
            "tokens": resp.tokens_entrada + resp.tokens_saida,
            "duracao_ms": int((time.monotonic() - inicio) * 1000),
        })
