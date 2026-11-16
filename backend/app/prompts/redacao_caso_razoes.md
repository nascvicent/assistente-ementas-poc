versao: 0.1

Você vai redigir duas partes de uma ementa do Tribunal de Contas do Estado de Pernambuco a partir de uma ficha já conferida. Use somente o que está na ficha. O leitor é alguém pesquisando jurisprudência que não leu o processo.

CASO EM EXAME (um parágrafo; até três se o caso exigir)
- Objeto do processo e elementos de fato e de direito indispensáveis ao contexto.
- Comece pelo objeto ("Auditoria Especial de Conformidade realizada…", "Consulta sobre…"). Não use "Trata-se de" nem "Cuida-se de".
- Impessoal, sem juízo de valor, sem adjetivos de ênfase, sem detalhe dispensável.

RAZÕES DE DECIDIR (um item por fundamento principal dos pontos selecionados)
- Uma ideia por item, em até três frases diretas.
- Fiel ao fundamento registrado na ficha: não amplie, não restrinja, não acrescente.
- Linguagem simples; mantenha o termo técnico quando indispensável.
- Sem argumentos acessórios e sem doutrina.

Em ambas: nenhum nome de pessoa natural (use cargo ou posição processual: "o prefeito", "o gestor", "o consulente"); pessoa jurídica privada por termo genérico ("a contratada"); normas na forma registrada na ficha, com "nº" e ano com quatro dígitos; nunca "Carta Magna" ou "Lei Maior" (use "Constituição Federal"); sem latim.

Não escreva cabeçalho, dispositivo, tese nem numeração: outro componente cuida disso.

Responda somente com um objeto JSON neste formato:
{"caso_em_exame": ["…"], "razoes": [{"ocorrencia_id": "oc1", "texto": "…"}]}

<ficha>
{{ficha}}
</ficha>
<pontos_selecionados>
{{pontos}}
</pontos_selecionados>
