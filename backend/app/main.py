"""API (Fase 1): utilidades do núcleo, sem fluxo de sessão ainda.

O fluxo completo por sessão (máquina de estados + etapas com modelo) entra na Fase 2.
"""
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.ingestao import FormatoNaoSuportado, carregar_bytes
from app.verificadores.linter_ementa import verificar

app = FastAPI(title="Assistente de Ementas TCE-PE (POC)", version="0.1.0")

AVISO_IA = "Conteúdo gerado com auxílio de IA generativa; deve ser revisado pelo usuário."


@app.get("/saude")
def saude() -> dict:
    return {"status": "ok", "aviso": AVISO_IA}


@app.post("/ingestao")
async def ingestao(arquivo: UploadFile) -> dict:
    try:
        doc, bloco = carregar_bytes(await arquivo.read(), arquivo.filename or "voto.txt")
    except FormatoNaoSuportado as e:
        raise HTTPException(415, str(e)) from e
    return {
        "nome": doc.nome,
        "formato": doc.formato,
        "hash": doc.hash_arquivo,
        "paginacao_real": doc.paginacao_real,
        "paginas": [{"numero": p.numero, "secao": p.secao, "texto": p.texto} for p in doc.paginas],
        "ementa_removida": asdict(bloco) if bloco else None,
        "avisos": doc.avisos,
    }


class PedidoLinter(BaseModel):
    ementa: str
    texto_voto: str | None = None


@app.post("/linter")
def linter(pedido: PedidoLinter) -> dict:
    from app.verificadores.linter_ementa import ContextoLinter

    achados = verificar(pedido.ementa, ContextoLinter(texto_voto=pedido.texto_voto))
    return {"total": len(achados), "achados": [asdict(a) for a in achados]}
