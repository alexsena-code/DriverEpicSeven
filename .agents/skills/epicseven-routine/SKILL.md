---
name: epicseven-routine
description: Calibrar capacidades e criar ou alterar pipelines MaaFramework do Epic Seven quando uma sequência recorrente justificar uma rotina.
---

# Desenvolver uma capacidade

Comece com primitivas quando estiver explorando uma tela ou resolvendo uma ação isolada. Só crie uma rotina quando houver uma sequência recorrente com estados e conclusão observáveis. O motor da sequência é o pipeline JSON do Maa; Python conecta janela, observação e evidência.

Leia [arquitetura: primitivas e pipelines](../../../docs/architecture.md#primitivas-e-pipelines) para os contratos e [docs/assets.md](../../../docs/assets.md) ao usar texturas/layouts do pacote. Uma coordenada CSB é local; um asset pode ser atlas ou 9-slice. Os templates atuais vêm de recortes do render real.

Para uma sequência nova, registre estado inicial, alvo, destino, bloqueios e limite de execução. Experimente primitivas dentro do pedido autorizado e guarde antes/depois. Acrescente templates com proveniência e capturas negativas; use `ScreenTarget` ou os reconhecedores Maa conforme a necessidade.

No pipeline, comece com um nó sem entrada de interface, reconheça em `next` e limite ações com `max_hit`. O timeout da espera de um próximo nó fica no nó anterior. Registre a rotina como `draft` até validar o percurso real; a conclusão exige o nó de sucesso e a tela final.

Durante ajustes, execute testes focados com `python -m pytest <arquivos/casos afetados>` e `driver-epic-seven validate`; inclua positivos, negativos e consumidores de leitores compartilhados. Valide o fluxo autorizado e reserve a suíte completa (`python -m pytest` sem seleção) para o fechamento da versão consolidada, sem falhas conhecidas. Não repita a suíte completa como diagnóstico nem junto da calibração ao vivo; novas execuções exigem mudança relevante, falha ou risco de regressão identificado, conforme AGENTS.md. Edições somente em documentação não exigem pytest. Um teste em fixture verifica reconhecimento, não aceitação de clique pelo jogo. Não habilite o início de batalhas, saltos de história ou próxima fase apenas com base no nome de um asset.

Use `ui_tree` como estrutura padrão e as projeções/consultas do contrato em [architecture.md](../../../docs/architecture.md#arvore-observada). Matches/OCR/relatórios antigos são fontes e compatibilidade; não crie um modelo paralelo nem copie o contrato para outra documentação. Atualize os Markdown canônicos; evidências de sessão ficam em `var/`.
