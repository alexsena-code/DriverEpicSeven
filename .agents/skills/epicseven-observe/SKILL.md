---
name: epicseven-observe
description: Observar e diagnosticar a janela Epic Seven com o driver local, incluindo reconhecimento, evidências e contexto dos logs.
---

# Observar Epic Seven

Na raiz deste repositório, use `.venv/Scripts/python.exe -m driver_epic_seven doctor` para identificar a janela. Para o fluxo normal, abra `agent` e mantenha o processo para enviar pedidos JSONL; consulte [README.md](../../../README.md#fluxo-principal-do-agente). Use `observe` ao precisar de uma leitura nova. `doctor` apenas consulta; a conexão aplica o perfil fixo da janela descrito em architecture.md.

Leia primeiro estado, `ui`, validade e eventos. A evidência visual continua alimentando o reconhecimento internamente; abra a imagem quando `image.required` indicar desconhecido/falha, houver dúvida ou for necessária conferência/calibração. Confira a idade antes de interpretar essa imagem como atual. `scene=lobby` não descarta uma sobreposição; `fresh=false` impede tratar o último botão como evento desta ação. Confira área cliente de 1212 × 682 e perfil/idioma antes de interpretar uma falha como mudança no jogo.

Uma tela `unknown` pode ser explorada por primitivas quando a tarefa autoriza interação. Escolha o ponto na imagem e forneça `--observation` recente; não invente um alvo. Nem toda ação precisa virar rotina. Para comandos e condições, consulte [README.md](../../../README.md) e [arquitetura: primitivas e pipelines](../../../docs/architecture.md#primitivas-e-pipelines).

Ao relatar, diferencie estado reconhecido, envio de entrada e transição confirmada. Preserve a evidência em `var/runs/`; capturas completas e progresso da conta não entram no Git.

Use `ui_tree` como estrutura padrão e as projeções/consultas do contrato em [architecture.md](../../../docs/architecture.md#arvore-observada). Matches/OCR/relatórios antigos são fontes e compatibilidade; não crie um modelo paralelo nem copie o contrato para outra documentação. Atualize os Markdown canônicos; evidências de sessão ficam em `var/`.

Para consultas repetidas na sessão `agent`, envie `snapshot` sem `--file`: nunca captura nem atualiza uma leitura vencida. Peça observação nova quando necessário; para detalhes de missão, use `quest read`, pois `observe` não conserva missão de uma leitura anterior. Durante pipeline ativo, outro processo pode ler `snapshot --file <observer.json>` sem conectar. A projeção referencia a árvore completa com proveniência; snapshot não autoriza entrada nem comprova captura contínua. Encerre a conexão com `disconnect` ou EOF.
