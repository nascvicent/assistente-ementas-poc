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
| Termo | Claude + usuário | prompt `sugerir_termos_sem_tesauro`; todos marcados **fora do tesauro** |
| Ementa | Claude + código | prompt `redacao_caso_razoes` para caso e razões; cabeçalho, dispositivo, numeração e títulos **por código** |
| Alerta | código + Claude | linter E01–E21, evidências não confirmadas, dispositivo A DEFINIR; prompt `verificacao_final` com trechos conferidos; ciência obrigatória nos alertas altos |
| Conversa | Claude | prompt `conversa`, com as páginas mais relacionadas à pergunta; não avança a etapa |

A aba **Publicada** mostra a ementa que já vinha no inteiro teor, para comparar
com a gerada. A aba **Registro** lista cada chamada (prompt e versão), verificação
e escolha; "Exportar a conversa" baixa tudo, com a ficha em JSON.

## Diferenças em relação à arquitetura definitiva

- **Sem gateway (regra 8 do CLAUDE.md, princípio 8 do documento 01).** A página
  chama o Claude direto. Os prompts, porém, são os mesmos arquivos de
  `backend/app/prompts/`, embutidos pelo script de geração.
- **Sem base do TCN (pendência P4).** Os termos são sugestões do Claude, sempre
  marcadas como fora do tesauro e confirmadas pelo usuário (art. 4º, III).
- **Sem banco.** O registro de eventos vive na página; exporta-se em arquivo.
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
python scripts/gerar_demo.py          # gera frontend/demo/dist/
cd backend && pytest                  # inclui a paridade JS × Python
```

Depois, republicar os arquivos de `dist/` no mesmo endereço.
