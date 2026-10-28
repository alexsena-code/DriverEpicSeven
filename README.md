# DriverEpicSeven

Habilitar um agente a dirigir o Epic Seven pela janela do Windows, usando **primitivas independentes** e **rotinas MaaFramework**. Ações isoladas não precisam virar rotina. O agente pode observar uma tela, escolher um alvo e verificar o resultado; uma sequência estável pode depois ser promovida a pipeline JSON.

Acompanhamento: [DriverEpicSeven no Linear — P-ALE-8](https://linear.app/akxl/project/driverepicseven-a9432259a160). Regras e contratos permanecem nos documentos canônicos deste repositório.

Há um único perfil do Epic Seven em `config/epic-seven.json` e um único pacote em `resources/epic-seven/`. A descoberta aceita o executável aberto, `EpicSeven.exe` ou `EpicSeven_Steam.exe`; comandos, leitores e rotinas são os mesmos. Usa captura `FramePool` e entrada `PostMessage`, ambas testadas com a janela coberta e sem foco em um percurso curto. A referência visual é uma área cliente de **1212 × 682**. Não há Computer Use, integração com a memória do jogo ou API interna de combate.

## Preparar

Windows e Python 3.11 ou 3.12:

```powershell
cd C:\Users\alexa\Documents\DriverEpicSeven
powershell -NoProfile -ExecutionPolicy Bypass -File tools/bootstrap.ps1
.\.venv\Scripts\Activate.ps1
driver-epic-seven validate
driver-epic-seven doctor
```

O ambiente é local em `.venv/`. Também é possível usar `.venv\Scripts\python.exe -m driver_epic_seven` em todos os exemplos, sem ativação. A instalação é editável e o repositório continua contendo os recursos e configurações; este projeto ainda não é uma distribuição autônoma em wheel.

Para os comandos de fase, instale também o OCR inglês oficial em revisão fixada. Os modelos ficam locais, fora do Git:

```powershell
python tools/install_ocr.py
```

O bootstrap aceita `-WithOcr` para incluir essa instalação. Tamanhos, hashes e origem ficam em `assets/ocr-provenance.json`.

`doctor` só descobre a janela e verifica a configuração. O driver não inicia, autentica ou fecha o jogo. Para ajustes pessoais, copie `config/local.example.json` para `config/local.json` e use `--config config/local.json` antes do comando. O override local só é aplicado quando indicado explicitamente ou pela variável `DRIVER_EPIC_SEVEN_CONFIG`.

Ao conectar, o driver ajusta a área interna da janela para **1212 × 682** e bloqueia o redimensionamento pela borda e a maximização durante a conexão. Ao desconectar normalmente, restaura esses controles e mantém o tamanho definido. Esse é o único tamanho calibrado atualmente; perfis futuros poderão oferecer outros tamanhos fixos. Uma janela minimizada precisa ser restaurada antes de conectar.

## Primitivas

Antes de uma operação nova ou teste no jogo, consulte as fontes extraídas por assunto ou família:

```powershell
python tools/query_sources.py "trocar personagem"
python tools/query_sources.py --family enhancement
python tools/query_sources.py --source wnd/formation.csb --find btn_remove
```

A consulta é offline e somente leitura. Usa o mapa de assuntos e as 33 famílias existentes para apontar aos CSB/DBs/textos, com status de interpretação e lacunas. Não conecta ao jogo nem recria o índice. Veja [busca por asset, texto e arquivos derivados](docs/assets.md#consulta-por-operacao).

A base de missões acrescenta `read-screen`, `quest read/list/inspect/open/tab/group/go/claim/claim-group/compare` e `swipe`. Veja os [contratos, exemplos e validação](docs/mission-operations.md#primitivas-de-missao). O leitor liga títulos e contadores visíveis ao catálogo; Go distingue modo/categoria de uma batalha identificada. Mouse 4 é o padrão; 64 é um fallback explícito e pode deslocar o cursor. Resgate pronto pode coletar várias missões do grupo; nenhuma escolha é automática.

Todas as observações retornam `ui_tree`, no [contrato padrão da árvore observada](docs/architecture.md#arvore-observada). Para consultar “Go da missão X no grupo Y” em uma leitura salva, use `quest query --observation <arquivo> --group <group_id> --task <task_id> --control go`. A consulta é somente leitura e preserva valores desconhecidos; a ação continua dependendo de observação atual e guardas.

Durante a conexão, o observador compartilha a última árvore em `var/runs/<execução>/observer.json`, com idade, invalidação e até 64 eventos de mudança/conclusão. `driver-epic-seven snapshot --file <caminho/observer.json> --after-sequence 0 --max-age-ms 500` consulta esse arquivo e confere a janela sem capturar nem abrir outra conexão; recalcula a validade no momento da consulta. Dentro do mesmo Runtime, `read_snapshot()` pode reutilizar uma leitura recente ou atualizar se não houver pipeline ativo. A imagem continua disponível para dúvida, tela desconhecida ou conferência visual. O observador acompanha as capturas que já acontecem; não mantém uma captura contínua quando o driver está ocioso.

### Fluxo principal do agente

Mantenha uma conexão aberta para observar, consultar e agir na mesma sessão:

```powershell
driver-epic-seven agent
```

O processo recebe uma linha JSON por pedido e devolve uma linha JSON por resposta. `args` contém os mesmos argumentos das primitivas e rotinas; não é um comando de shell. Exemplos, enviados na entrada do processo aberto:

```jsonl
{"id":"observar","args":["observe"]}
{"id":"consultar","args":["snapshot","--max-age-ms","500"]}
{"id":"abrir","args":["click","--target","orbis_button","--from-state","lobby","--expect","orbis_guide"]}
{"id":"missoes","args":["quest","read"]}
{"id":"voltar","args":["key","escape","--from-state","orbis_guide","--expect","lobby"]}
{"id":"encerrar","args":["disconnect"]}
```

Esses pedidos são exemplos individuais: envie ações conforme o objetivo e a resposta anterior. A conexão sozinha não captura nem inicia rotinas. Cada resposta traz a projeção textual `ui`, estado, validade, eventos novos e métricas. A árvore completa, com proveniência por campo, fica no arquivo indicado por `evidence.response_file`. `enabled: null` continua desconhecido. A projeção não habilita cliques nem escolhe missões automaticamente.

Consulte `snapshot` para reutilizar uma leitura recente; dentro de `agent`, ele não recebe `--file` e **nunca captura**, mesmo se a leitura venceu. Nesse caso, peça `observe`, `quest read`, `session inspect` ou `stage inspect <id>` conforme o contexto necessário. A leitura simples não mantém dados de missões de uma captura anterior. Toda ação continua passando pelo reconhecimento atual e pelas guardas do driver.

No percurso reconhecido, `image.required` é falso e nenhuma imagem é enviada ao modelo. Em desconhecido, erro ou resultado que exige revisão, a resposta indica a imagem disponível; `inspect_image: true` solicita conferência visual explicitamente. A ferramenta que opera a sessão abre a imagem somente quando isso for necessário. Uma imagem antiga continua antiga: confira `validity` e `image.requires_fresh_observation`. Fechar a entrada ou enviar `disconnect` libera a conexão e invalida o observador. Não há loop extra de captura nem atualização contínua.

Os atalhos abaixo foram conferidos nas opções do jogo e validados na configuração atual da demo, com a janela sem foco. As primitivas de tecla usam um acionamento Maa de **100 ms**; os destinos continuam sendo reconhecidos antes de declarar sucesso.

`read-screen` também publica em `ui.operation_view` os painéis operacionais calibrados: Otherworld, Abyss, Arena e prévias de itens/habilidades. Os controles de integrante selecionado e Auto aparecem nos nós da mesma árvore. Campos sem prova permanecem desconhecidos; `state=unknown` pode coexistir com um painel parcial identificado. Nessa leitura conhecida a imagem pode ser dispensada no envio ao modelo, preservando capturas internas, validade e guardas. Escopo e fontes em [architecture.md](docs/architecture.md#operacoes-e-auto).

A mesma árvore também lê as composições observadas de lobby/menu, configurações, avisos e resultados, Recruit/Connections, Moonlight's Blessing, heróis/equipamentos, inventário/correio, Marco Brilhante, apresentações e Summon, além de nível e despertar. Path of Heir e Diary usam os nós canônicos de grupo/missão e `ui.quest_view`, com IDs vinculados somente a títulos atuais inequívocos. As extensões são de leitura; não acrescentam executores nem ampliam os alvos de entrada. [Cobertura, evidências e lacunas](docs/validation.md#consolidacao-stove-ui).

Esses leitores reconhecem a estrutura da tela e extraem seu conteúdo atual. Nome e descrição do herói são dados, sem dependência de Tieria ou de uma lista de nomes. Uma observação já fornecida pode ser adaptada à árvore sem conectar ao jogo. Ler a tela Connections, suas missões ou o botão de conclusão também não realiza recrutamento ou qualquer ação.

Na navegação mapeada, um fundo animado pode mudar sem invalidar o alvo: a primitiva reobserva painel, controle e regiões estáveis pela mesma árvore e captura. Essa prova vale para navegação explicitamente não consumidora; outras ações mantêm suas guardas anteriores. Uma resposta sem destino confirmado pede nova leitura, sem repetição de entrada. [Contrato e limites](docs/architecture.md#navegação-com-fundos-animados).

Inclui os popups de equipamento/artefato, prévia e confirmação de Equip All, confirmações de habilidade, resultado rápido de Arena e os objetivos textuais da preparação de aventura. A árvore distingue requisito de estrela de conquista: ler três objetivos não preenche `earned_stars` nem comprova 3★. Objetivos sem interpretação, instâncias, seleção e habilitação sem prova continuam desconhecidos. São extensões de leitura; não habilitam executores genéricos dessas famílias.

```jsonl
{"id":"ler-painel","args":["read-screen"]}
{"id":"garantir-auto","args":["battle-auto","on"]}
```

`battle-auto on` só atua em batalha já iniciada e com HUD positivamente desligado; se estiver ligado, não clica, e se estiver desconhecido, recusa. O grafo de conclusão também tem essa guarda, com um clique máximo por batalha. Consulta offline de um controle em uma observação salva:

```powershell
driver-epic-seven ui-query --observation <leitura.json> --view abyss_floors --control select_team
```

| Tecla | Destino observado desde o lobby |
|---|---|
| Tab | Menu rápido; Tab também confirmou o fechamento |
| G | Orbis Guide |
| C | Tela de heróis |
| O | Opções |
| 1 | Mapa do episódio atual |
| 3 | Categorias de batalha, sem iniciar uma batalha |
| Esc | Retorno dos menus validados ao lobby |

`hotkeys` distingue os defaults extraídos do DB das entradas em `live_validations`. O escopo é a configuração e os percursos observados, não todo contexto do jogo ou cancelamento de qualquer diálogo. Se Orbis abrir na aba Diary, `quest read` preserva o grupo desconhecido; escolha a aba observada com `quest tab heir --observation <arquivo>` e releia antes de consultar missões de Path of Heir. Consulte [evidências e limites do fluxo](docs/validation.md).

Captura, reconhecimento e contexto recente dos logs:

```powershell
driver-epic-seven observe
```

A saída JSON contém `state`, os alvos encontrados, a imagem salva e `observation_file`. Capturas e registros ficam em `var/runs/`, fora do Git.

Navegação por alvo reconhecido, sem criar uma rotina:

```powershell
driver-epic-seven click --target orbis_button --from-state lobby --expect orbis_guide
driver-epic-seven key escape --from-state orbis_guide --expect lobby
driver-epic-seven wait-state lobby --timeout 6
```

Se o lobby ocioso estiver reconhecido, `click --target wake_lobby --expect lobby` restaura os controles. Esse ponto fixo é uma exceção calibrada para essa tela.

Exploração por coordenada: use o caminho de `observation_file` retornado por uma captura recente. O comando verifica janela, idade, semelhança da tela e região do clique antes da entrada:

```powershell
$seen = driver-epic-seven observe | ConvertFrom-Json
driver-epic-seven click --point 600 550 --observation $seen.observation_file --from-state lobby_idle --expect lobby
```

Uma tela nova pode aparecer como `unknown` e ainda ser inspecionada. A coordenada deve ser escolhida na imagem; esse modo aceita uma observação explícita recente, inclusive durante calibração de telas ainda sem nome. Não é necessário criar um pipeline para essa exploração. `--expect` é opcional: sem ele, o resultado confirma o envio e salva a tela seguinte, mas não declara a ação semanticamente concluída. `key escape --observation <arquivo>` usa o mesmo vínculo com uma observação.

Para calibração explícita de Escape longo, `key escape --duration-ms 5000 --observation <arquivo>` admite até 5 s, conservando as guardas de imagem/janela. As demais teclas e todos os atalhos normais mantêm 100 ms. O teste de 5 s para cutscene não chegou a ser enviado; o usuário também relatou que Escape curto abre Skip na story, ainda sem promoção automática ao grafo.

`skill-double-tap 2 --observation <arquivo> --from-state battle_running` envia um gesto de dois toques na segunda habilidade manual observada. É experimental, limitado aos três centros de habilidade em 1212 × 682; exige conferir a tela/cooldown e verificar o efeito depois. Não inicia batalha nem liga Auto. Consulte [o contrato do gesto](docs/architecture.md#toque-duplo-de-habilidade-observado).

## Rotinas

```powershell
driver-epic-seven list
driver-epic-seven run orbis_roundtrip
```

`orbis_roundtrip` é um pipeline Maa: reconhece lobby ou lobby ocioso, restaura o HUD se necessário, localiza Orbis Guide, abre, reconhece o guia, envia Escape e confirma o lobby. Não coleta recompensas.

| Capacidade | Estado inicial |
|---|---|
| Observar, clicar em alvo/ponto observado, Escape, esperar tela | Implementada |
| Abrir Orbis e voltar | Validada em percurso curto |
| Restaurar HUD do lobby ocioso | Calibrada e incluída no percurso |
| Selecionar e preparar fase por ID, com OCR e uma rolagem limitada | Pipeline validado ao vivo em `pen002`, episódio 2/capítulo 5 |
| Iniciar fase por pipeline parametrizado | Validado ao vivo em fases do episódio 2/capítulo 5, com identidade e orçamento |
| Concluir batalha, histórias, confirmações e avisos | Pipeline `finish-battle`, com vários Skips, cancelamento de amizade, banners e Tap to close |
| Encadear as próximas fases | Comando `chapter`: um grafo Maa, um início por fase e orçamento total do trecho |

## Selecionar uma fase com confiança

O catálogo contém as 12 fases do episódio 2/capítulo 5: `pen001` a `pen006` e `pes001` a `pes006`. A seleção começa no mapa desse capítulo ou na preparação da fase pedida; o caminho desde a taberna ainda depende de navegação observada.

```powershell
driver-epic-seven stage list
driver-epic-seven stage inspect pen002
driver-epic-seven stage prepare pen002
```

`prepare` seleciona a linha, confirma a descrição, abre a preparação e verifica local, título e custo. Ele para antes de iniciar. No teste real, confirmou **Silver Fox Territory / Permeating Darkness**, com custo de **8** e energia disponível **912**.

O comando abaixo inicia no máximo uma vez, com limite explícito de energia. Execute somente quando esse início fizer parte do objetivo autorizado:

```powershell
driver-epic-seven stage start pen002 --max-energy 8
```

O driver recusa fase bloqueada, identidade divergente, custo diferente do catálogo, saldo insuficiente e fase concluída sem `--allow-replay`. Esse parâmetro só deve ser usado quando repetir a fase for o objetivo. O fluxo não escolhe heróis nem otimiza a equipe. Veja o [contrato e a evidência da seleção](docs/campaign.md#selecao-de-fase).

## Concluir e avançar automaticamente

```powershell
driver-epic-seven finish-battle --timeout 300
driver-epic-seven chapter --from-stage pes004 --max-energy 28 --timeout 600
```

`finish-battle` acompanha somente a batalha já iniciada até voltar ao mapa. `chapter` compila as fases restantes do capítulo em um único pipeline Maa: prepara, inicia, pula histórias, confirma resultados, fecha avisos e avança. No exemplo, os únicos novos inícios são as fases 10, 11 e 12, com custo total máximo de 28.

Se houver um resultado ou aviso da fase anterior pendente, use `chapter --from-stage pes005 --max-energy 20 --finish-current`: o fluxo encerra esse resultado e depois inicia somente 11 e 12. Falha interrompe o trecho; antes de retomar, observe a tela e escolha a próxima fase pendente. Veja [o fluxo, os limites e os avisos genéricos](docs/campaign.md#fluxo-de-batalha).

Para interromper uma rotina entre operações, crie `var/STOP`. A operação já enviada pode terminar; esse mecanismo não desfaz cliques. Remova o arquivo quando quiser retomar comandos de entrada. Observação continua disponível.

## Organização

```text
AGENTS.md                    orientação canônica para o agente
.agents/skills/              workflows reutilizáveis descobertos pelo Codex
config/                      configuração única e ajustes locais opcionais
src/driver_epic_seven/       janela, Maa, primitivas, evidências e CLI
resources/epic-seven/
  pipeline/                  rotinas nativas Maa em JSON
  image/                     templates pequenos já calibrados
  vision.json                estados, alvos e fidelidade visual
routines/registry.json       entradas, conclusão, status e pendências
data/catalogs/               catálogo de missões e índice de fontes por operação
data/stages/                 identidade e custo das fases disponíveis ao seletor
data/layouts/                layouts CSB já interpretados
assets/                      proveniência; extrações extensas em local/ ignorado
tests/                       invariantes e reconhecimento offline
tools/                       preparação, importação e consulta offline
docs/                        arquitetura, descobertas e evolução
var/                         execuções locais, ignoradas pelo Git
```

A organização usa a [referência enviada](https://x.com/lincolixavier/status/2037588026394587330) como inspiração conceitual, adaptada para Codex, `AGENTS.md`, primitivas e pipelines Maa. Não replica a estrutura de outra ferramenta. Instruções do projeto ficam em `AGENTS.md`, procedimentos reutilizáveis em `.agents/skills/`, exemplos de comandos e regras detalhadas em `docs/`. Não há configuração global do Codex alterada nem subagentes iniciados automaticamente. Consulte a [documentação oficial de AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

## Caminho por nível — preparação em andamento

O roteiro estático e o plano de uma leitura salva não conectam ao jogo:

```powershell
driver-epic-seven path roadmap --level 1
driver-epic-seven path plan --observation var/runs/<execucao>/observation.json --level 1
```

Na conexão `agent`, `path inspect` lê as missões atuais; `path open` abre o Caminho a partir dos estados calibrados. `path go <task_id>` navega pelas receitas disponíveis. `path prepare tar008` apenas confere a preparação; `path campaign --from-stage tar007 --to-stage tar008 --max-energy 16 --timeout 600` é um exemplo de trecho, **não um pedido para repetir fases já jogadas**. `path finish-stage tar008 --timeout 300` conclui uma reserva pendente com zero novos inícios. O diário persistente impede repetir Start em outro pedido.

O catálogo dos 65 grupos não equivale a 65 executores prontos. A unidade prevista é um grupo, seguida de revisão do agente para recompensas, Marco Brilhante e melhorias. Os grupos 1 e 2 foram concluídos; o segundo abriu o grupo 3 em 0/5, com intervenções para tutorial, formação, retorno e melhoria. O ciclo ininterrupto por nível e a instalação portátil ainda estão pendentes. Consulte [escopo do roteiro](docs/mission-operations.md#roteiro-por-nivel) e [fechamento do grupo 2](docs/validation.md#grupo2-fechamento).

`path altar cmon001 --max-energy 9` executa uma entrada calibrada; `--finish-current` continua uma entrada registrada com zero Start. `path collect --level 1 --allow-ready-group` coleta missões prontas; `path collect-group --level 1 --allow-ready-group` coleta a recompensa final. Ambos exigem alvos atuais e recusam um envio já registrado ou incerto. `path inspect` organiza a revisão com o leitor existente; não é um executor automático dos 65 grupos.

O perfil padrão usa mouse 4. A validação STOVE atual também passou a usar 4, depois de o usuário observar o cursor sendo movido pelo modo 64. O modo 64 permanece uma escolha explícita de fallback, sem troca automática.

O compilador `path run-group --level 2 --plan <plano.json> --timeout 1200` está em calibração. O plano informa `max_energy`, `max_gold`, `max_actions` e escolhas por missão em `tasks`. Ele compõe as unidades suportadas em um único grafo Maa, confere o grupo atual e interrompe para revisão após a prova do próximo grupo. Sua existência não comprova um ciclo completo validado. Entradas ou aplicações já registradas não são repetidas.

As novas unidades limitadas ao grupo 2 são `path abyss --max-energy 10` (ou `--prepare` / `--finish-current`) e `path equipment <task_id> --hero-name <nome>` (`--preview` prepara sem aplicar; `--apply-preview` exige a prova atual conservada na mesma conexão). A melhoria requer `--max-gold`. Consulte o estado da calibração em [validação](docs/validation.md); não execute esses exemplos como repetição de ações desta conta. `path recover <task_id>` usa navegação mapeada com zero Start/Receive; telas sem retorno comprovado continuam bloqueadas.

## Validar e evoluir

Durante os ajustes, selecione os testes da operação e dos leitores compartilhados afetados. Por exemplo:

```powershell
python -m pytest tests/test_path_executors.py tests/test_stove_story.py
driver-epic-seven validate
```

Depois de estabilizar os testes focados e o fluxo autorizado, rode a suíte completa sobre a versão consolidada:

```powershell
python -m pytest
driver-epic-seven validate
```

Não use a suíte completa a cada ajuste nem junto da calibração ao vivo. Uma nova execução completa exige mudança relevante, falha ou risco de regressão identificado; corrija primeiro no conjunto focado. Edições somente em documentação não exigem pytest. A regra canônica está em [AGENTS.md](AGENTS.md) e o procedimento em [architecture.md](docs/architecture.md#preparacao-antes-da-calibracao).

Os testes com capturas da conta usam arquivos locais ignorados. Nesta máquina eles foram importados da sessão anterior. Em outro checkout podem ser importados com `python tools/import_session.py --session <pasta-da-sessao>`; sem eles, o teste correspondente informa `skipped`.

Leia [primitivas e rotinas](docs/architecture.md#primitivas-e-pipelines), [seleção de fase](docs/campaign.md#selecao-de-fase), [fluxo de combate e avanço](docs/campaign.md#fluxo-de-batalha), [arquitetura](docs/architecture.md), [assets](docs/assets.md) e [evidências e limites](docs/validation.md#descobertas-iniciais). O escopo validado é o perfil e os percursos observados; novas telas, derrota e outros tipos de interrupção ainda exigem calibração.

O [mapa inicial de operações de missão](docs/mission-operations.md) cobre 877 registros, 58 condições e 33 famílias propostas. A [especificação por condição](data/missions/operation-map.json) contém parâmetros, exemplos e evidências exigidas; é um desenho não executável, sem novos pipelines habilitados.
