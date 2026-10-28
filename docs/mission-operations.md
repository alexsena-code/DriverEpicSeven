# Mapa inicial das operações de missão

**Escopo do catálogo: desenho e levantamento.** Os executores propostos para as 33 famílias não foram habilitados. Validações pontuais por primitivas, autorizadas separadamente, estão registradas abaixo; elas não promovem uma família inteira a execução automática.

O catálogo contém **877 missões**, **58 condições distintas** e foi agrupado em **33 famílias de operação**. Inclui Path of Heir, A Journey of Succession, Journey Through World Arena e Connections. Cinco quizzes não trazem condição preenchida e permanecem para investigação. Isso cobre os tipos do catálogo, sem afirmar que todas as missões estejam disponíveis ou pendentes nesta conta.

A especificação completa por condição, parâmetros, exemplos e task_ids está em [operation-map.json](../data/missions/operation-map.json). Os nomes de capacidades são propostos, não uma API executável.

O cruzamento com layouts, imagens e DBs está em [apoio estático às famílias](assets.md#apoio-as-familias) e [static-family-evidence.json](../data/missions/static-family-evidence.json). Essa análise também identifica 17 condições adicionais nas subquestões de mudança de especialidade, fora do escopo das 58 condições acima; não habilita execução nem acrescenta validação ao vivo.

## Estrutura comum

A implementação inicial desta base está em [primitivas de missão](mission-operations.md#primitivas-de-missao): leitor, navegação pontual, resgate e comparação, calibrados inicialmente no Path of Heir. As famílias abaixo continuam propostas e não executadas automaticamente por esse leitor.

Missão observada → requisito normalizado → escolha de capacidade → conferência de alvo/custo → unidade de ação → resultado → contador da missão → resgate individual → resgate de grupo.

O agente escolhe parâmetros e resolve pré-requisitos. O Maa conduz sequências de interface conhecidas. Primitivas atendem ações pontuais. O verificador distingue ação enviada, progresso, condição satisfeita e recompensa resgatada.

Cada plano precisa de task_id/group_id, parâmetros originais, alvo concreto (herói/item/pet), contador inicial, orçamento por recurso, máximo de execuções e máximo de falhas. A quantidade pedida pela missão é independente desses limites.

O leitor também precisa registrar grupo ativo, condição satisfeita, recompensa disponível e recompensa resgatada. Nos layouts analisados, Go e Receive podem ocupar a mesma posição; o rótulo e o estado atual precisam distingui-los. Receber a recompensa individual e receber a do grupo são operações separadas, quando previstas no plano.

## Famílias e execução proposta

| Tipo | Forma inicial | Fluxo proposto | Conferência |
|---|---|---|---|
| Campanha e capítulos (`campaign`, 41 registros) | rotina Maa + leitura | Ler destino e progresso → selecionar episódio/capítulo/fase → preparar e conferir custo → iniciar uma vez → tratar histórias e resultado → reler missão | Vitória/capítulo exigido e condição da missão confirmados; resgate separado. |
| Hunt, Altar, Catalyst, Labyrinth, Abyss e outros modos (`combat_modes`, 390 registros) | rotina Maa por modo | Resolver destinos permitidos → abrir modo e dificuldade → conferir fase/equipe/custo → iniciar → concluir combate → voltar ao painel desse modo → conferir missão | Contador correto, dificuldade elegível e vitória; Abyss exige o andar alcançado. |
| Vitórias consecutivas (`consecutive`, 9 registros) | rotina Maa + diário persistente | Ler sequência exigida → validar Repeat/Quick Battling elegível → registrar vitórias e falhas por execução → parar no alvo → reler missão | Sequência aceita pela missão; resultados isolados não comprovam uma série. |
| Vitória com equipe/elemento exigido (`team_battle`, 2 registros) | planejador + rotina de combate | Resolver boss/fases → conferir heróis e quantidade por elemento → salvar equipe → vencer destino elegível → conferir missão | Composição exigida e contador; observar se apoiador/substituição interfere. |
| Obter materiais em um modo específico (`drop_farm`, 2 registros) | rotina Maa + inventário | Ler material e origens → registrar saldo/contador → escolher estágio permitido → vencer → conferir drops → atualizar saldo e missão | Material de origem elegível e incremento; não prometer quantidade por vitória. |
| World Boss (`world_boss`, 1 registros) | rotina específica | Conferir acesso e janela do modo → montar equipe exigida pela tela → iniciar → processar resultado → conferir missão | Conclusão reconhecida no modo e contador da missão. |
| Rift: nível e pontos (`rift`, 6 registros) | planejador + leitura + combate | Ler temporada/nível/pontos → escolher etapa disponível → executar dentro do orçamento → reler progresso do Rift e missão | Nível ou pontos efetivamente atingidos na temporada correta. |
| Hall of Trials: nota, modo e condições na batalha (`trials`, 9 registros) | planejador + rotina específica | Ler modo e requisito → conferir bônus/equipe → executar batalha → ler nota/pontos/condições → conferir missão | Score/modo exigidos ou contador da condição dentro de uma mesma batalha. |
| Arena NPC, normal e modalidades aceitas (`arena`, 156 registros) | rotina Maa por modalidade | Ler pvptype aceito → confirmar acesso → selecionar NPC ou adversário elegível → conferir custo/equipe → iniciar uma vez → ler resultado → conferir missão | Tipo de Arena correto e contador. Participação e vitória são requisitos diferentes. |
| Mock Arena (`mock_arena`, 15 registros) | rotina/planejador próprios | Conferir acesso ao treino → selecionar enter exato → ler regras e escolhas → vencer → conferir missão | Vitória no cenário mock solicitado; não substitui uma batalha RTA. |
| Quiz do caminho da Arena (`quiz`, 5 registros) | investigação + primitivas | Abrir missão do quiz → ler pergunta e opções → obter resposta fundamentada → responder → confirmar resultado e missão | Quiz aceito/concluído na interface. |
| Herói: nível, despertar e promoção (`hero_growth`, 62 registros) | leitura + primitivas; rotina se recorrente | Resolver herói/quantidade → ler estado atual → escolher operação e materiais → conferir custo → aplicar uma alteração → verificar estado e missão | Nível/despertar/estrelas e quantidade de heróis; Penguin deve ser usado quando explicitamente exigido. |
| Melhorar habilidades (`hero_skills`, 13 registros) | primitivas parametrizadas | Selecionar herói e habilidade → ler nível/custo/material → aplicar melhoria autorizada → conferir habilidade e contador | Alteração aplicada e número de melhorias aceito pela missão. |
| Amizade de herói (`friendship`, 1 registros) | leitura + plano de progressão | Ler amizade e alvo → selecionar meio de progresso elegível → executar com limite → verificar amizade e missão | Herói e nível de amizade atingidos; fechar o banner não é progredir por si só. |
| Specialty Change (`specialty`, 1 registros) | planejador de pré-requisitos | Escolher herói elegível → ler requisitos da troca → planejar subtarefas → completar requisitos → confirmar troca → conferir missão | Troca concluída e personagem resultante confirmado. |
| Recrutar por Connections (`connections`, 3 registros) | planejador que compõe operações | Abrir conexão do chrid correto → ler requisitos e progresso → planejar subtarefas → conferir todos os requisitos → recrutar → verificar origem e missão | Herói recrutado pela origem content exigida; uma cópia de outra origem pode não cumprir. |
| Configurar apoiadores (`supporters`, 1 registros) | primitivas de configuração | Abrir Supporters → registrar configuração anterior → escolher heróis ou autoatribuição explicitamente prevista → salvar → conferir configuração e missão | Configuração salva e incremento da missão. |
| Melhorar equipamento ou artefato (`enhancement`, 46 registros) | primitivas; rotina curta quando repetitiva | Resolver tipo/item → ler nível atual → escolher materiais e prévia → conferir custo → melhorar → conferir nível/contador | Distinguir vezes que melhorou, nível final +N e quantidade de itens que atingiram +N. |
| Equipar itens ou ativar conjunto (`equipping`, 6 registros) | primitivas + verificador de composição | Resolver herói/slots/conjunto → ler equipamentos atuais → escolher itens → conferir troca/custo → equipar → verificar slots e conjunto ativo | Herói correto, quantidade de peças, nível mínimo e efeito de conjunto ativo conforme a missão. |
| Fabricar equipamento (`crafting`, 7 registros) | rotina de fabricação delimitada | Abrir Blacksmith → escolher categoria/tabela elegível → ler custo e quantidade → fabricar → identificar resultado → conferir missão | Quantidade de fabricações e origem/equipid elegíveis; qualidade não é garantida pelo processo. |
| Converter equipamento e fabricar exclusivos (`conversion`, 6 registros) | primitivas ou rotina específica por variante | Resolver variante → abrir sistema correto → selecionar tipo e materiais → conferir prévia/custo → converter → conferir resultado e missão | Conversão do tipo solicitado; Exclusive Equipment tem fluxo próprio. |
| Reforjar equipamento (`reforging`, 13 registros) | primitivas de transformação | Selecionar instância elegível → ler estado e materiais → conferir transformação → reforjar → verificar novo estado e missão | Reforja concluída do item elegível e contador. |
| Vender ou extrair equipamento/artefato (`disposal`, 7 registros) | primitivas com seleção explícita | Listar instâncias escolhidas → excluir equipados/bloqueados/reservados → conferir seleção e resultado esperado → vender ou extrair → verificar inventário e missão | Quantidade/tipo corretos e mudança no inventário; venda e extração não são intercambiáveis. |
| Forest of Souls: Penguin e Spirit Bloom (`production`, 2 registros) | primitivas; rotina curta se recorrente | Abrir Sanctuary/Forest of Souls → selecionar produto → ler quantidade/custo → produzir imediatamente quando exigido → verificar saldo/inventário → conferir missão | Produto materialid e origem content corretos; produção imediata quando a missão a pede. |
| Trocas e lojas (`shops`, 13 registros) | primitivas de transação | Resolver loja e produto → ler preço/saldo/limite → conferir quantidade → efetuar troca prevista → verificar saldo/produto e missão | Loja/categoria exigida e incremento; comprar o mesmo produto em outra loja pode não cumprir. |
| Gastar moeda específica / purificar Heart of Orbis (`spending`, 5 registros) | planejador que escolhe operação consumidora | Ler tokentype e total exigido → resolver operação elegível → ler saldo e orçamento → executar uma unidade → verificar gasto efetivo e contador | Quantidade da moeda efetivamente consumida; não basta contar cliques. |
| Pets: invocar, brincar, sintetizar e liberar (`pets`, 11 registros) | primitivas por ação; rotina se recorrente | Resolver ação/pet → ler atributos e recursos → escolher instâncias/material/herança quando aplicável → confirmar → verificar pet/inventário e missão | Evento de invocação/brincadeira, grau final ou quantidade liberada, conforme condition. |
| Invocar heróis (`summoning`, 4 registros) | primitivas com banner e orçamento definidos | Ler gachaid aceito → abrir banner → conferir contador gratuito/custo → executar invocação prevista → processar resultado → conferir missão | Invocação no tipo de banner exigido; obter herói específico é outro requisito. |
| Guild: presença, ajuda e pedido de ajuda (`guild`, 5 registros) | primitivas por ação social | Conferir guild e ação → ler pedido/recurso/limite → realizar a ação prevista → conferir registro e contador | Presença, doação ou pedido são eventos separados. |
| Login e reputação diária (`time_gates`, 31 registros) | leitura + plano com dependência temporal | Ler evento e período → verificar login/diárias → concluir subtarefas quando necessário → coletar recompensa diária elegível → conferir contador | Evento/período e recompensa diária completa reconhecidos; reconectar não comprova novo dia. |
| Moonlight Theater (`theater`, 1 registros) | rotina de história parametrizada | Selecionar storyid/ato → conferir acesso/custo → executar história → finalizar → conferir registro e missão | Ato/episódio marcado como concluído e contador. |
| Adquirir ou concluir Side Story arquivada (`side_story_records`, 2 registros) | planejador por estado buy/clear | Resolver storyid e estado pedido → conferir aquisição/progresso → adquirir ou concluir subtarefas do registro → conferir estado e missão | buy exige aquisição; clear exige registro completo. Um estado não substitui o outro. |
| Entregar recursos em Connections (`connection_gift`, 1 registros) | primitiva de entrega | Abrir requisito give correto → ler recurso e quantidade real → conferir saldo → entregar → conferir requisito e missão | Entrega completa do requisito; count=1 pode representar uma entrega de 30 unidades. |

## O que cada contador significa

- **Quantidade de ações:** melhorar cinco vezes pode exigir cinco eventos, mesmo que um clique aumente vários níveis.
- **Estado final:** possuir dois heróis nível 60 ou três peças +15 pede verificar inventário/equipamento antes de gastar.
- **Maior andar:** Abyss 40 não significa repetir quarenta vezes o primeiro andar.
- **Sequência:** dez vitórias consecutivas precisam de controle da série e da falha, além da quantidade total de batalhas.
- **Condição dentro de uma batalha:** exaustão e bônus de Trials não devem ser somados entre partidas diferentes.
- **Origem:** Connections, drops, fabricação e lojas precisam preservar a origem exigida, além do produto.
- **Tempo:** login e diárias dependem do evento/reset; reconectar repetidamente não comprova progresso.
- **Gasto:** count pode ser unidades da moeda. Em destiny_give, count=1 pode representar uma entrega de 30 Brave Crests.
- **Resgate:** condição satisfeita, recompensa individual e recompensa do grupo são três estados distintos.

## Arena e limites da demo

A [página oficial da demo Steam](https://store.steampowered.com/app/5129800/), consultada em 26/10/2026, exclui Guild War e World Arena. O catálogo marca 25 tarefas RTA como excluídas. Uma missão que aceita NPC pode usar essa modalidade após confirmar o acesso; uma missão exclusiva de RTA não pode ser substituída por NPC. Mock Arena e quizzes ficam para checagem própria. A exclusão de Guild War não demonstra que presença, ajuda, loja da Guild ou World Boss estejam indisponíveis.

## Reaproveitamento e lacunas

**Já existe no projeto:** captura/entrada Win32 via Maa, observação e OCR, primitivas com guarda, seleção/início da campanha, diário de entradas, Skip, clique mantido, Rank Up, avisos, resultado e parada por derrota. O escopo de validação ao vivo continua sendo o registrado em docs/validation.md e docs/campaign.md.

**Falta para as novas famílias:** calibrar acesso e navegação, controles de alvo/custo, preparação e resultado de cada modo, leitura dos contadores dos caminhos e resgate individual/de grupo. As telas compartilhadas podem ser reaproveitadas depois de confirmar a transição daquele modo.

Apoiadores, equipamentos e crescimento podem começar como primitivas. Batalhas e produções recorrentes justificam rotinas. Connections, Specialty Change, Rift e Trials precisam também de um planejador de requisitos, não apenas um ciclo de cliques.

## Sequência sugerida para uma futura calibração

1. **Leitor do Orbis Guide:** grupo ativo, texto, contador, Go/Receive e dependências; somente leitura inicialmente.
2. **Apoiadores e Forest of Souls:** configuração pontual e uma produção delimitada; verificar estado/inventário e missão.
3. **Arena NPC:** uma batalha elegível, custo e retorno à lista; conferir se o contador certo avança.
4. **Spirit Altar / Hunt:** um adaptador por modo, dificuldade e retorno; só depois habilitar lote.
5. **Crescimento e equipamento:** seleção explícita de herói/item e materiais, prévia e orçamento.
6. **Modos e condições compostas:** sequência, elementos, drops, Trials, Rift, Guild, Connections e arquivos de história.

Essa sequência é uma proposta. Não foram lidas as pendências atuais da conta, criados novos pipelines, agendadas ações ou executadas transações nesta etapa.

## Critério para promover uma capacidade

Mapeada → telas calibradas → ação unitária autorizada → resultado observado → contador confirmado → rotina registrada com escopo. Um fluxo desenhado ou um teste offline não recebe o status de validação ao vivo.

<a id="primitivas-de-missao"></a>

## Primitivas de missão

Implementação inicial em 26/10/2026. Primitivas do CLI, sem despachante automático de missões nem novas rotinas das cinco famílias prioritárias. A campanha anterior permanece pausada. O relatório HTML anterior foi preservado.

### Decisões com o usuário

- Validar navegação na conta aberta, sem iniciar batalhas ou gastar recursos.
- Permitir resgates prontos, interrompendo em seletores ou escolhas de herói/item.
- Após o teste revelar coleta conjunta, permitir **todas as missões prontas do grupo selecionado**. Não prometer resgate isolado de uma linha: um Receive coletou quatro missões no mesmo grupo.
- Mouse **PostMessage (4) como padrão**, sem deslocar o cursor; **PostMessageWithCursorPos (64) como fallback**. O segundo move o cursor brevemente e o restaura. Ambos usam MaaFramework.
- Fallback é uma decisão explícita do agente após nova observação, registrada pelo perfil e no resultado. Não há troca automática no controlador. Uma transição incerta de resgate/início não autoriza repetir a ação com outro método.

Os dois perfis são `config/mission-primitives.json` (4) e `config/mission-primitives-fallback.json` (64). A captura permanece FramePool (2) e o teclado PostMessage (4). O perfil histórico de campanha mantém 64; o perfil padrão do driver mantém 4. A validação desta base incluiu ambos e não é um benchmark de confiabilidade entre eles.

### Primitivas disponíveis

O leitor agora também produz a [árvore observada, contrato versão 1](architecture.md#arvore-observada), em `ui_tree`, preservando o relatório anterior. `quest query --observation <arquivo> --group <group_id> --task <task_id> --control go` resolve um controle por hierarquia em uma leitura salva, sem interagir com o jogo. As ações continuam exigindo as guardas atuais e conferem a árvore com o relatório recém-lido.

| Primitiva | Contrato |
|---|---|
| `observe` | Captura, estado, janela, métodos e contexto recente dos logs; nenhuma entrada |
| `read-screen [--roi X Y W H]` | OCR Maa com texto, confiança e caixa; nenhuma entrada |
| `quest list / inspect` | Consulta estática de tarefa, grupo, família, condição, parâmetros e recompensas; sem progresso da conta |
| `quest read` | Liga o grupo e títulos visíveis ao catálogo; lê contador e distingue incomplete, claim_ready, claimed e unknown |
| `quest open` | Um clique no Orbis reconhecido no lobby; exige confirmação do painel, sem resgate |
| `quest tab heir` | Um clique na aba lida por OCR e confirmação do caminho |
| `quest group <group_id>` | Um clique no grupo adjacente, com identificação do grupo de origem e destino |
| `quest go <task_id>` | Um clique no Go da missão visível, incompleta e identificada; confirma nível de navegação e destino informado, sem iniciar batalha |
| `quest claim <task_id> --allow-ready-group` | Um Receive de missão pronta; pode coletar todas as prontas do grupo. Não fecha banners ou escolhe itens automaticamente |
| `quest claim-group <group_id>` | Um Receive da recompensa final, separado das missões; exige grupo identificado, contador completo e controle presente. Caminho positivo ainda não exercitado ao vivo nesta implementação |
| `quest compare` | Compara duas leituras do mesmo grupo/missão/janela; distingue incremento do contador de confirmação de resgate |
| `click`, `hold`, `key`, `wait-state` | Primitivas existentes para alvos reconhecidos ou captura recente, mantendo suas guardas |
| `swipe` | Um arraste com início/fim/duração e observação recente; retorna nova observação sem percorrer a lista automaticamente |

As ações do painel estão inicialmente calibradas para **Path of Heir, inglês, cliente 1212 × 682**. Os demais caminhos permanecem no catálogo; consultas estáticas não tornam suas abas/ações calibradas. Texto quebrado, ambíguo ou de baixa confiança não é vinculado a uma tarefa por aproximação. Títulos de destino podem ser conferidos em até três linhas alinhadas, sem correspondência parcial.

### Categoria não é batalha

O campo `navigation.kind` diferencia:

1. `battle_categories`: menu de categorias, como Normal/Seasonal.
2. `mode_menu`: modo e opções de dificuldade. O exemplo calibrado é Remnant of Supremacy, com Normal/Hard/Hell.
3. `stage_list`: lista/mapa de fases.
4. `supporter_selection`: seleção de apoiador.
5. `battle_preparation`: preparação da batalha.
6. `combat` e `battle_result`: combate e resultado, sem inferir a identidade da fase somente pelo tipo da tela.

`quest_panel` identifica o guia e `unknown` preserva lacunas de reconhecimento. A classificação de navegação complementa o estado visual existente; não habilita novos alvos de combate.

Um Go confirmado retorna `verification_scope: navigation_only`. Um título de modo e uma dificuldade **não** tornam `battle_identity_verified` ou `cost_verified` verdadeiros. A identificação de batalha exige o seletor de fase existente (`stage inspect/prepare`), que liga local/história ao ID. Custo verificado também exige identidade e correspondência com o custo catalogado. Mesmo esses sinais não autorizam início: ele continua separado e limitado por orçamento.

No teste, a missão “Clear Otherworld Breach 1 time” abriu **Remnant of Supremacy**. A diferença de nomes foi observada; não se deve substituir esse título pelo nome da missão nem declarar uma batalha concluída ao alcançar o menu.

### Uso pelo agente

```powershell
driver-epic-seven quest list --path heir --group group_guide_16
driver-epic-seven quest inspect guide_16_004_001
driver-epic-seven quest open
$seen = driver-epic-seven quest read | ConvertFrom-Json
driver-epic-seven quest tab heir --observation $seen.observation_file
$seen = driver-epic-seven quest read | ConvertFrom-Json
```

Cada ação usa a leitura que imediatamente a precede. Exemplos de operações independentes, conforme o estado observado:

```powershell
driver-epic-seven quest group group_guide_15 --observation $seen.observation_file
driver-epic-seven quest go guide_16_004_001 --observation $seen.observation_file --expect-text "Remnant of Supremacy" --destination-kind mode_menu
driver-epic-seven quest claim guide_16_002_001 --observation $seen.observation_file --allow-ready-group
driver-epic-seven swipe --begin 700 560 --end 700 325 --duration-ms 450 --observation $seen.observation_file --from-state orbis_guide
```

Os exemplos não formam um roteiro para executar em sequência: grupo, tarefa e leitura precisam corresponder. A confirmação do Go pode usar `--expect <estado>` no lugar de `--expect-text`, mas `--destination-kind` continua obrigatório. Um destino que já aparece na origem é recusado como prova distintiva.

Se uma navegação com modo 4 não produzir efeito, observe novamente. Somente se ainda estiver no mesmo painel/alvo, uma tentativa explícita com o perfil de fallback poderá ser apropriada:

```powershell
driver-epic-seven --config config/mission-primitives-fallback.json quest read
```

Reavalie a identidade e a próxima ação com essa leitura; não repita o comando anterior cegamente. Capturas e resultados registram os métodos usados. O teste já mostrou entrada aceita pelo Maa sem a pós-condição visual no modo 4; isso não comprova falha universal desse método.

### Resgates e prova

`condition_satisfied`, `claim_ready`, `claimed` e `group_claimed` são sinais distintos. No teste, um Receive elevou o progresso do grupo de 0/5 para 4/5, exibiu um banner de várias recompensas e reorganizou as linhas. A confirmação de resgate individual exige reencontrar a tarefa com a marca de concluído. Uma linha ausente ou fora da tela não comprova resgate.

O leitor só libera ação em uma linha totalmente visível, com título exato e controle/counter compatíveis. O total do contador é confrontado com `parameters.count` quando numérico. Contador 5/5 de uma missão não libera o Receive cinza do grupo em 0/5. A marca visual de concluído é reconhecida via Maa com verificação de pixels; sua ausência não vira um palpite de estado.

Um clique enviado não é repetido enquanto se espera a resposta do servidor. A primitiva pode repetir **leituras** por até cinco segundos para conferir a transição, sem novos cliques. Se aparecer banner ou tela não resolvida, retorna `needs_review`; nenhuma seleção é feita. Avisos informativos conhecidos podem ser fechados separadamente pelas primitivas já existentes, após inspeção. Banners novos e escolhas exigem revisão.

Compare o antes e o depois, após fechar um aviso entendido e reler a missão:

```powershell
driver-epic-seven quest compare guide_16_002_001 --before <leitura-inicial.json> --after <leitura-final.json>
```

A comparação exige a mesma janela/processo, grupo e tarefa e ordem temporal válida. Isso não detecta troca de conta dentro do mesmo processo; intervenções dessa natureza invalidam a comparação operacional.

### Evidência e limites

| Evidência local em `var/runs/` | Resultado |
|---|---|
| `20261026T111533Z_6a9b3bc6` | Grupo 16, duas missões prontas; terceira linha cortada sem ação; grupo 0/5 sem liberação de resgate final |
| `20261026T111548Z_dc9c4ff1` | Um único Receive, mouse 4; banner posterior em `20261026T111607Z_170d3366` |
| `20261026T111842Z_7540b48e` | Progresso 4/5 e marcas de resgate; comparação confirmou `guide_16_002_001` |
| `20261026T111916Z_3275bdc1` | Grupo 16 → 15 confirmado; retorno ao 16 também observado |
| `20261026T112523Z_8b0f3485` | Menu de modo → categorias; ambos sem identidade de fase/custo; retorno ao lobby |
| `20261026T112614Z_6c76495d` | Aba Heir e rolagem com mouse 64; três tarefas resgatadas identificadas após a lista mudar |
| `20261026T112729Z_4b151d8b` | Go com `destination-kind=mode_menu` confirmado; fase/custo não identificados e nenhum início enviado |
| `20261026T113536Z_74d2af31` → `20261026T113609Z_bafab495` | Escape 4 voltou ao lobby, mas abrir Orbis com mouse 4 não confirmou efeito; origem foi relida, fallback 64 abriu Orbis/Heir, confirmou grupo 16 em 4/5 e terminou no lobby. Troca documentada em `input_fallback.json` |

O fechamento informativo e retorno também foram observados. A recompensa final do grupo 16 não foi resgatada: falta a missão de Otherworld Breach. Não houve combate, compra, escolha de recompensa ou consumo de material para completar missões neste trabalho. Quatro tarefas já satisfeitas foram resgatadas pelo comportamento conjunto do jogo.

Os testes unitários cobrem vínculo exato, contadores divergentes, baixa confiança, sobreposição, grupo incorreto, linha cortada, não repetição de missão marcada como resgatada, comparação e separação entre modo/fase/custo. O replay offline usa oito capturas locais, incluindo negativas. Capturas completas e leituras da conta ficam ignoradas pelo Git; o pequeno template tem proveniência em `assets/template-provenance.json`.

Verificação: **58 testes passaram** na suíte completa em 144,70 s; os 12 testes novos da base passaram, incluindo o replay local. `validate` confirmou 90 nós e zero erros. A suíte não envia entrada ao jogo. A navegação e o resgate acima são a evidência ao vivo, separada desses testes.

Permanece para as cinco famílias: identidade e orçamento de herói/item, operação específica de cada modo, retorno desde o destino correto e validação de incremento após realizar uma ação. A base não conclui essas missões automaticamente.

<a id="expansao-operacional"></a>

## Expansão operacional — 26/10/2026

Na consolidação STOVE de 27/10, as telas salvas de Path of Heir e Diary foram integradas aos nós canônicos de grupo, missão e controle. Path of Heir exige título de grupo único, cabeçalho, aba e rodapé atuais; cada missão exige título exato dentro desse grupo. A leitura mantém missões cortadas, contadores ausentes e inventário completo do grupo como desconhecidos. Receive sem contador não promove a condição a satisfeita. Diary conserva fragmentos observados sem atribuir IDs do catálogo por aproximação.

Connections, prévias/resultados de nível e despertar e recibos são painéis de leitura na mesma árvore. A confirmação de desbloqueio de uma Connection não comprova recrutamento; a apresentação de um herói não comprova instância possuída. As integrações não habilitam execução geral das famílias, resgates ou summons. [Escopo e validação da consolidação](validation.md#consolidacao-stove-ui).

O usuário escolheu **mapear as outras famílias dos caminhos**, aproveitando bindings, layout/composição, SDK e o índice pesquisável antes de calibrar. O levantamento estático existente de 33 famílias não significa execução calibrada. Começar pela leitura das pendências reais do Orbis e associar cada uma a requisito, entidade, controle/variante e prova de conclusão; priorizar as famílias observadas. A expansão está na [ALE-185](https://linear.app/akxl/issue/ALE-185).

Aventura tem progressão validada no escopo documentado, mas 3★ gerais ficam como incremento específico: condições e proposta em [campaign.md](campaign.md#planejamento-de-tres-estrelas). O objetivo de 3★ vale para as próximas fases do percurso, com equipe e condições conferidas antes da entrada; corrigir fases antigas está fora do escopo atual. Referências do Marco Brilhante (`coreloop`) e de composição estão em [assets.md](assets.md#referências-para-o-próximo-objetivo-marco-brilhante-e-estrelas); são preparação estática, sem validação de execução. Mapear não autoriza automaticamente gastos, resgates, invocações, mudanças de equipe ou novos combates.

O usuário autorizou uma unidade de Otherworld Breach, a conclusão de sua missão e trocas explícitas de equipe. O percurso Normal de Remnant of Supremacy foi concluído por primitivas com uma entrada, custo observado de um Spectral Core, resultado, retorno e incremento da missão confirmados. Não é uma rotina autônoma de todos os modos. A formação solicitada Brieg na frente, Sigret, Furious e Muwi foi conferida visualmente. [Evidência e limitações](validation.md#otherworld-e-formacao).

| Capacidade / famílias atendidas | Requisito → entidade → controle → prova | Estado e próxima unidade |
|---|---|---|
| Otherworld Breach / `combat_modes` | Missão `enter=hcs*` → `hcsc001`, Normal → dificuldade, equipe, Start único → Clear Reward e contador da mesma missão | Unidade ao vivo validada por primitivas. Hub/preparação/resultado têm adaptação parcial na árvore; identidade interna da batalha/equipe e executor genérico continuam pendentes. Hard/Hell e compras não exercitados. |
| Selecionar, reposicionar e substituir integrantes / transversal a campanha e combate com equipe | Instância e slot atuais → `formation.csb` e lista → selecionar integrante, setas; lista, `+`, slot → composição final relida | Reposição Brieg/Árbitro Vildred e substituições por Furious/Muwi observadas. Distinguir selecionar a linha da lista de aplicar a substituição; CP isolado não identifica equipe. |
| Remover integrante / mesma capacidade transversal | Integrante selecionado → `selected_btn/btn_remove` → slot vazio → cartão da lista e `+` → `+` roxo vazio → formação relida | Ida/volta unitária com Muwi validada sem gasto; Brieg, Furious e Sigret preservados. Identidade visual e continuidade do cartão, sem ID interno de instância. O `+` da lista não reinseriu automaticamente. |
| Equipar/desequipar, Equip All e descartar troca / `equipping`, `enhancement` | Item atual → candidato → atributos/slot → Equip ou prévia Equip All → Change e segunda confirmação → equipamento aplicado relido; reset descarta comparação | Seleção/reset e, posteriormente, remoção/recolocação da arma da Sigret e Unequip All → Equip All validados por primitivas. Seis slots, atributos, conjuntos e CP restaurados; ouro preservado no teste. Equip All também informou ausência de equipamento melhor com slots preenchidos. IDs internos e executor genérico continuam pendentes; prévia de CP não comprova aplicação. [Evidência e limites](validation.md#equipar-desequipar-e-equip-all--26102026). |
| Melhorar equipamento ou artefato / `enhancement` | Tipo e item → `item_detail`, `unit_item_upgrade`, `equip_item`, `item_material` e `item_equip_balance` → material/quantidade → prévia → confirmação autorizada → nível/EXP e contador de eventos | Duas aplicações de um Lesser Artifact Charm no Daydream Joker da Sigret confirmaram +0→+3→+7, custo 17.280 de ouro por aplicação e missão 0/2→1/2→2/2, com resgate. Pó de equipamento continua em seleção/limpeza sem gasto. Cópia Max Up foi apenas prévia, removida sem consumo. `item_equip_upgrade` é receita de reforja, não fórmula de EXP comum. |
| Melhorar habilidade / `hero_skills` | Personagem e `skill1/2/3` na tabela player correta → `unit_skill_renewal`, `skill_upgrade` → seleção/custo → melhoria autorizada → nível e contador | Leap Strike, Coldhearted Management e Wind Cutter de Muwi receberam +1 cada, com confirmação individual, custo unitário 120 Stigma/2.000 ouro e missão 0/3→1/3→3/3, com resgate. Tabela player grade3 necessária; custo igual não identifica receita estática única. Não substituir a exigência de eventos por nível final presumido. |
| Abyss normal / `combat_modes` | Requisito de andar máximo → hub normal → andar disponível/concluído/bloqueado → Select Team → preparação com identidade/custo → Start autorizado → conquista e contador | Uma unidade no andar 31 concluiu com CLEAR, custo de 10 de energia, Back e incremento unitário da missão. Hub/lista/preparação/resultado e custo estão na árvore parcial. Replay, Purify, Challenge Mode e generalização para outros andares não validados. |
| Arena normal e NPC / `arena` | `pvptype` aceito → Rookie Arena → aba, linha selecionada → Challenge → preparação, bandeiras e Start/Quick Match → resultado e contador | Unidades posteriores validaram NPC Quick Match (Phantom CIC's Training), Opponents sem Quick (Dcry) e NPC sem Quick (Rose Apostles Worship Service), com vitória, uma bandeira por entrada e missão 0/3→1/3→2/3→3/3, seguida de resgate. A causa do delta zero na unidade anterior permanece desconhecida. Não generalizar adversários, cooldown, boosting ou executores. |

A leitura de duas regiões roladas do Path of Heir 17 cobriu as cinco tarefas: campanha já satisfeita, melhoria de artefato, melhoria de habilidade, Abyss e Arena. IDs, contadores, estados e proveniência das leituras ficam no relatório privado `var/runs/20261026T192147Z_72af049c/otherworld-analysis.json`; catálogo estático continua sem progresso da conta. A recompensa final do grupo 16 permaneceu disponível e não foi resgatada.

**Ordem atual aprovada pelo usuário:** fechar primeiro o mapeamento das famílias e das operações compartilhadas (seleção, troca/remoção de integrantes, escolha de item/material, prévia de melhoria e confirmação de resultado); só depois ampliar a `ui_tree` com os novos campos e controles. O mapa deve ligar requisito → entidade/instância → fontes → controles/variantes → sequência candidata → custo/guardas → prova, com estado mapeado/calibrado/validado e lacunas explícitas. Um caminho indisponível pode ficar bloqueado/desconhecido: não é necessário gastar ou completar todo o pacote para encerrar o levantamento. As calibrações unitárias autorizadas continuam usando primitivas e a árvore existente, sem um segundo modelo de estado.

Antes de qualquer operação/teste, usar a [consulta por operação](assets.md#consulta-por-operacao). Reutilizar `formation.csb` e `unit_list.csb`, não somente o shell `battle_ready.csb`. Seleção/remoção, comparação/reset de item e prévias têm percursos manuais limitados registrados em [mapeamento reversível](validation.md#mapeamento-reversivel); controles e distinções de fontes em [assets.md](assets.md#melhoria-fontes). O [levantamento inicial de Abyss/Arena](validation.md#abyss-arena) foi seguido por [combates unitários e integração parcial](validation.md#combate-e-arvore). Não iniciar batalha nem gastar só para fechar o mapa. Aplicação de melhorias e vínculo da contagem de Rookie Arena continuam pendentes.

Após autorização do usuário, os combates unitários de Abyss/Arena foram exercitados e o bloco mapeado ganhou adaptação parcial na `ui_tree`, descrita em [architecture.md](architecture.md#operacoes-e-auto). A expansão posterior acrescentou telas de equipamento, confirmações e resultados validados. Isso não fecha as 33 famílias nem habilita seus executores. Identidade de instância, ligação de todos os slots e habilitação continuam desconhecidas sem reconhecimento; seleção de integrante expõe remover/detalhes com prova nativa. Auto tem guarda positiva de HUD, e não um toggle cego. O teste posterior das três variantes de Arena confirmou o crédito no grupo 17 sem estabelecer a causa do delta zero anterior. Evidências e limites em [validação](validation.md#herdeiro-17-estrelas-e-melhorias--26102026).

<a id="roteiro-por-nivel"></a>
## Roteiro por nível — 27/10/2026

`path_planning.py` prepara os 65 grupos do Path of Heir a partir do catálogo existente: 751 registros, incluindo 430 repetições no grupo 65 e 30 registros de login/tempo. São requisitos estáticos, sem progresso da conta ou disponibilidade de executor implícitos. `path plan` e `path roadmap` são puros; `path inspect` consulta a árvore atual. Linhas ocultas ficam desconhecidas e o contador do grupo representa resgates, não apenas condições satisfeitas.

A política em `data/missions/adventurer-policy.json` define um grupo por bloco, seguido de checkpoint do agente: confirmar missões, resgatar e verificar, conferir recompensa do grupo, inspecionar Marco Brilhante/baús/loja e só então escolher melhorias para o próximo grupo. Prioridade ao carry e requisitos mínimos observados; eventos de melhoria não equivalem a nível final. Marco Brilhante depende de desbloqueio, saldo e preço atuais, sem associação inventada com um nível fixo. Os limites de 3 baús/300 essências são tetos de planejamento, não autorização baseada no pacote.

**Revisão acordada em 28/10:** depois de fechar o grupo 2, analisar releituras/OCR repetidos, ordem e custo dos reconhecedores, latência até Skip/Confirm, tempos de espera de vídeos e falhas de retomada. Separar tempos do framework, transporte e decisão do agente por métricas/eventos existentes. Conferir reutilização de controles e o atalho Escape observado pelo usuário; o pressionamento de 5 s na cutscene ainda não foi validado. Estruturar então uma refatoração pequena com medições antes/depois e guardas preservadas, sem antecipar otimização durante o fechamento. Só depois dessa revisão preparar a exposição MCP.

| Operação do novo bloco | Estado |
|---|---|
| Abrir Path of Heir, incluindo Diary inicialmente selecionado | Grafo Maa e ida ao painel observados no STOVE |
| Go para Covenant, campanha do prólogo, Abyss e equipamento | Navegações unitárias observadas; tutorial e estados de retorno têm limites no fechamento do grupo 2 |
| Wish List recomendada | Aplicação 14/14 observada por primitivas; executor completo ainda pendente |
| Covenant grátis do grupo 1 | Um envio a custo zero, apresentação Angelica e missão Receive observados; não repetir se o resultado do envio estiver pendente |
| Prólogo | tar007/tar008 e capítulo 4 ijp001→ijp008 concluídos; cinco batalhas do capítulo 4 com 3★ e histórias gratuitas com retomadas. Catálogo não comprova todas as fases |
| Spirit Altar | Uma entrada cmon001 Dark Easy, vitória e retorno validados; retomada com zero Start |
| Receive de missões | Um envio elevou grupo 1 de 3/6 para 6/6 e mostrou recibo; coleta conjunta preservada |
| Recompensa do grupo | Um envio e recibo, seguido de grupo 2 confirmado; aviso de energia exigiu fechamento explícito |
| Abyss e equipamento do grupo 2 | Andar 1 vencido uma vez; Equip All aplicado a Arby; arma +3 em uma aplicação de 22400 ouro. Melhoria exigiu primitivas; executor não promovido |
| Revisão entre grupos | Grupo 2 fechado, grupo 3 em 0/5. Pauta de desempenho/refatoração registrada; nenhuma compra no checkpoint |
| Executar um nível inteiro e voltar ao agente | Compilador integrado e testes estruturais; ciclo único ininterrupto ainda não validado. Grupo 2 terminou com intervenções do agente |
| Demais famílias | Roteadas por condição; conservar os estados de mapeamento e validações por primitivas deste documento |

O primeiro grupo observado tinha 3/6 resgatadas. Covenant, capítulo 3 e Altar foram coletados conjuntamente, chegando a 6/6; o resgate final abriu o grupo 2. O checkpoint releu Arby 42/50, equipamento CP 24400 e Marco saldo 73/custo 60, sem nova compra ou melhoria. Isso não equivale a um ciclo autônomo ininterrupto: houve calibração e confirmação posterior ao aviso de Rank. Steam/STOVE usam a equivalência assumida pelo usuário para preparação; as novas operações foram testadas no STOVE. Escopo e limites em [validation.md](validation.md#fechamento-altar-resgates).

