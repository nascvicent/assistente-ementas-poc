PROJETO
Aplicação web interna do TCE-PE que conduz a elaboração de ementas de deliberações
colegiadas em etapas: voto → ficha → ocorrência → tese → termo do Tesauro de Contas
Nacional → montagem → alerta. Inspirada no ASSINE (TCE-CE). Substitui o uso de um
prompt único no AuroraChat (LibreChat).

DOCUMENTOS DE REFERÊNCIA (ler antes de propor ou escrever código)
- docs/01-arquitetura.md: fluxo, componentes, modelo de dados, stack.
- docs/02-regras-ementa-tcepe.md: estrutura da ementa, enumerações, linter, pendências.
- docs/03-instrucoes-e-backlog.md: instruções, roteiro e pendências.
- docs/04-prompts.md: prompts por etapa e prompt único adaptado para o AuroraChat.
- Protótipo de interface: frontend/prototipo/index.html (referência visual e de fluxo);
  correspondência com o backend em docs/contrato-interface.md.
(As versões mais atuais vivem no Projeto "plataforma semelhante - tcepe" do Claude.)

REGRAS DE ARQUITETURA (não negociáveis)
1. A ordem das etapas e as transições ficam em código (máquina de estados).
   O modelo nunca decide o próximo passo.
2. Uma chamada de modelo = uma tarefa, com esquema Pydantic de saída.
   Nada de parsear texto livre.
3. Todo fato extraído do voto carrega trecho literal + página, conferido por código.
4. Termos do tesauro: o modelo devolve IDs de uma lista de candidatos; código valida;
   a interface mostra o rótulo do banco. Nunca criar termo.
5. Cabeçalho, dispositivo, numeração e títulos de seção são montados por código.
6. Prompts em arquivos versionados em backend/app/prompts/, nunca embutidos em funções.
7. Toda chamada de modelo e toda escolha do usuário gera registro na tabela evento.
8. O acesso ao modelo passa pelo gateway; nenhuma etapa importa SDK de provedor.

REGRAS DE DOMÍNIO
- Norma: Portaria Normativa TC nº 322/2026 (resumo no documento 02, seção 0).
  Ela prevalece sobre qualquer regra dos documentos.
- Estrutura: EMENTA (cabeçalho em maiúsculas, só termos nominais) / I. CASO EM EXAME /
  II. RAZÕES DE DECIDIR / III. DISPOSITIVO / IV. TESE DE JULGAMENTO (dispensável).
  Sem "Questão em discussão". Referências normativas ao final são opcionais.
- Termos do cabeçalho vêm preferencialmente do tesauro; termo livre é permitido,
  mas sempre marcado como fora do tesauro e confirmado pelo usuário.
- Nenhum nome de pessoa natural na ementa (art. 10, § 2º).
- Fonte dos fundamentos é o voto vencedor. O bloco de ementa que já vier dentro do
  inteiro teor é removido antes de qualquer chamada de modelo.
- Não inventar regra do TCE-PE. Na dúvida, marcar "A DEFINIR" e perguntar.

CÓDIGO
- Backend Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL + pgvector.
- Frontend React + TypeScript.
- Nomes de domínio em português (ficha, ocorrencia, tese, ementa); termos técnicos
  de framework em inglês.
- Todo verificador e toda transição de estado com teste de unidade.
- Mudança de prompt exige rodar o conjunto de avaliação e registrar o resultado.
- Nenhum voto real, nome de responsável ou dado pessoal em teste, fixture ou commit.
  Usar votos fictícios ou anonimizados.

COMUNICAÇÃO
- Responder em português do Brasil.
- Ao propor mudança de arquitetura, dizer qual princípio do documento 01 ela afeta.

COMANDOS
- Testes: `cd backend && pytest`
- Subir ambiente: `docker compose up --build` (API em :8000, Postgres em :5432)
- Carregar tesauro: `python scripts/carregar_tesauro.py <arquivo-ou-url-skos> --saida dados/tesauro.json`
