# Protótipo de interface

`index.html` é o protótipo navegável do fluxo (arquivo único, sem dependências além
das fontes). Usa dados simulados de uma Consulta e não chama modelo nem API.

Abra direto no navegador. "Usar o voto de exemplo" percorre o fluxo inteiro.

Os identificadores do caso real usado como base (relator, município e número do
processo) foram trocados por fictícios nesta cópia, conforme o `CLAUDE.md`.

É a referência visual e de fluxo para o frontend React + TypeScript da Fase 3.
A correspondência com o backend está em `docs/contrato-interface.md`.

## Versão online

Página privada em https://claude.ai/artifact/58CuCxJuv7zo79EuJzozHC (só o dono vê
até compartilhar). É gerada por `scripts/gerar_prototipo_online.py`, que troca o
logotipo oficial por uma marca neutra e usa o download da hospedagem no
"Exportar a conversa". Atualizações: editar `index.html`, gerar e republicar no
mesmo endereço.

Não enviar voto real não publicado para a versão online: ela fica fora da rede do
Tribunal (documento 01, seção 8).
