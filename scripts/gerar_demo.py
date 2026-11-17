#!/usr/bin/env python3
"""Gera a demonstração online em frontend/demo/dist/.

- prompts.js  ← backend/app/prompts/*.md (mesmos arquivos versionados que o backend usa)
- exemplo.js  ← frontend/demo/exemplo-voto.txt (voto fictício)
- copia index.html, nucleo.js, leitura.js e fluxo.js

Publicada em https://claude.ai/artifact/58CuCxJuv7zo79EuJzozHC
(slug 21661840-3ec0-4d59-af4a-44651f65ad8f), com as capacidades sample e downloads.
"""
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DEMO = RAIZ / "frontend" / "demo"
PROMPTS = RAIZ / "backend" / "app" / "prompts"
ARQUIVOS = ["index.html", "nucleo.js", "avaliacao.js", "tesauro.js", "leitura.js", "fluxo.js"]
SNAPSHOT_TCN = DEMO / "dados" / "tcn.json"


def tesauro_compacto(caminho: Path) -> dict:
    """Snapshot da carga (scripts/carregar_tesauro.py) → formato compacto lido por tesauro.js."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    termos = [[t["id"], t["rotulo"], 1 if t.get("meta") else 0, t.get("tg", []), t.get("alternativos", [])]
              for t in dados["termos"].values()]
    return {"versao": dados["versao"], "fonte": dados["fonte"], "avisos": dados.get("avisos", []), "termos": termos}


def carregar_prompts() -> dict:
    prompts = {}
    for arq in sorted(PROMPTS.glob("*.md")):
        bruto = arq.read_text(encoding="utf-8")
        m = re.match(r"versao:\s*(\S+)\s*\n", bruto)
        if not m:
            sys.exit(f"{arq.name}: falta a linha 'versao:' no topo")
        prompts[arq.stem] = {"versao": m.group(1), "texto": bruto[m.end():].lstrip("\n")}
    return prompts


def main() -> int:
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO / "dist"
    saida.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS:
        shutil.copy(DEMO / nome, saida / nome)
    prompts = carregar_prompts()
    (saida / "prompts.js").write_text("window.PROMPTS = " + json.dumps(prompts, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    if SNAPSHOT_TCN.exists():
        tcn = tesauro_compacto(SNAPSHOT_TCN)
        (saida / "tcn.js").write_text("window.TESAURO_DADOS = " + json.dumps(tcn, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
        print(f"tesauro: {len(tcn['termos'])} termos ({tcn['versao']})")
    exemplo = (DEMO / "exemplo-voto.txt").read_text(encoding="utf-8")
    (saida / "exemplo.js").write_text("window.VOTO_EXEMPLO = " + json.dumps(exemplo, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"demo gerada em {saida} ({len(prompts)} prompts: " + ", ".join(f"{k}@{v['versao']}" for k, v in prompts.items()) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
