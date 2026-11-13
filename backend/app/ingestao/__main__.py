"""python -m app.ingestao voto.pdf [--json]  → texto paginado sem o bloco de ementa."""
import json
import sys

from app.ingestao import carregar_arquivo


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("uso: python -m app.ingestao <voto.pdf|docx|odt|txt> [--json]", file=sys.stderr)
        return 2
    doc, bloco = carregar_arquivo(argv[1])
    for aviso in doc.avisos:
        print(f"aviso: {aviso}", file=sys.stderr)
    if "--json" in argv:
        print(json.dumps({
            "nome": doc.nome, "formato": doc.formato, "hash": doc.hash_arquivo,
            "paginas": [{"numero": p.numero, "secao": p.secao, "texto": p.texto} for p in doc.paginas],
            "ementa_removida": bloco.texto if bloco else None,
            "avisos": doc.avisos,
        }, ensure_ascii=False, indent=2))
    else:
        print(doc.texto_paginado())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
