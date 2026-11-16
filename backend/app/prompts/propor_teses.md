versao: 0.1

Você vai propor quatro redações de tese de julgamento para um ponto decidido pelo Tribunal de Contas do Estado de Pernambuco. O usuário escolherá uma. A tese irá para o repositório de jurisprudência e será lida por quem não conhece o processo.

Uma tese, segundo a Portaria Normativa TC nº 322/2026, art. 8º:
- é um enunciado abstrato e geral, aplicável a casos semelhantes;
- entende-se sozinha, sem referência ao caso;
- expressa uma regra ou uma interpretação identificável;
- não diz mais nem menos do que a deliberação decidiu.

Escreva as quatro em profundidade crescente. Cada uma contém a anterior e acrescenta um elemento:
1. A regra geral: conduta ou situação e sua qualificação jurídica.
2. A regra + a norma que a fundamenta.
3. A regra + norma + a condição ou circunstância que delimita quando ela vale.
4. A regra + norma + condição + a consequência, o critério de responsabilização ou o precedente citado.

Restrições:
- Uma frase por tese, com inicial maiúscula e ponto final.
- Use apenas normas e precedentes da lista em <normas_permitidas>.
- Não use nenhum item de <termos_proibidos> (nomes, lugares, números de processo).
- Não cite valores em reais, datas nem número de processo.
- Não use "no caso", "na espécie", "nos autos", "em análise preliminar".
- Se o ponto não comportar um dos níveis (por exemplo, o voto não indica condição), devolva "texto": null nesse nível em vez de inventar.
- Para cada tese, informe em "acrescentou" o elemento novo em até 6 palavras.
- Se o ponto for mera aplicação de regra a fatos, sem entendimento aproveitável em outros casos, devolva "sem_tese": true e explique em "motivo" em uma frase.
{{orientacao}}

Responda somente com um objeto JSON neste formato:
{"sem_tese": false, "motivo": null, "teses": [{"nivel": 1, "texto": "…", "acrescentou": "regra geral"}, {"nivel": 2, "texto": "…", "acrescentou": "…"}, {"nivel": 3, "texto": "…", "acrescentou": "…"}, {"nivel": 4, "texto": "…", "acrescentou": "…"}]}

<ponto>
{{ponto}}
</ponto>
<normas_permitidas>
{{normas_permitidas}}
</normas_permitidas>
<termos_proibidos>
{{termos_proibidos}}
</termos_proibidos>
