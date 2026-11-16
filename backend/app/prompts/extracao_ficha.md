versao: 0.1

Você vai ler uma deliberação do Tribunal de Contas do Estado de Pernambuco e preencher uma ficha estruturada. A ficha alimenta as etapas seguintes de elaboração da ementa, e cada informação será conferida por um programa contra o texto original. Por isso:

- Para cada informação com campo "evidencia", copie em "trecho" um fragmento literal do texto (10 a 40 palavras) que a comprove e informe em "pagina" o número do marcador [[p. N]] mais próximo acima do fragmento. Copie exatamente, sem corrigir, resumir nem juntar pedaços separados.
- Se uma informação não estiver no texto, deixe o campo como null (ou a lista vazia) e coloque o nome do campo em "nao_identificado". Não deduza.
- Pareceres e relatórios transcritos só contam como fundamento se o voto os adota expressamente ("acolho", "adoto como razões de decidir"). Registre a origem em "fonte": "voto", "parecer_mpc" ou "relatorio_auditoria".
- Se houver voto vencedor diferente do voto do relator, os fundamentos vêm do voto vencedor; marque "relator_vencido": true.

O que preencher:
1. processo: número, modalidade (exatamente uma de: {{modalidades}}), tipo (ex.: CONFORMIDADE, OPERACIONAL; null se não houver), órgão julgador (PLENO, PRIMEIRA_CAMARA ou SEGUNDA_CAMARA), relator, unidade jurisdicionada, exercícios (anos), objeto (uma frase curta, nominal, sem nomes de pessoas).
2. votacao: unânime ou por maioria; se o relator foi vencido, quem redige o voto vencedor.
3. ocorrencias: cada questão decidida que tenha fundamentação própria (irregularidade, item de resposta a consulta, requisito de cautelar, preliminar). Para cada uma: id ("oc1", "oc2"…), título nominal curto (sem verbo, até 12 palavras), resumo em uma frase, fundamentos, normas e precedentes citados, consequências (multa e débito: "APLICADA", "NAO_APLICADA" ou null; alteração em recurso: "MANUTENCAO", "REDUCAO", "EXCLUSAO", "MAJORACAO" ou null), responsáveis (nomes como aparecem) e se integra o fundamento do julgamento de mérito.
4. julgamento: resultado (um ou mais de: {{resultados}}; para consulta conhecida e respondida, use lista vazia), providências (zero ou mais de: {{providencias}}), resultado por responsável quando o voto distinguir.

Responda somente com um objeto JSON neste formato:

{
  "processo": {"numero": "…", "modalidade": "…", "tipo": null, "orgao_julgador": "PLENO", "relator": "…", "unidade_jurisdicionada": "…", "exercicios": [2024], "objeto": "…",
               "evidencia": {"trecho": "…", "pagina": 1}},
  "especie_recursal": null,
  "votacao": {"unanime": true, "relator_vencido": false, "redator_voto_vencedor": null, "evidencia": {"trecho": "…", "pagina": 1}},
  "ocorrencias": [
    {"id": "oc1", "titulo": "…", "resumo": "…", "relacionada_ao_merito": true,
     "fundamentos": [{"texto": "…", "fonte": "voto", "evidencia": {"trecho": "…", "pagina": 1}}],
     "normas": [{"citacao": "Lei nº 14.133/2021, art. 75", "evidencia": {"trecho": "…", "pagina": 1}}],
     "precedentes": [{"citacao": "Acórdão T.C. nº 0000/2023", "evidencia": {"trecho": "…", "pagina": 1}}],
     "consequencias": {"multa": null, "debito": null, "alteracao_multa": null, "alteracao_debito": null, "evidencia": null},
     "responsaveis": []}
  ],
  "julgamento": {"resultado": ["…"], "providencias": [], "por_responsavel": [], "evidencia": {"trecho": "…", "pagina": 1}},
  "nao_identificado": []
}

<texto>
{{voto_paginado}}
</texto>
