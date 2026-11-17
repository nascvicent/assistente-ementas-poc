# Demonstração online

Versão do protótipo que lê um voto de verdade e chama o Claude etapa por etapa.
Publicada em https://claude.ai/artifact/58CuCxJuv7zo79EuJzozHC (privada até ser
compartilhada). Só funciona aberta pelo Claude, porque usa a conta de quem abre.

## O que ela faz

| Etapa | Quem faz | Como |
|---|---|---|
| Leitura do voto | navegador | `leitura.js`: PDF (pdf.js), DOCX e ODT (JSZip), TXT; texto por página, limpeza e **remoção da ementa já existente** |
| Ficha | Claude + código | prompt `extracao_ficha`; enumerações saneadas e **cada trecho conferido na página** (`nucleo.js`) |
| Ponto | usuário | escolha numerada; atalho quando só há um ponto |
| Tese | Claude + código | prompt `propor_teses`; verificador barra nomes do caso, valores e normas que não estão no voto; dispensar ou pedir outras redações |
| Termo | Claude + código + usuário | prompt `consultas_tesauro` (expressões de busca) → busca na **cópia local do TCN** (`tesauro.js`) → prompt `ranquear_termos` escolhe **identificadores** entre os candidatos → código descarta o que não estiver na lista; a tela mostra o rótulo da base. Também: busca manual no TCN, sugestão fora do tesauro (marcada) e termo digitado (reconhecido se existir no TCN) |
| Ementa | Claude + código | prompt `redacao_caso_razoes` para caso e razões; cabeçalho, dispositivo, numeração e títulos **por código** |
| Alerta | código + Claude | linter E01–E21, evidências não confirmadas, dispositivo A DEFINIR; prompt `verificacao_final` com trechos conferidos; ciência obrigatória nos alertas altos |
| Conversa | Claude | prompt `conversa`, com as páginas mais relacionadas à pergunta; não avança a etapa |

Também na tela: nova tentativa focada (`corrigir_evidencias`) quando um trecho da
ficha não é achado no voto; escrever ou editar a tese (passa pelo mesmo
verificador); digitar um termo próprio ("genérico > termo"); retirar um ponto já
incluído (ação `RETIRAR_OCORRENCIA`, também no backend); incluir ao final as
referências normativas e os precedentes (art. 10, § 1º), montadas por código.

## Avaliação

A aba **Avaliação** compara, por código (`avaliacao.js`), a ementa do fluxo e a do
**prompt atual do AuroraChat** (`prompt_unico_aurorachat`, versão B-1.0: o
"prompt-mestre" recebido em 17/11/2026; a versão A-0.1 era a adaptação da Parte A
do documento 04), rodado sobre o mesmo voto sem a ementa publicada, com a
**publicada**. A saída do AuroraChat é posta no formato publicado antes de medir
(`normalizarFormato`: "EMENTA:", itens numerados, teses em itens); os ajustes
feitos e os pontos do linter no texto como saiu aparecem em linhas próprias.
Medidas: semelhança
geral e por seção, termos do cabeçalho em comum, mesmo resultado no dispositivo,
pontos do linter, normas e valores sem suporte no voto, quantidade de itens. Tem
nota do revisor (1 a 5) para cada lado e "Copiar resumo da avaliação", em colunas
separadas por tabulação, para colar numa planilha.

## Sessões salvas

Cada ementa fica gravada no armazenamento da página, em área privada de quem a
fez (`data/users/<id>/`, que nem o dono da página lê), com o texto do voto. A barra
lateral lista as anteriores com onde pararam ("Parou na tese", "Ementa concluída")
e permite retomar ou excluir.

A aba **Publicada** mostra a ementa que já vinha no inteiro teor, para comparar
com a gerada. A aba **Registro** lista cada chamada (prompt e versão), verificação
e escolha; "Exportar a conversa" baixa tudo, com a ficha em JSON.

## Diferenças em relação à arquitetura definitiva

- **Sem gateway (regra 8 do CLAUDE.md, princípio 8 do documento 01).** A página
  chama o Claude direto. Os prompts, porém, são os mesmos arquivos de
  `backend/app/prompts/`, embutidos pelo script de geração.
- **TCN sem remissivas nem notas.** A cópia local (`dados/tcn.json`, 2.594 termos,
  exportação completa de 17/11/2026 do serviço do IRB, hierarquia até 5 níveis)
  não traz termos remissivos (USE/UP) nem notas de escopo. Assuntos que o TCN não
  cobre (ex.: vacinação, duodécimo) entram como fora do tesauro.
- **Busca só por palavras.** Sem busca por significado (pgvector), o Claude
  sugere expressões de busca antes; a escolha final continua restrita à base.
- **Sem banco do Tribunal.** As sessões e o registro de eventos ficam no
  armazenamento da página, não na tabela `evento`; exporta-se em arquivo.
- **Núcleo duplicado em JavaScript.** `nucleo.js` é porte do Python; a paridade é
  testada em `backend/tests/test_paridade_js.py`. Mudou uma regra, mude os dois.
- A montagem do cabeçalho e do dispositivo existe só em JavaScript por enquanto;
  vai para o backend na Fase 2 (tabela de dispositivo ainda **provisória**, P1).

## Sigilo

Fora da rede do Tribunal. Só votos fictícios ou já publicados: a página pede essa
confirmação antes de aceitar arquivo ou texto colado. O arquivo é lido no
navegador; só o texto vai ao Claude.

## Atualizar

```bash
python scripts/gerar_demo.py               # gera frontend/demo/dist/
cd backend && pytest                       # inclui a paridade JS × Python
python frontend/demo/testes/e2e_demo.py    # navegador, Claude e armazenamento simulados
```

Depois, republicar os arquivos de `dist/` no mesmo endereço.

## Tesauro do IRB

Atualizar a cópia local: `python scripts/carregar_tesauro.py <exportação.json> --saida frontend/demo/dados/tcn.json`
(aceita o JSON do TemaTres e SKOS) e gerar a demo de novo. O relatório da carga
mostra termos novos, alterados e removidos em relação à anterior.


O TCN tem serviço web aberto do TemaTres em
`https://tesauro.irbcontas.org.br/vocab/services.php`, feito para integração com
sistemas. Em 16/11/2026 o endereço estava atrás de uma verificação anti-robô da
Cloudflare: acesso por programa recebe "Just a moment…" (HTTP 403). Isso vale
para esta página e também para o servidor do Tribunal. Caminhos: o IRB liberar o
acesso do servidor do Tribunal ao serviço, ou fornecer a exportação SKOS completa
para carga local (`scripts/carregar_tesauro.py`), que é o que a arquitetura já
prevê (índice local, documento 01, seção 4).
