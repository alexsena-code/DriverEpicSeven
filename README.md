# DriverEpicSeven

Habilitar um agente a dirigir o Epic Seven pela janela do Windows, usando **primitivas independentes** e **rotinas MaaFramework**. Ações isoladas não precisam virar rotina. O agente pode observar uma tela, escolher um alvo e verificar o resultado; uma sequência estável pode depois ser promovida a pipeline JSON.

Acompanhamento: [DriverEpicSeven no Linear — P-ALE-8](https://linear.app/akxl/project/driverepicseven-a9432259a160). Regras e contratos permanecem nos documentos canônicos deste repositório.

Há um único perfil do Epic Seven em `config/epic-seven.json` e um único pacote em `resources/epic-seven/`. A descoberta aceita o executável aberto, `EpicSeven.exe` ou `EpicSeven_Steam.exe`; comandos, leitores e rotinas são os mesmos. Usa captura `FramePool` e entrada `PostMessage`, ambas testadas com a janela coberta e sem foco em um percurso curto. A referência visual é uma área cliente de **1212 × 682**. Não há Computer Use, integração com a memória do jogo ou API interna de combate.

## Como navegar neste projeto

- [Instalar e fazer a primeira leitura](#preparar)
- [Guia de trabalho do agente](#guia-de-trabalho-do-agente)
- [Testes de desenvolvimento](#testes-de-desenvolvimento)
- [Primitivas e protocolo de sessão](#primitivas)
- [Rotinas, planos e retomada](#rotinas)
- [Validar e evoluir](#validar-e-evoluir)

## Guia de trabalho do agente

### Entrada e responsabilidades

Abra a pasta clonada como workspace do agente. Leia [AGENTS.md](AGENTS.md)
antes de executar comandos; esse arquivo contém as regras operacionais.
As skills locais de [observação](.agents/skills/epicseven-observe/SKILL.md)
e [rotinas](.agents/skills/epicseven-routine/SKILL.md) orientam os respectivos
fluxos. Um agente que não descubra skills automaticamente pode ler esses
arquivos diretamente. A configuração `.codex/` é opcional para outros agentes;
não é uma dependência do driver Python.

O agente escolhe objetivo, operação, parâmetros e limites. O driver descobre
a janela, captura, reconhece, verifica guardas e registra evidências. Pipelines
Maa executam ações e transições delimitadas. Não implemente um segundo motor
de automação em scripts nem use Computer Use para dirigir o jogo.

| Local | Responsabilidade |
|---|---|
| `src/driver_epic_seven/` | Runtime, aplicação, CLI/JSONL, leitores e guardas |
| `resources/epic-seven/` | Pipelines Maa, configuração visual e templates |
| `config/` e `routines/registry.json` | Perfil único, overrides e catálogo de rotinas |
| `data/` | Catálogos estáticos, requisitos e mapa de operações |
| `tools/` | Instalação, consulta e extração offline |
| `tests/` | Testes de contratos, leitores, grafos e fixtures |
| `docs/` | Contratos técnicos, fontes, capacidades e validação |
| `var/` | Capturas, diários, planos e relatórios privados; ignorado pelo Git |

### Ciclo de operação

1. Instale conforme [Preparar](#preparar). Consulte `capabilities` e o registry
   para distinguir operação executável, calibrada e apenas mapeada. Combine
   com o usuário o trecho e os limites de recursos antes de agir.
2. Após abrir ou reiniciar o jogo, use `doctor` para redescobrir a janela.
   Abra `driver-epic-seven agent` e mantenha esse processo para enviar pedidos
   JSONL pela entrada padrão e ler as respostas pela saída padrão.
3. Envie `observe` para uma leitura nova. Leia `ui`, estado, validade e eventos;
   a árvore completa `ui_tree` fica na evidência indicada pela resposta.
   Consulte `snapshot` para reutilizar a leitura, conferindo idade/invalidação.
   Se venceu, solicite a leitura apropriada: snapshot na sessão nunca captura.
4. Escolha uma primitiva existente para um passo ou uma rotina existente para
   a sequência autorizada. Confira estado e alvo atuais. `enabled: null`
   significa desconhecido. Catálogo estático não comprova acesso nem progresso.
5. Confira destino e prova de conclusão na resposta. Entrada aceita não prova
   resultado. Em erro ou incerteza, releia e preserve a evidência antes de decidir
   a continuação; não reenvie Start, compra, melhoria ou resgate por tentativa.
6. Encerre com `disconnect`. Após intervenção manual, invalide as suposições
   anteriores e faça nova observação. Preserve o diário da própria conta.

Os [exemplos JSONL](#fluxo-principal-do-agente) mostram o formato dos pedidos.
Operações longas podem usar `async: true`, `status`, `events` e `cancel`, conforme
[planos e retomada](#planos-e-consulta-durante-execução--wave-3). O agente deve
consumir cada resposta e decidir o próximo passo; copiar uma sequência inteira
de exemplos não constitui um plano autorizado.

### Diagnóstico e ajustes

| Sintoma | Próximo passo |
|---|---|
| Janela não encontrada | Abra o cliente nativo, restaure a janela e confira `doctor`; não reutilize PID/HWND antigo. |
| Tela desconhecida ou alvo ausente | Leia a evidência atual, confira idioma/composição e abra a captura quando `image.required` indicar. Não invente um clique. |
| Snapshot vencido | Envie `observe`, `quest read`, `read-screen` ou a inspeção específica necessária; confira a nova validade. |
| Entrada aceita, destino ausente | Observe novamente, confira origem/alvo e o histórico. Mouse 64 só como fallback explícito no escopo autorizado. |
| OCR ausente | Rode `python tools/install_ocr.py` e `validate`; os modelos não acompanham o clone. |
| Operação bloqueada por diário/resultado incerto | Leia identidade, checkpoint e provas. Use apenas a continuação implementada (`--finish-current` quando suportado); não apague o diário para liberar repetição. |
| Fontes privadas ou fixture ausentes | Registre a lacuna; consulte o mapa de fontes. Um skip local não é validação positiva. |

Antes de mudar gesto, ponto ou reconhecedor, consulte o índice offline:

```powershell
python tools/query_sources.py "trocar personagem"
python tools/query_sources.py --family enhancement
```

Siga a ordem requisito → entidade → controle/variante → prova de conclusão.
As fontes extraídas privadas podem não estar disponíveis num clone novo;
o índice público preserva referências e lacunas. Detalhes de consulta e
proveniência estão em [assets](docs/assets.md#consulta-por-operacao).
Coordenadas de CSB e nomes internos são pistas de calibração, não seletores
de tela nem coordenadas globais.

Reutilize a `ui_tree` canônica: reconhecedores Maa alimentam adaptadores,
e os consumidores usam a árvore/projeções comuns. Para conteúdo dinâmico,
reconheça a composição e extraia o valor atual, sem exigir o nome de um herói
da demo. Calibre uma operação com capturas positivas e negativas, mantenha
proveniência de templates e valide destino observável. Não aumente limiares
globais para aceitar uma tela nova ou um fundo animado.

Durante a implementação, rode os testes focados pertinentes e
`driver-epic-seven validate`. Faça ida/volta e repetição curta somente quando
o teste ao vivo estiver autorizado. Após estabilizar o conjunto, execute a
suíte completa sem concorrer com jogo/testes pesados. Registre comando,
versão, duração, resultados e skips em `var/`; atualize os documentos canônicos
existentes. [Procedimento completo](docs/architecture.md#preparacao-antes-da-calibracao).

### Pedido inicial sugerido para outro agente

> Leia AGENTS.md e o guia do agente no README. Confira instalação e capacidades
> sem realizar ações no jogo. Depois redescubra a janela e faça uma observação
> para identificar a tela atual. Use o driver local e o protocolo agent/JSONL,
> preserve os diários desta conta e me apresente o trecho e os limites necessários
> antes de iniciar progressão. Se precisar ajustar um leitor ou rotina, consulte
> primeiro as fontes da operação, preserve as guardas e valide com evidências.

## Preparar

Requer Windows 10/11 de 64 bits, Git e Python 3.11 ou 3.12 de 64 bits.
Abra o cliente nativo do Epic Seven (Steam ou STOVE), entre na sua conta e use
o jogo em **inglês**, em janela e sem minimizar. Emuladores e outros idiomas
não fazem parte do perfil calibrado.

No PowerShell, clone e instale com o OCR incluído:

```powershell
git clone https://github.com/alexsena-code/DriverEpicSeven.git
cd DriverEpicSeven
powershell -NoProfile -ExecutionPolicy Bypass -File tools/bootstrap.ps1 -Python py -WithOcr
.\.venv\Scripts\python.exe -m driver_epic_seven validate
.\.venv\Scripts\python.exe -m driver_epic_seven doctor
```

Se `py` selecionar uma versão diferente, forneça o caminho do `python.exe`
3.11/3.12 em `-Python`. O bootstrap verifica a versão antes de instalar.
Para usar os comandos curtos dos exemplos, ative o ambiente com
`.\.venv\Scripts\Activate.ps1`; a forma com `python.exe` acima funciona sem ativação.

Com `doctor` concluído, a primeira leitura é:

```powershell
.\.venv\Scripts\python.exe -m driver_epic_seven observe
```

Essa leitura conecta e calibra o tamanho da janela, captura a tela e grava
evidências em `var/`; não inicia combate. Estado `unknown` pede inspeção da
captura antes de agir. Depois, use o [fluxo do agente](#fluxo-principal-do-agente)
ou consulte `driver-epic-seven --help` e `driver-epic-seven capabilities`.

Cada instalação começa com seus próprios diários em `var/current-account/`.
Não copie essa pasta de outra conta. As autorizações e os relatos históricos
da demo nos documentos não autorizam gastos na conta de quem clonar:
defina com seu agente as fases, os limites de recursos e as repetições permitidas.
O projeto fornece comandos e protocolo JSONL; requer um agente ou operador
para escolher os pedidos, e não oferece uma interface gráfica de uso final.

Para atualizar, encerre a conexão do driver, execute `git pull --ff-only` e
rode novamente o bootstrap com `-WithOcr`. Configurações pessoais ficam em
`config/local.json`, fora do Git. Para interromper uma execução, crie o arquivo
`var/STOP` (por exemplo, `New-Item var/STOP -ItemType File -Force`);
remova-o conscientemente antes de iniciar outra operação.

O ambiente é local em `.venv/`. Também é possível usar `.venv\Scripts\python.exe -m driver_epic_seven` em todos os exemplos, sem ativação. A instalação é editável e o repositório continua contendo os recursos e configurações; este projeto ainda não é uma distribuição autônoma em wheel.

Para os comandos de fase, instale também o OCR inglês oficial em revisão fixada. Os modelos ficam locais, fora do Git:

```powershell
python tools/install_ocr.py
```

O bootstrap aceita `-WithOcr` para incluir essa instalação. Tamanhos, hashes e origem ficam em `assets/ocr-provenance.json`.

`doctor` só descobre a janela e verifica a configuração. O driver não inicia, autentica ou fecha o jogo. Para ajustes pessoais, copie `config/local.example.json` para `config/local.json` e use `--config config/local.json` antes do comando. O override local só é aplicado quando indicado explicitamente ou pela variável `DRIVER_EPIC_SEVEN_CONFIG`.

Ao conectar, o driver ajusta a área interna da janela para **1212 × 682** e bloqueia o redimensionamento pela borda e a maximização durante a conexão. Ao desconectar normalmente, restaura esses controles e mantém o tamanho definido. Esse é o único tamanho calibrado atualmente; perfis futuros poderão oferecer outros tamanhos fixos. Uma janela minimizada precisa ser restaurada antes de conectar.

## Testes de desenvolvimento

```powershell
python -m pytest --test-tier=fast
python -m pytest tests/test_stage_selection.py --test-tier=native
python -m pytest --durations=20 --junitxml=var/tests/fechamento/pytest.xml
```

O último comando cobre a suíte completa; reserve-o para o fechamento estabilizado.
`fixtures` identifica dados privados, e não a ausência de Maa/OCR: a seleção rápida
audita também dependências de fixtures. `--fixture-cache=off` força reconhecimento
independente das capturas; o cache padrão existe somente no processo dos testes,
sem compartilhar Resource/Tasker mutáveis e sem uso no driver ao vivo.
`--test-profile=var/tests/amostra/profile.json` e `--test-audit=var/tests/amostra/audit.json`
registram custo e seleção. [Procedimento e limites](docs/architecture.md#estrategia-de-testes).

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

CLI e JSONL adaptam os pedidos para a mesma `Application`, no processo local.
`driver-epic-seven capabilities` consulta o registry e o mapa existentes sem
conectar: rotinas validadas e famílias apenas mapeadas continuam distintas.
Os comandos anteriores permanecem disponíveis. A resposta de execução acrescenta
`execution.identity`, `status` e provas; envio aceito não significa conclusão.
O JSONL aceita opcionalmente `identity` com `objective_id`, `plan_id`,
`operation_id` e `attempt_id`, todos strings não vazias. Sem esse campo, gera
identidades novas. Reutilizar uma identidade não autoriza repetir uma reserva.
Erros da aplicação acrescentam `execution_error`, preservando a correlação do pedido.

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

### Planos e consulta durante execução — Wave 3

O protocolo JSONL versão 2 aceita `async: true` para executar um pedido longo
em um único worker e devolver a confirmação de submissão. Pedidos sem esse
campo mantêm a resposta síncrona. Na mesma conexão, `status`, `events`,
`snapshot`, `capabilities` e `cancel` continuam disponíveis enquanto o Maa
executa. Outro pedido de entrada é recusado. Consultas usam a árvore existente,
com idade e invalidação; não iniciam outra captura/OCR.

```jsonl
{"id":"trecho","async":true,"identity":{"objective_id":"objetivo-autorizado","plan_id":"trecho-1","operation_id":"campanha","attempt_id":"tentativa-1"},"args":["path","campaign","--from-stage","ijp002","--to-stage","ijp003","--max-energy","16"]}
{"id":"andamento","args":["status"]}
{"id":"eventos","args":["events","--after-sequence","0"]}
{"id":"parar","args":["cancel"]}
{"id":"encerrar","args":["disconnect"]}
```

São exemplos de protocolo para uso autorizado após a manutenção. A confirmação
de submissão não comprova entrada nem conclusão. O status conserva a identidade
do pedido original, resultado/erro, progresso comprovado, unidades pendentes,
limites e prazo. `ui.controls` distingue visibilidade, região ativa calibrada,
habilitação desconhecida e impedimentos; a consulta nunca autoriza uma ação.
Cancelar sinaliza a parada ao worker: os envios e reservas anteriores permanecem
no diário, com incerteza quando houve entrada. Não há rollback ou replay liberado.
`disconnect`/EOF aguardam o worker antes de liberar o Runtime.

`chapter`, `path campaign` e `path run-group` usam contratos finitos comuns.
Checkpoints ficam junto ao diário em `plans/`, vinculados ao objetivo/plano e
ao conteúdo original. A retomada usa a mesma identidade de objetivo/plano e
preserva prazo/contagens; omite unidades concluídas e compila continuações sem
Start para entradas pendentes. Falta de prova ou capacidade devolve revisão
ao agente. Equipamento incerto conserva a reconciliação explícita
`--finish-current`. Um grupo exige crédito, recibos, recompensa final e próximo
checkpoint; vitória isolada não conclui missão.

No CLI independente, `--execution-identity '<JSON com os quatro IDs>'` fornece
a identidade persistente antes do comando. O default é uma tentativa por unidade.
Uma eventual nova tentativa exige `--plan-budget` explícito desde o pedido inicial
(`max_attempts`, `max_starts`, `max_total_energy`, `max_actions`) e, após derrota
comprovada, a política `--retry-policy` já existente. Nenhum desses campos inicia
retry automático; uma retomada conserva os tetos originais.

Fora da conexão, `status --file <execution.json>` consulta somente o registro
de lifecycle; `events --file <observer.json>` consulta o histórico salvo. Esses
dois comandos não descobrem janela. O plano em andamento é consultado por
`status` no JSONL e pelo checkpoint; o arquivo de lifecycle não promete
atualização contínua. Eventos mantêm sequência/cursor e indicam histórico perdido.

Em 29/10/2026, o aceite da Wave 3 é **offline**, pois o jogo está em manutenção.
Não executar `agent`, `doctor`, captura ou controle da janela para esta validação.
As provas usam fixtures privadas e controlador Maa em memória. A validação de
um grupo legítimo ao vivo fica adiada e não bloqueia o fechamento offline;
simulações e capturas históricas não comprovam progresso atual da conta.
Veja [contratos](docs/architecture.md#wave3-planos) e
[evidências e limites](docs/validation.md#wave3-offline).

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

A Wave 2 permite preparar uma unidade parametrizada de
Abyss normal: `path abyss --floor 32 --mode normal --expected-energy 10 --prepare`.
Com `--next-floor --prepare`, o andar informado é o destino da navegação
a partir do resultado atual. A preparação comum exige o andar selecionado/disponível ou sua preparação atual; não seleciona
andares por catálogo nem inicia combate. `path altar cmon002 --prepare` também
aceita a preparação já aberta. CP ilegível não substitui nem elimina as guardas
de composição, integrantes, identidade e custo. Quick Battle tem estado próprio
de leitura, sem executor. [Contrato e limites](docs/architecture.md#nucleo-local),
[evidências da primeira migração](docs/validation.md#wave2-batalhas).

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

Os aliases de compatibilidade incluem `path abyss --max-energy 10` (ou `--prepare` / `--finish-current`) e `path equipment <task_id> --hero-name <nome>` (`--preview` prepara sem aplicar; `--apply-preview` exige a prova atual conservada na mesma conexão). A melhoria requer `--max-gold` e `--material-limits`. Consulte o estado da calibração em [validação](docs/validation.md); não execute esses exemplos como repetição de ações desta conta. `path recover <task_id>` usa navegação mapeada com zero Start/Receive; telas sem retorno comprovado continuam bloqueadas.

Operações independentes de missão aceitam um escopo persistente explícito:

```powershell
driver-epic-seven path altar cmon002 --scope objetivo-altar-normal --prepare
driver-epic-seven path abyss --scope objetivo-andar32 --floor 32 --prepare
driver-epic-seven path equipment --operation enhance_weapon --scope melhoria-planejada --hero-name "Nome observado" --preview --auto-level 6 --max-gold 50000 --material-limits '{"Equipment Enhancement Powder":2,"Lesser Equipment Charm":3}'
driver-epic-seven path formation select --scope leitura-formacao --source right
```

`path formation reposition` exige origem, destino e `--member-name` comprovado;
`assign`/`substitute` exigem candidato visível e destino. `remove` está delimitado
à prova de vazio na esquerda. Uma mutação registrada não é reenviada; `--finish-current` comprova o destino
sem nova mutação quando o contexto original está no diário. Os quatro
nomes de posição são rótulos visuais, sem ID interno presumido. A leitura aparece
em `ui.formation_view`, derivada da mesma árvore.

`--retry-policy` é um objeto JSON passado antes do comando, com
`previous_attempt_id`, `max_attempts`, `max_total_cost` e
`deadline_epoch_seconds`. Para derrota, o pedido mantém `objective_id`/`plan_id`
e usa nova `attempt_id` com prova vinculada. Para campanha com resultado
desconhecido, `kind=uncertain` e `stage_id` identificam a exceção autorizada:
mantém-se o objetivo, usa-se novo plano e tentativa, preserva-se a entrada
anterior e exigem-se evidência de reconciliação, janela atual e orçamento.
O diário admite até três entradas por fase; não há retry automático.

Após derrota comprovada, uma política explícita `kind=defeat_new_plan` pode
vincular um novo trecho finito à tentativa e ao plano anteriores. O histórico
e o teto de três entradas da fase não são reiniciados. Consulte o contrato de
[planos e retomada](docs/architecture.md#wave3-planos).

## Validar e evoluir

Durante os ajustes, selecione os testes da operação e dos leitores compartilhados afetados. Por exemplo:

```powershell
python -m pytest tests/test_path_executors.py tests/test_stove_story.py
driver-epic-seven validate
```

Depois de estabilizar os testes focados e o fluxo autorizado, rode a suíte completa no fechamento da wave ou de uma entrega independente, sobre a versão consolidada:

```powershell
python -m pytest --durations=20 --durations-min=0.1 --junitxml=var/tests/fechamento-01/pytest.xml
driver-epic-seven validate
```

Não rode a suíte completa automaticamente a cada chat, subissue ou ajuste. Antes de entregar/integrar, confira se o resultado cobre a versão funcional atual; uma nova execução exige mudança relevante, falha ou risco de regressão novo e motivo registrado. Corrija primeiro no conjunto focado. Escolha um novo diretório de relatório por tentativa e registre revisão, alterações funcionais, resultados/skips e ambiente em `var/`. Não sobreponha suíte/profiling pesado a outra sessão editando/testando o conjunto ou à calibração ao vivo. Edições somente em documentação não exigem pytest. A regra canônica está em [AGENTS.md](AGENTS.md); seleção, checkpoints e investigação do custo estão em [architecture.md](docs/architecture.md#estrategia-de-testes).

Os testes com capturas da conta usam arquivos locais ignorados. Nesta máquina eles foram importados da sessão anterior. Em outro checkout podem ser importados com `python tools/import_session.py --session <pasta-da-sessao>`; sem eles, o teste correspondente informa `skipped`.

Leia [primitivas e rotinas](docs/architecture.md#primitivas-e-pipelines), [seleção de fase](docs/campaign.md#selecao-de-fase), [fluxo de combate e avanço](docs/campaign.md#fluxo-de-batalha), [arquitetura](docs/architecture.md), [assets](docs/assets.md) e [evidências e limites](docs/validation.md#descobertas-iniciais). O escopo validado é o perfil e os percursos observados; novas telas, derrota e outros tipos de interrupção ainda exigem calibração.

O [mapa inicial de operações de missão](docs/mission-operations.md) cobre 877 registros, 58 condições e 33 famílias propostas. A [especificação por condição](data/missions/operation-map.json) contém parâmetros, exemplos e evidências exigidas; é um desenho não executável, sem novos pipelines habilitados.

## Proveniência e arquivos locais

Os recortes de templates e os dados derivados do jogo conservam sua origem em
`assets/template-provenance.json` e [docs/assets.md](docs/assets.md).
São assets de terceiros, sem atribuição de autoria ao projeto. O OCR oficial
é instalado separadamente, com revisão e hashes em `assets/ocr-provenance.json`.
Este repositório não declara uma licença geral de redistribuição para assets
do jogo. Pacotes originais, chaves, modelos baixados, capturas completas,
fixtures privadas, configurações pessoais e progresso da conta não acompanham
o clone. Links para `var/` nos relatos são referências históricas locais.

A verificação automática no GitHub instala o projeto no Windows com Python
3.11 e 3.12, valida os recursos e executa a seleção rápida auditada. Não controla
o jogo e não substitui testes nativos nem calibração ao vivo. Testes que dependem
das evidências privadas podem informar `skipped` em um clone novo.


### Repetir a fase escolhida pelo Try again (experimental)

Abra `repetir_fase.bat` na raiz. Escolha a fase e a equipe **no jogo**, termine
uma batalha manualmente e deixe o rodapé com **Leave**, **Lobby** e **Try again**
visível antes de continuar no terminal. O lançador pergunta a quantidade de
**novas batalhas**, o teto total do recurso exibido no botão e o prazo total
(até 30 minutos). Por exemplo, 10 repetições com custo 8 exigem teto de pelo
menos 80. A primeira batalha manual não entra nessa contagem.

Também disponível em `.venv/Scripts/python.exe -m driver_epic_seven repeat-stage --count 10 --max-resource 80 --timeout 1800` (em uma única linha).

O grafo Maa usa um envio por repetição e comprova entrada em combate antes de
aceitar outro resultado. Mantém o mouse 4 do perfil, ativa Auto apenas quando
comprovadamente desligado e reaproveita os tratamentos de história/avisos já
existentes. Não recarrega recurso; custo divergente, saldo insuficiente,
derrota ou tela sem tratamento impedem a próxima repetição e encerram por
prazo finito. Pare com **Ctrl+C** ou criando `var/STOP`; o arquivo não é apagado
pelo lançador. O rodapé não comprova vitória nem identidade da fase: a escolha
permanece vinculada ao botão atual, sem nomes ou progresso inventados.

Cada novo início fica registrado antes da entrada. Um lote interrompido com
início pendente bloqueia outro lote até conferir/reconciliar sua evidência;
não há retomada automática. Evidências ficam em `var/runs/`.

**Validação:** testes offline; percurso ao vivo pendente. Nesta sessão a conexão
recebeu `WinError 5: Access is denied`, antes de capturar ou enviar entrada.
Não há prova de que o clique desta nova rotina foi aceito pelo jogo.


### Moonlight Theater por `.bat`

Abra **`moonlight_theater.bat`** na raiz. O Windows solicitará permissão de
administrador quando necessária. Deixe Moonlight Theater aberto no ato que
quer assistir, com **Watch** disponível; informe quantos atos, o limite de
ingressos e o prazo total. O lançador aceita 1–20 atos, até 100 ingressos e até
30 minutos. Este escopo usa **um ingresso por ato**; Watch gratuito não está
habilitado pelo fluxo de confirmação calibrado.

A rotina toca Watch, confirma o ingresso específico, avança diálogos com
pausa configurada de 100 ms, suspende os toques diante de combate e avança o
CLEAR até o próximo ato selecionado pelo jogo. Não coleta recompensas nem
compra ingressos. Auto só recebe um clique se o HUD comprovar desligado, e o
próximo passo exige comprovar ligado. Ausência ou ambiguidade nunca alterna o
botão. Na calibração do Theater, a luta avançou sem esse clique; a ativação
nessa variante permanece pendente.

Pare com **Ctrl+C** ou criando `var/STOP`. O lançador não apaga STOP. Uma
confirmação incerta bloqueia outro Watch. Havendo um único ato pendente, o
lançador tenta **somente sua conclusão, sem Watch, Confirm ou novo ingresso**.
Essa continuação exige a mesma identidade de janela registrada; após reiniciar
o jogo ou trocar de conta, o contexto deve ser conferido antes de reconciliar
o diário. Não há descarte automático de entradas pendentes.

CLI: `.venv/Scripts/python.exe -m driver_epic_seven theater --acts 2 --max-tickets 2 --timeout 1800`.
Continuação sem novo gasto: `theater --acts 1 --max-tickets 0 --timeout 600 --finish-current`.
Também é aceito na conexão `agent`. Capturas, plano, resultado e diário ficam
em `var/`; o lançador imprime a pasta de evidência ao terminar.

**Estado experimental:** Watch/confirmar e a conclusão com continuação foram
exercitados no ato 6 de Fallen Land, Season 1, com saldo 32 → 31 e ato 7
selecionado. Durante a calibração houve pausas para incluir variantes visuais;
o lote novo sem interrupção, vários atos em uma tarefa, fim de temporada e
ativação do Auto nessa modalidade ainda precisam de prova própria. Telas sem
tratamento, limite de toques ou prazo encerram a tarefa para revisão.


Atualização do reconhecimento do Theater (02/11): além das composições rápidas,
a rotina reconhece a forma dos controles com OCR localizado de fala/narração,
e a abertura com `Act N` e aviso de toque. A cor do fundo deixa de ser o único
caminho para reconhecer essas cenas. O `.bat` não mudou; feche uma execução
antiga e abra novamente para carregar a atualização. Isso não habilita toque
contínuo em telas sem reconhecimento nem altera gastos ou o toggle de Auto.


O `.bat` do Theater agora mostra acompanhamento no próprio terminal. Mudanças
de etapa aparecem assim que forem lidas; um resumo é repetido a cada 5 segundos,
com tempo decorrido, ato alvo, atos confirmados, tentativas de avanço e idade
da última leitura disponível. Combate informa Auto ligado/desligado/desconhecido;
ausência de leitura recente ou de reconhecimento também fica visível. A
confirmação de ingresso é descrita como solicitação, sem antecipar gasto ou
sucesso do clique. O total final vem do resultado verificado da tarefa.

O texto é salvo em `progresso.log`, na pasta exclusiva de cada abertura do
lançador: `var/runs/terminal_<id>/`. As evidências do driver ficam em uma
subpasta dessa pasta. O perfil efetivo é preservado, alterando somente o destino
das evidências para isolar o acompanhamento de execuções anteriores. O leitor
consulta apenas a árvore/eventos existentes: não captura, não executa OCR e
não envia comandos ao jogo. Reabra o `.bat` para carregar essa atualização.
