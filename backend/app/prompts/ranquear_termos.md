versao: 0.1

Você vai escolher, numa lista de candidatos, os termos do Tesauro de Contas Nacional que melhor indexam um ponto decidido pelo Tribunal de Contas do Estado de Pernambuco. A lista abaixo é o único universo válido: ela foi recuperada da base do tesauro. Um programa descartará qualquer identificador que não esteja nela.

- Devolva de 0 a 5 identificadores, do mais adequado ao menos adequado.
- Prefira o termo mais específico que ainda cubra o assunto inteiro.
- Não devolva dois termos em que um é o termo genérico do outro; fique com o específico.
- Não escolha um termo só porque uma palavra coincide: ele precisa representar o assunto decidido.
- Para cada escolha, uma justificativa de até 15 palavras.
- Se nenhum candidato servir, devolva lista vazia e, em "sugestao_livre", um termo nominal equivalente (Portaria Normativa TC nº 322/2026, art. 4º, III), no singular, em até 5 palavras. Ele será mostrado ao usuário marcado como "fora do tesauro". Se algum candidato servir, "sugestao_livre" pode trazer um termo que complemente a indexação, ou null.

Responda somente com um objeto JSON neste formato:
{"escolhas": [{"id": "…", "justificativa": "…"}], "sugestao_livre": null}

<ponto>
{{ponto}}
</ponto>
<tese_escolhida>
{{tese}}
</tese_escolhida>
<candidatos>
id | termo | termo genérico
{{candidatos}}
</candidatos>
