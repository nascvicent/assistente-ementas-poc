# Protótipo × backend

Correspondência entre o protótipo (`frontend/prototipo/index.html`) e o núcleo da
Fase 1, para orientar a API de sessão (Fase 2) e o frontend React (Fase 3).

## Etapas

| Trilha do protótipo | Função no protótipo | Estado(s) no backend | O que a API precisa entregar |
|---|---|---|---|
| Voto | `inicio`, `recebe` | `AGUARDANDO_VOTO` → `EXTRAINDO` | Upload; nº de páginas; avisos da ingestão (sem camada de texto, ementa removida p. X–Y) |
| Ficha | tabela da ficha | `EXTRAINDO` → … | Linhas da Ficha com página **conferida** (`Evidencia.pagina_encontrada`); `nao_identificado`; itens não confirmados |
| Ponto | `pedePonto` | `AGUARDANDO_OCORRENCIA` | Ocorrências restantes (título, resumo, página, `relacionada_ao_merito`) |
| Tese | `propoeTeses` | `PROPONDO_TESES` → `AGUARDANDO_TESE` | 4 teses + o elemento acrescentado em cada nível; opção "Dispensar" |
| Tesauro | `buscaTermos` | `BUSCANDO_TERMOS` → `AGUARDANDO_TERMO` | Até 5 termos com `id`, rótulo **do banco** e rótulo do TG |
| Ementa | `monta` | `MONTANDO` → `AGUARDANDO_MAIS_OCORRENCIA` | Versão da ementa por partes, com o trecho novo marcado |
| Alerta | `verifica` | `VERIFICANDO` → `CONCLUIDA` | Achados (código, gravidade, mensagem, referência com página) e regras atendidas |

Os passos de progresso que aparecem enquanto o sistema trabalha (`pensa`) podem vir
por SSE, um evento por verificação concluída. A aba Registro é a leitura da tabela
`evento`.

## Entrada do usuário

O protótipo trata número como escolha e o resto como pergunta. O backend
(`harness/roteador.py`) faz o mesmo e ainda reconhece "voltar", "cancelar",
"sim"/"não" na pergunta do laço e "dispensar a tese". Número fora da lista vira
`OPCAO_INVALIDA`, como no protótipo ("Não há opção N").

## Conferência

A ementa que o protótipo monta com os 4 pontos passa no linter (E01–E21) sem
nenhum ponto a conferir.

## O que o protótipo ainda não mostra

| Falta | Regra | Sugestão |
|---|---|---|
| Termo fora do tesauro (nenhum candidato serve) | Portaria 322/2026, art. 4º, III; E21 | Cartão "Nenhum termo específico encontrado" com o genérico mais próximo e um termo livre marcado "fora do tesauro", com confirmação |
| Busca manual no tesauro | doc 01, §6.3, passo 6 | Campo de busca na etapa Tesauro |
| Pedir novas teses com orientação | doc 01, §6.2 | Opção "Gerar outras redações" (já existe `Acao.PEDIR_NOVAS_TESES`) |
| Editar a tese escolhida | doc 01, §6.2 | Edição inline; gravar `tese_editada` |
| Voltar uma etapa | doc 01, §3.1 | Botão ou comando "voltar" |
| Ciência obrigatória em alerta de gravidade alta | doc 01, §6.5 | Caixa "Li e conferi" antes de copiar |
| Evidência não confirmada | doc 01, §6.1 | Marcar a linha da ficha como "não confirmado" |
| Voto do relator vencido | Portaria 322/2026, art. 6º, III | Aviso na ficha quando só o voto vencido foi enviado |

## Diferenças de detalhe

- **Ordem do cabeçalho.** O protótipo põe o termo genérico e depois o específico de
  cada ponto, na ordem das escolhas. O backend ordena todos pela hierarquia do
  tesauro (`IndiceTesauro.ordenar_amplo_especifico`).
- **Dispositivo da Consulta.** O protótipo usa "Consulta conhecida e respondida";
  na tabela do backend a Consulta ainda está `A_DEFINIR` (pendência P1).
- **Fontes.** O protótipo usa Geist e Literata pelo Google Fonts. O documento 03
  cita Bricolage Grotesque, Instrument Sans e Source Serif 4. Na rede do Tribunal
  as fontes precisam ser servidas localmente.
