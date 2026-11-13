# Documentos do projeto

As versões de referência vivem no Projeto "plataforma semelhante - tcepe" do Claude:

| Documento | Conteúdo |
|---|---|
| `01-arquitetura.md` | Fluxo, componentes, modelo de dados, stack, avaliação |
| `02-regras-ementa-tcepe.md` | Portaria Normativa TC nº 322/2026, estrutura da ementa, enumerações, linter E01–E21 |
| `03-instrucoes-e-backlog.md` | Instruções para o assistente de código, roteiro, pendências P1–P7 |
| `04-prompts.md` | Prompt único (Fase 0) e prompts por etapa B1–B6 |

Copie-os para esta pasta quando quiser versioná-los junto com o código.

## Onde cada regra virou código

| Regra | Arquivo |
|---|---|
| Enumerações (doc 02, §6) | `backend/app/dominio/enumeracoes.py` |
| Dispositivo por modalidade (doc 02, §4.4, **provisório — P1**) | `backend/app/dominio/dispositivo.py` |
| Ficha do caso (doc 01, §5.1) | `backend/app/esquemas/ficha.py` |
| Linter E01–E21 (doc 02, §7) | `backend/app/verificadores/linter_ementa.py` |
| Evidência literal (doc 01, §6.1) | `backend/app/verificadores/evidencia.py` |
| Remoção da ementa do inteiro teor (doc 02, §10) | `backend/app/ingestao/secoes.py` |
| Tesauro: busca, expansão TG, IDs em conjunto fechado (doc 01, §6.3) | `backend/app/tesauro/indice.py` |
| Máquina de estados (doc 01, §3.1) | `backend/app/harness/estados.py` |
| Escolha × pergunta (doc 01, §3) | `backend/app/harness/roteador.py` |
| Gateway de modelo (regra 8) | `backend/app/modelo/gateway.py` |
| Esquema do banco (doc 01, §5.2) | `scripts/sql/001_schema.sql` |

## Decisões tomadas nesta implementação (a validar)

- O título da seção IV aceito pelo linter é "TESE DE JULGAMENTO" (termo da Portaria);
  "TESE" é aceito com alerta de gravidade baixa até a Diretoria de Julgamento confirmar.
- Seção IV ausente não gera alerta (tese dispensável, art. 8º, p.u.).
- Modalidades sem tabela de dispositivo ficam `A_DEFINIR` e não são avaliadas pela regra E08.
- E18 (verbo no cabeçalho) e E19 (adjetivo valorativo) são heurísticas por lista de palavras.
- DOCX/ODT/TXT sem marcas de página viram página única, com aviso: as citações usarão p. 1.
