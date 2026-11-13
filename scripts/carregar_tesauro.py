#!/usr/bin/env python3
"""Carga do Tesauro de Contas Nacional a partir de exportação SKOS.

Exemplos:
  python scripts/carregar_tesauro.py tcn.rdf --saida dados/tesauro.json
  python scripts/carregar_tesauro.py tcn.rdf --database-url postgresql+psycopg://...

A fonte oficial (instância TemaTres ou arquivo do IRB) ainda está por confirmar (P4).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.tesauro.carga import carregar  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fonte", help="arquivo ou URL da exportação SKOS")
    p.add_argument("--saida", type=Path, help="snapshot JSON (também usado para comparar com a carga anterior)")
    p.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--formato", help="xml, turtle… (padrão: detectar pela extensão)")
    a = p.parse_args()
    if not a.saida and not a.database_url:
        p.error("informe --saida e/ou --database-url")
    rel = carregar(a.fonte, a.saida, a.database_url, a.formato)
    print(rel.texto())
    for linha in rel.relacoes_quebradas[:20]:
        print(f"  relação quebrada: {linha}")
    for linha in rel.ciclos[:20]:
        print(f"  ciclo: {linha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
