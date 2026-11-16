versao: 0.1

Uma ficha extraída de uma deliberação do Tribunal de Contas do Estado de Pernambuco citou trechos que um programa não encontrou literalmente no texto. Para cada item abaixo, faça uma de duas coisas:

- se a informação estiver no texto, devolva em "trecho" um fragmento LITERAL (10 a 40 palavras) que a comprove, copiado exatamente como está, e em "pagina" o número do marcador [[p. N]] mais próximo acima dele;
- se a informação não estiver no texto, devolva "remover": true.

Não corrija ortografia, não junte pedaços separados, não resuma. Um programa vai conferir de novo.

Responda somente com um objeto JSON neste formato:
{"correcoes": [{"caminho": "…", "trecho": "…", "pagina": 1, "remover": false}]}

<itens>
{{itens}}
</itens>

<texto>
{{voto_paginado}}
</texto>
