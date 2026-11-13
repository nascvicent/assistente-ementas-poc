# Assistente de Ementas (POC) — TCE-PE

Prova de conceito de uma aplicação que conduz a elaboração de ementas de deliberações
colegiadas do TCE-PE em etapas verificáveis, conforme a Portaria Normativa TC nº 322/2026:

```
voto → ficha → ocorrência → tese → termo do Tesauro de Contas Nacional → montagem → alerta
```

O código conduz o fluxo; o modelo de linguagem só executa tarefas pequenas, com saída
estruturada e conferida por código. Detalhes em `docs/` e em `CLAUDE.md`.

## Estado atual (Fase 1 — núcleo sem interface)

| Módulo | Situação |
|---|---|
| `dominio/` enumerações, rótulos de modalidade, dispositivo provisório | feito (tabela de dispositivo **provisória**, pendência P1) |
| `esquemas/ficha.py` Ficha do caso (Pydantic) | feito |
| `ingestao/` PDF, DOCX, ODT, TXT → texto por página; remoção do bloco EMENTA | feito |
| `verificadores/evidencia.py` conferência de trecho literal × página | feito |
| `verificadores/linter_ementa.py` regras E01–E21 | feito (E18/E19 heurísticas) |
| `tesauro/` leitura SKOS, índice lexical, validação de IDs, ordem amplo→específico | feito (busca vetorial pendente) |
| `harness/` máquina de estados e roteador escolha × pergunta | feito |
| `modelo/gateway.py` interface do gateway + implementação falsa para testes | feito (provedor real pendente, P5) |
| Etapas com modelo (extração, teses, ranqueamento, redação, alerta, conversa) | próximo passo |
| Frontend | protótipo navegável em `frontend/prototipo/` (dados simulados); React na Fase 3 |

## Como rodar

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Linha de comando (sem modelo):

```bash
# texto paginado do voto, com o bloco de ementa removido
python -m app.ingestao voto.pdf

# linter sobre uma ementa em texto
python -m app.verificadores.linter_ementa ementa.txt

# carga do tesauro a partir de exportação SKOS (TemaTres)
python scripts/carregar_tesauro.py tcn.rdf --saida dados/tesauro.json
```

Ambiente completo:

```bash
docker compose up --build
```

## Dados

Nenhum voto real, nome de responsável ou dado pessoal entra no repositório.
Os testes usam votos e um tesauro **fictícios**.
