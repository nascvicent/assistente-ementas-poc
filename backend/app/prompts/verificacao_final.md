versao: 0.1

Você vai comparar partes de uma deliberação do Tribunal de Contas do Estado de Pernambuco em busca de divergências materiais. Não avalie o mérito da decisão nem o estilo.

1. Para cada ponto listado, compare o que a fundamentação diz sobre a consequência (resultado, multa, débito, valores, base legal, responsáveis) com o que a parte dispositiva determina. Compare também, quando existirem, a resposta dada e o enunciado de prejulgado ou de súmula proposto.
   Registre uma divergência somente quando puder citar os dois trechos literais que se contradizem, com as páginas (marcadores [[p. N]]). Copie os trechos exatamente; um programa vai conferi-los. Diferença de redação sem mudança de sentido não é divergência. Se não houver nenhuma, devolva lista vazia.

2. Para cada tese da ementa, diga se ela é fiel, amplia ou restringe o que foi decidido no ponto correspondente, citando o trecho literal do voto que mostra o limite.

Responda somente com um objeto JSON neste formato:
{"divergencias": [{"descricao": "…", "trecho_a": "…", "pagina_a": 1, "trecho_b": "…", "pagina_b": 2}],
 "alcance_teses": [{"tese": 1, "situacao": "fiel", "explicacao": "…", "trecho": "…", "pagina": 1}]}

<voto>
{{voto_paginado}}
</voto>
<pontos>
{{pontos}}
</pontos>
<teses>
{{teses}}
</teses>
