# Assets, layouts e dados

Na Wave 3 de 29/10/2026, fontes, templates e fixtures privadas existentes são
reutilizados offline, sem descobrir/conectar/capturar a janela durante manutenção.
Observações sintéticas declaram origem de simulação; um oráculo de reconhecimento
testa composição/execução e não prova reconhecimento de pixels. Replays de imagens
históricas conservam sua proveniência e não descrevem a conta atual. Nenhum novo
template ou vínculo de asset é promovido apenas pelo fluxo simulado. A matriz e
os limites dessas camadas ficam em [validation.md](validation.md#wave3-offline).

A consolidação STOVE usa os mapas privados por operação em `var/stove-session/` e os layouts já interpretados. A auditoria `final-adapter-source-audit.json` confere existência das referências estáticas; isso não comprova o vínculo de uma variante com o cliente atual. Em particular, nível usa `unit_level_up.csb` e `dlg_promote_levelup.csb`, despertar usa `unit_zodiac2_renewal.csb` e `dlg_zodiac_reward_stat.csb`, opções usa `option.csb` e a página de Summon usa `gacha_renew.csb`. Caminhos estáticos não viram seletores de entrada.

As três variantes visuais de apresentação de baú têm recortes pequenos em `resources/epic-seven/image/coreloop_chest_presentation_*.png`, com origem, hashes, limites e calibração em `assets/template-provenance.json`. São arte do jogo recortada para reconhecimento local; não foram extraídas como textura nem identificam raridade/conteúdo. O layout exato dessa apresentação, do hub Recruit e do recibo de equipamento permanece sem vínculo comprovado, portanto esses nós não inventam uma referência de layout. Capturas completas e dados da conta continuam privados em `var/`.

Na navegação com animação, os layouts de lobby, `unit_detail.csb`, `unit_zodiac2_renewal.csb`, `unit_list.csb` e os bindings/opções foram cruzados com capturas atuais. `btn_zodiac` e `btn_lv_up` declaram 95 × 97 e ficam separados das legendas; os marcadores Maa existentes fornecem um recorte interno atual, sem transformar coordenadas CSB em posições globais. A reutilização desses glifos foi conferida no Arby. O selo de despertar acompanha a constelação (Leão/Virgem observadas), portanto sua região de leitura não é fixa na posição da Tieria. Mapa privado: `var/ui-readers-live/animation-guard-source-map.json`.

Na progressão de 29/10/2026, o mesmo lobby ilustrado foi observado com iluminação diurna. `lobby_stained_window_day.png` e `lobby_idle_upper_left_day.png` são alternativas dos dois recortes de fundo existentes; conservam ROIs, limiares e exclusões de HUD/avisos. A recuperação do HUD diurno foi validada com uma entrada mouse 4 e destino `lobby`; não representa calibração de outras ações. Proveniência e hashes em `assets/template-provenance.json`; [prova e limites](validation.md#lobby-ilustrado-diurno--29102026).

Em `wnd/inbattle_target_guide.csb`, cada `/base/n_l/n_btn_N` e `/base/n_r/n_btn_N` compõe `btn` (Button, 170 × 192) e `num` (Sprite, 26 × 34) na mesma origem local e âncora central. Isso explica o centro candidato do marcador numérico observado; não fornece coordenada global nem identidade da instância. No combate de `dap002` em `20261029T103345Z_fab80d9d`, a escolha do marcador atual de Victorika como aliada da S2 de Ruele foi seguida de mudança de turno. O mapa privado `var/heir-progression-mvtc17zn/target-guide-controls.json` conserva a referência; não há executor genérico novo de alvo.

Para o apoio do pacote às 33 famílias de missão, consulte a [análise antes das medições](assets.md#apoio-as-familias). A amostra adicional de 32 layouts, 25 DBs e nove mapas de foco permanece em `assets/local/static-family-study/`, com síntese em `data/missions/static-family-evidence.json`; ela não é um conjunto de reconhecedores calibrados.

<a id="cobertura-da-extracao"></a>

## Cobertura da extração e uso das fontes

Após a retrospectiva de ALE-179 e o refinamento de 27/10/2026, a ordem é preparar offline → calibrar com testes focados → validar ida/volta e o fluxo relevante autorizado → suíte completa ao final da versão estabilizada. Testes pesados e calibração ao vivo não devem concorrer. A regra está em AGENTS.md e o procedimento em [architecture.md](architecture.md#preparacao-antes-da-calibracao). A auditoria abrangente do pacote é acompanhada em ALE-187, antes de avançar para famílias de missão.

Inventário, extração de bytes e interpretação são etapas diferentes. O pacote tem 94.583 entradas; o conteúdo útil somado é 7.661.495.628 bytes. A extração completa é privada em `assets/local/full-pack/`: `audit.sqlite` acompanha origem, offset/tamanho, destino, SHA-256, extração e interpretação por arquivo; `files/` guarda os bytes e `interpreted/` guarda estruturas derivadas. O pacote original é aberto somente para leitura. O hash SHA-256 do original foi idêntico antes/depois da extração. A cobertura final está em [pack-coverage.json](../data/catalogs/pack-coverage.json); `partial` e `uninterpreted` permanecem distintos de interpretação completa.

`tools/inspect_csb_layout.py` passou a preservar recursos por estado de CheckBox/Button, imagem/fonte, texto, tintura, alpha, 9-slice, regras de layout, ancestralidade e resumos de animações/timelines. Foi identificado e corrigido o tratamento da classe `Widget`, cujo conteúdo base é direto; tratá-la como uma classe com opções aninhadas impedia a leitura de layouts de opções. Classes ainda sem campos próprios e valores de frames não interpretados ficam explícitos. A referência de estrutura é o [schema Cocos2d-x 3.17.2](https://github.com/cocos2d/cocos2d-x/blob/cocos2d-x-3.17.2/cocos/editor-support/cocostudio/CSParseBinary_generated.h), não uma afirmação sobre a versão exata do motor do jogo. O SHA do header oficial é registrado pelo extrator.

### Conhecimento a consultar antes de medir

| Fonte | Relação confirmada offline | Aplicação e limite |
|---|---|---|
| `key_binding.db` | Binding default → cena/evento → botão/caminho candidato | Preparar origem/destino/retorno. Paths podem ser abreviados; `btn_close` aparece em mais de um ramo. Não enviar teclas só por haver linha no DB. |
| `system_option.db` | 71 linhas com subcategoria, ordem, plataformas e chaves de texto; inclui opções de teclado PC | Identificar o catálogo de configuração correto. Não confundir com `option.db`, cujas linhas são de equipamento, nem inferir configuração atual da conta. |
| `text/en/text.db` | 145.298 linhas; `chat_notice_skip` contém a pergunta específica de desativação dos avisos; `chat_notice_title` resolve Chat Notification Settings | Usar chaves e contexto para construir candidatos a OCR/guardas. A existência de uma frase não prova que o diálogo apareceu. O layout `notice.csb` tem texto genérico em coreano; não associá-lo automaticamente a todo aviso da demo. |
| `chat_filter.csb` | Oito CheckBox compartilham `cm_checkbg.png`/`cm_checkicon2.png`; `select_all` é uma imagem branca com tintura ARGB `[255,29,66,25]` e 9-slice | A composição ajuda a explicar o fundo verde da linha principal. O campo selected não está serializado nessa amostra e assume default do schema; isso não contradiz as caixas desligadas observadas ao vivo. |
| `quick_menu_renew.csb` | Seis animações e 14 timelines, incluindo alpha/visibilidade; `slide_in` usa frames 1–11 | Identificar elementos transitórios e preparar reconhecimento de conteúdo estável. Índices de frames não estabelecem duração em segundos no cliente. |
| Mapas `gamepad_path_map` | Ligações parciais entre controles, subárvores e exclusões | Corroborar ancestralidade e variantes; não funcionam como seletor de acessibilidade nem comprovam binding ou foco atual. |
| SDK Maa instalado | `RecognitionDetail` distingue resultados brutos, filtrados e melhor resultado | Conferir a API da versão fixada e filtrar antes da fidelidade adicional; não recuperar candidatos abaixo do limiar do Maa. Duração, estabilidade e destino continuam exigindo prova local. |

Essa informação complementa os controles visuais calibrados; não os substitui automaticamente. Novas texturas extraídas permanecem candidatas até o replay e a observação do render atual.

### Resultado da varredura integral — 26/10/2026

**94.583 arquivos inventariados e extraídos, 7.661.495.628 bytes de conteúdo, com leitura de volta e SHA-256 por arquivo.** O original tem 7.666.379.762 bytes e permaneceu íntegro. O inventário completo e os dumps ficam privados. O nível final de interpretação é: **59.771 estruturados, 34.811 parciais e um opaco**, sem erro pendente de leitura nos formatos reconhecidos. Estruturado significa sintaxe/contêiner/células lidos; não é uma declaração de semântica integral ou disponibilidade na conta.

| Formato/fonte | Cobertura obtida | Lacuna preservada |
|---|---|---|
| CSB: 2.287 layouts, 126.182 nós | Hierarquia, recursos por estado, textos/fontes/campos, tintura/alpha, layout/recorte/9-slice, barras/sliders e resumos de timelines | 19 blocos de opções próprias: 14 ClippingNode, três TileSprite e dois CircleProgress. Valores de frames não avaliados; vetores FrameDuration de dois layouts são retidos como palavras não resolvidas, sem virar tempos. |
| DB: 1.037 arquivos | Células textuais de 1.016 tabelas, 14 definições de filtros virtuais e estrutura de sete tabelas com linhas opacas | 312 linhas dessas sete tabelas continuam opacas. Há metadados de controle opacos em nove tabelas e blocos auxiliares sem semântica atribuída em duas. Filtros não foram executados. |
| Atlas textual: 12.299 arquivos | Páginas, propriedades e 394.070 regiões indexadas | Posição no atlas não é caixa de clique no cliente; escala/composição continuam necessárias. Um atlas vazio foi registrado como vazio. |
| SCSP: 19.868 arquivos | Wrapper/tamanho e LZ4 conferidos; payload preservado | Estrutura binária interna ainda não interpretada. |
| SCSB: 2.551 arquivos | Wrapper/zlib e valores JSON lidos | Semântica de execução dos cenários não avaliada. |
| SCT: 11.932 arquivos | Versões 0/1/2, cabeçalhos, metadados e armazenamento bruto/LZ4 lidos | Mapeamento de processador/pixels e renderização não validados; não são templates prontos. |
| SCA: 464 arquivos | Cabeçalho, página de textura, dimensões e quantidade declarada de regiões | Geometria das regiões e payload restante não lidos. |
| PNG/JPG/WebP: 31.331 arquivos | Contêineres, dimensões e modo conferidos | Identidade semântica e render na interface não inferidos. |
| TFLite: 11 modelos | Versão, subgrafos e metadados de tensores de entrada/saída lidos pelo schema oficial | Operadores, pesos e significado das saídas não avaliados; nenhuma inferência executada. |
| Outros JSON/XML, textos, fontes e revisões | Sintaxe, propriedades ou identidade/linhas/escalares, conforme o formato | Profundidade por arquivo está no índice; não há promessa de semântica completa de shaders, efeitos ou glifos. |
| `bin64/game.bin` | Extraído com 18.449.110 bytes e hash verificado | Conteúdo opaco sem leitor compatível identificado. Não se conclui que a lógica/scripts estejam ausentes do pacote. |

O leitor de DB preserva a chave do contêiner separada da coluna `id`: algumas tabelas não têm `id`, e em outras a chave corresponde a outro campo. Variantes do índice e blocos sem chave foram mantidos com offsets/hashes. As sete tabelas com linhas opacas são `equip_item_undress`, `level_chapter_starmig`, `tile_sub_object_data`, `tile_sub_mission`, `pvp_npcbattle_team`, `pvp_npcbattle` e `character_recall`. Ausência de células decodificadas nessas tabelas não significa tabela vazia, conteúdo indisponível ou atividade liberada.

### Índice de ligações e achados adicionais

O mesmo `audit.sqlite` contém `asset_refs`, `text_refs` e `atlas_regions`. Foram indexados 142.774 candidatos literais a referências de assets, dos quais 130.173 resolvem para caminhos existentes no inventário; 324.744 ocorrências de candidatos a chaves de texto e as 394.070 regiões de atlas. A verificação confirmou que nenhum destino marcado como resolvido está fora do inventário. Referências não resolvidas podem ser placeholders, frames ou nomes dinâmicos; não são prova de recurso quebrado. O índice é estático e não é a árvore observada da sessão.

- [static-control-links.json](../data/input/static-control-links.json) liga os sete casos de abrir/fechar navegação a defaults, configuração PC, textos e controles candidatos. `O (alphabet)` é explícito no texto inglês. O caminho qualificado diferencia os dois `btn_close` do menu rápido; nomes isolados não são seletores únicos.
- `system_option`/textos também declaram **Alt — Check Key Mapping Info**, ausente da lista atual de bindings extraídos. É candidato a uma validação futura; não foi exposto como primitiva nem validado ao vivo nesta auditoria.
- `chat_notice_keyward_desc` descreve notificações por palavra-chave independentes da configuração geral. Isso reforça a separação da terceira aba; a preparação atual permanece limitada a Public/Guild conforme autorizado.
- Os modelos internos estão agrupados por caminhos `equip_cleanup`, `battle` e `banpick`. Os tensores de equipamento citam grau, atributos e melhorias; os de combate citam heróis, habilidades, alvos e buffs. Isso oferece hipóteses para estudos futuros, sem provar política correta, equivalência com a interface ou autorização para uma ação.
- [sdk-contracts.json](../data/input/sdk-contracts.json) registra versão, hashes dos módulos, campos de RecognitionDetail e assinaturas das APIs instaladas. A presença de `post_click_key` não fornece duração configurável; a ação nativa parametrizada usada pelo driver permanece separada. Não atualizar a versão do framework por suposição ao consultar documentação.

As lacunas acima permanecem documentadas, com cobertura por arquivo no JSON e no índice privado. Por decisão do usuário em 26/10/2026, a pesquisa abrangente da [ALE-189](https://linear.app/akxl/issue/ALE-189) foi encerrada como cancelada por corte de escopo; isso não declara interpretação integral dos formatos. Quando uma lacuna impedir uma operação concreta, abrir uma issue específica com fonte, objetivo e critério de conclusão delimitados.

### Referências para o próximo objetivo: Marco Brilhante e estrelas

Consulta estática em 26/10/2026, no pacote identificado em `assets/local/full-pack/identity.json`. O índice privado é `assets/local/full-pack/audit.sqlite`; `files.details.normalized_file` aponta para o JSON interpretado em `interpreted/`. Consultar por `files.source`, preservando os nomes originais abaixo, em vez de depender do nome hash do JSON.

**Marco Brilhante:** os textos `ui_lobby_coreloop_btn`, `ui_coreloop_main_title` e `system_531_title` identificam **Milestone of Radiance**, nome interno `coreloop`.

| Fonte no pacote | Referência útil |
|---|---|
| `db/core_loop_pass_track.db` | 280 linhas de etapas: `track_type`, `number`, `token`, `price`, referências de recompensa e repetição. Uma linha não comprova uma etapa disponível na conta. |
| `db/core_loop_pass_upgrade.db` | 12 linhas de transição de grau e `weight`; pesos exigem interpretação do grupo antes de serem apresentados como probabilidades. |
| `db/core_loop_pass_drop.db` / `db/core_loop_pass_config.db` | 4 regras de obtenção e 5 configurações estáticas. |
| `db/core_loop_pass_large_icon.db` | 27 ligações de item a ícone. |
| `wnd/coreloop_*.csb` | 10 layouts; `coreloop_main.csb` tem 271 nós, incluindo custo, loja e dois `btn_get`, em `/Layer/n_get/n_new/btn_get` e `/Layer/n_get/n_bagic/btn_get`. Confirmar ancestralidade e variante antes de calibrar. |
| `text/en/text.db` | Ajuda, tutorial, moedas, resgate, baús e seleção de herói; chaves `coreloop`, `to_essence`, `to_milestone_b`, `to_milestone_n`. |

Não foi encontrado binding contendo `coreloop` em `db/key_binding.db`; isso não prova ausência de atalho. Nenhuma abertura, gasto ou coleta do Marco foi validada nesta consulta.

**Estrelas de aventura:** `db/level_enter_adventure.db.mission1..3` → `db/mission_data.db.id` → `condition`/`value` e texto localizado. A projeção pequena e pesquisável está em [star-requirements.json](../data/stages/star-requirements.json): 414 entradas do catálogo de campanha, 1.146 condições resolvidas e 30 entradas sem as três referências. Ausência de referência permanece lacuna; não significa três estrelas, fase gratuita ou ausência de objetivo. O arquivo mantém parâmetros brutos e não contém progresso da conta.

Para composição, `db/character_player.db` tem 730 linhas estáticas, com `id`, `ch_attribute`, `role` e `grade`, mas não cobre sozinho os heróis jogáveis. A definição virtual `db/character.db` inclui também `character_player_grade2` e `character_player_grade3`, além de tabelas de monstros e testes. Muwi (`c3132`, texto `chrn_c3132`) foi localizado em `character_player_grade3.db`; referências do mesmo texto em variantes de monstro não identificam o jogador. Seguir a composição e preservar os candidatos, sem tratar a definição virtual como inventário vazio. Cruzar com heróis efetivamente possuídos, instâncias, níveis/equipamentos e equipe observada; o pacote não comprova posse ou aptidão para vencer. Layouts candidatos de preparação/resultados incluem `wnd/battle_ready.csb` e `wnd/result_base.csb`; conferir os nomes reais no inventário antes de ampliar os adaptadores. A lógica proposta e os limites estão em [campaign.md](campaign.md#planejamento-de-tres-estrelas).

<a id="formacao-fontes"></a>

### Formação: o que era antecipável no pacote

A calibração de 26/10/2026 confirmou que consultar somente `battle_ready.csb` deixa de fora controles importantes da composição. `wnd/formation.csb` contém 346 nós: quatro alvos `position/n_scale/baseN/bgN/btnN`, quatro `btn_change_N` com recurso `img/hero_config_btn_change.png`, e `selected_btn/btn_remove` e `selected_btn/btn_team_detail`. Os alvos de posição são `Button` com toque declarado e alpha zero; invisibilidade do desenho do botão não significa ausência de área de seleção. `wnd/unit_list.csb` fornece a lista, busca e ordenação. Os candidatos e a proveniência estão em [static-control-links.json](../data/input/static-control-links.json), no ramo `formation`.

Esses dados permitiam preparar a hipótese selecionar integrante → observar controles → trocar posição ou substituir pela lista, antes de tentar arrastar o sprite. Os campos necessários desses botões já estavam interpretados; a falha foi de consulta e integração das fontes, não uma lacuna de extração desses campos. Nos 346 nós, nenhum callback exportado tem nome, e o extrator não avalia bindings em execução, transformações globais ou timelines. Portanto o CSB não comprova sozinho a ordem dos eventos, o slot selecionado, a instância possuída ou o comportamento do botão `+` da lista.

Ao vivo, selecionar um integrante expôs remover/detalhes e setas nos outros slots. As setas trocaram posições; selecionar um herói da lista e acionar `+` abriu a escolha do slot de substituição. A tentativa de arrastar não demonstrou troca. Uma calibração posterior removeu Muwi e confirmou o slot vazio; o `+` da lista abriu os destinos, e o `+` roxo do slot vazio reinseriu o herói. As setas azuis de slots ocupados representam outra variante. A composição original foi relida, com CP auxiliar restaurado. A identidade foi conferida por nome, nível e continuidade do cartão; nenhum ID interno de instância foi exposto. O vínculo completo entre o `+` renderizado e seu layout de origem permanece em aberto; não atribuí-lo a um nó por semelhança de nome. Evidências e limites em [validation.md](validation.md#mapeamento-reversivel).

<a id="melhoria-fontes"></a>

### Itens, materiais e habilidades: fontes e variantes

`wnd/unit_detail.csb` distingue a navegação para habilidades (`n_menu_hero/center_hero/btn_skill`) e Manage Equipment (`n_menu_equipment/center_equipment/btn_equip_detail`). No gerenciador `wnd/equip_base.csb`, `CENTER/n_now` contém os itens atuais e `CENTER/n_change` contém candidatos. Selecionar um candidato muda a comparação e o CP de prévia; `CENTER/btn_reset` descarta a seleção. `n_side_base/btn_change` aplica a troca e pode ter custo; `n_side/n_right/btn_enhance` apenas abre a melhoria do candidato. O popup `wnd/item_detail.csb` também tem um `n_btn/btn_upgrade` que abre a melhoria. Esses botões não são o `CENTER/btn_upgrade` de `wnd/unit_item_upgrade.csb`, que confirma o gasto. Preservar ancestralidade, entidade e variante, mesmo quando todos mostram “Enhance”.

Em `unit_detail.csb`, `n_menu_equipment/center_equipment/btn_equip` e `btn_unequip` correspondem aos candidatos Equip All/Unequip All observados na Sigret. `item_detail.csb/n_btn/btn_putoff` e `btn_puton` são os candidatos de remoção/equipamento individual. O teste ao vivo confirmou que Equip All pode informar ausência de equipamento melhor ou abrir uma comparação de seis slots seguida por Change e uma segunda confirmação. Isso não prova uma regra universal de otimização nem identidade interna dos candidatos. Bindings não retornaram candidato contendo `equip`; nenhum novo atalho foi presumido. Fontes continuam parcialmente interpretadas e callbacks sem nome. [Evidência unitária](validation.md#equipar-desequipar-e-equip-all--26102026).

A melhoria comum usa `db/equip_item.db` (artefato, charms e campos de XP), `db/item_material.db` (pó e charms genéricos de equipamento) e `db/item_equip_balance.db` (nível, preço e XP bruto de equipamento). Exemplos de ligação: `ef317` é Daydream Joker; `est2f` é Lesser Artifact Charm; `ma_est1e` é Equipment Enhancement Powder, com `get_xp=100`; `ma_est2e/4e/6e` têm `get_xp=1500/4500/13500`. A prévia ao vivo mostrou incrementos de XP diferentes do valor bruto em dois materiais; a causa e a fórmula não foram estabelecidas. O campo `price` do pacote não equivale automaticamente ao custo mostrado em Enhance. Usar o custo atual, sem calcular orçamento só desses campos.

Equipamento e artefato compartilham o título “Enhance Equipment”, mas oferecem materiais diferentes. Pó abre `wnd/item_select_slidebar_popup.csb`, com `n_window/n_detail/{slider,btn_min,btn_minus,btn_plus,btn_max,btn_go}` e variante declarada `*n_window`; o vínculo da variante em execução não está resolvido. Selecionar a quantidade abre a prévia; clicar no material reservado o remove, sem confirmar Enhance. Quantidade entre parênteses representa reserva de prévia neste percurso, não prova consumo. Cópias de artefato marcadas “Max Up” oferecem aumento de limite, separado dos charms “Exp+”; essa operação não foi exercitada.

`db/item_equip_upgrade.db` descreve outra operação: linhas com `item_equip_base`, `item_equip_result`, `material`, `count` e `price`. Uma receita Wyvern liga uma base ao resultado `_u`, com material de reforja. Portanto essa tabela e `item_equip_upgrade_stat.db` ficam no assunto reforja, sem servir como fórmula de melhoria comum por EXP. As fontes amplas de uma família continuam incluindo candidatos de grupos compartilhados; consultar suas lacunas antes de atribuir função.

Para habilidades, seguir os campos `skill1/2/3` do personagem até `skill_player`, `skill_player_grade2` ou `skill_player_grade3`; os três primeiros IDs de Muwi são `sk_c3132_1/2/3`. `wnd/unit_skill_renewal.csb` contém os seletores `RIGHT/n_sel_skill/n_skilline/btn_skill1..3` e o botão consumidor `RIGHT/n_btn/btn_go`. `db/skill_upgrade.db` tem custos e variantes por recurso, classe e zodíaco; diversas linhas apresentam o mesmo primeiro custo observado. Esse custo não resolve sozinho a chave da receita. A ligação completa da fórmula permanece pendente, e a tela atual é necessária para custo, nível e elegibilidade.

**Otherworld Breach:** `level_battlemenu_chaosgate` liga a temporada ao título e a `chaosgate_stage`; esta liga Normal/Hard/Hell a `hcsc001..003`. Em `level_enter_battle`, as três entradas usam `type=hunt`, `contents_type/sub_type=chaosgate`, `type_enterpoint=to_chaosgatekey` e custo estático 1. Essa distinção evita confundir o token com energia ou tratar uma entrada de Hunt comum como a mesma operação. O texto antigo `help_infoadve1_10_1_desc` descreve Crack in the World em regiões opcionais, apesar do título Otherworld Breach; seu conteúdo não descreve o menu atual. Conferir versão, entidade e contexto antes de usar um texto de ajuda como contrato.

<a id="altar-quick-battle"></a>

### Spirit Altar: variante Quick Battle

O shell `battle_ready.csb` declara `RIGHT/clipper/_/n_content/n_btn_quick0/btn_quick_on`
e `n_btn_quick1/{btn_go_quick_battle,btn_quick_off}`, sob
`/base/n_window_ready`. `slide_content_quick_battle` contém configuração e
contagem. O nome on/off representa a ação candidata do botão; não prova o estado
atual. Em 28/10, o usuário forneceu referências: fundo claro significa ativo;
fundo escuro, desativado, à direita de Start. A leitura atual conferiu Easy
desativado após intervenção do usuário. Os recortes nativos `altar_quick_on/off`
vieram das capturas locais, com fontes/hashes no catálogo de proveniência.

A variante ativa mostrou quantidade 10/10 e custo 90/959, enquanto Easy normal
mostrou Start 9/959; são preparações distintas. Dark Normal mostrou Start 10/959.
Isso não autoriza Quick Battle ou consumo. Os reconhecedores são de leitura,
com positivos, estado oposto, tela de outra família e imagens escurecidas como
negativos. Transição automática do toggle e execução Quick permanecem sem prova.

<a id="abyss-arena-fontes"></a>

### Abyss e Arena: seleção, preparação e entrada consumidora

Para Abyss, `db/level_battlemenu.db` liga `abyss` a `mode=Hell` e `abysshard` a `Hell_Challenge`. `level_enter_battle.db` contém 120 entradas com `local=abyss_local_name` e 20 com `abysshard_local_name`; a presença no pacote não comprova acesso. As linhas `abyss030/031/040` ligam o andar anterior por `req_map_progress`, usam `type=abyss`, `contents_type=abyss` e declaram `to_stamina`, custo bruto 10. `abysshard001` é variante `contents_type=abyss_hard`, com custo bruto 30. O custo atual precisa ser lido na preparação; não importar regras de outros clientes ou temporadas.

`wnd/dungeon_hell_tower.csb` é um shell com oito nós e rolagem, sem os botões de preparação. A composição `wnd/dungeon_hell.csb` fornece `RIGHT/floor_info`, `RIGHT/contents/n_available/btn_go`, `n_locked/btn_go_floor` e `n_complete/{btn_go_floor,btn_replay}`. Na calibração, o andar disponível exibiu Select Team; o bloqueado ofereceu Move to Floor, e o concluído ofereceu Move to Floor e Replay. A posição de Move to Floor mudou entre essas variantes. Select Team abriu `battle_ready` sem consumo; o Start da preparação é outra ação. Purify e recompensas têm controles separados (`LEFT/cleanning/btn_clean`, `btn_temporary_gat` e `dungeon_hell_cleaning.csb`) e não foram acionados. `level_abyss_reward.db` não foi ligado à recompensa de conquista mostrada; não tratá-lo como catálogo de first clear só pelo nome.

Arena usa `wnd/pvp_sel_renew.csb` para o hub e `pvp_base.csb` para listas/abas. `pvp_bar.csb` declara fundo selecionável; ao vivo, escolher a linha marcou o adversário e habilitou Challenge, sem alterar o texto “Please choose your opponent”. Portanto esse texto isolado não comprova ausência de seleção. `CENTER_1/btn_try` e `CENTER_5/btn_try` são candidatos de abertura da preparação normal/NPC, distintos de `pvp_ready.csb` e seus botões consumidores. Os títulos e posições das abas mudam em execução: o NPC match está em `RIGHT/btn_tab_5` no layout, mas apareceu como segunda aba. Preservar a ligação exata como candidata até resolver o binding em execução.

Em `wnd/pvp_ready.csb`, `CENTER/edit_layer/n_btn_quick0/btn_go` e `n_btn_quick1/btn_go` são variantes consumidoras. Os irmãos `btn_quick_on` e `btn_quick_off`, com fundos preto e branco, alternam a preparação entre Start e Quick Match. Após a calibração reversível, uma NPC Quick Match, uma Opponents sem Quick e uma NPC sem Quick tiveram vitória e crédito individual confirmados. Ler bandeiras, custo, configuração de boosting, modalidade, adversário e limite diário antes de agir; não generalizar os três testes para outras combinações. Refresh, loja, passes, defesa e recompensas são operações separadas. [Evidência](validation.md#herdeiro-17-estrelas-e-melhorias--26102026).

`db/pvp_npcbattle_s2.db` tem 30 linhas com nomes, `team_1..4` e recompensas. `npc_06` liga o texto Phantom CIC's Training a quatro IDs de personagem. `npc_21..30` compartilham o texto Celestial Participants e têm os quatro campos de equipe vazios: não escolher uma linha única só pelo título. `pvp_npcbattle.db` e `pvp_npcbattle_team.db` têm zero linhas nesta extração; isso não significa que NPC Challenge esteja vazio no jogo. `db/pvp_reset.db` contém preços de refresh, não o custo de iniciar partida. Cooldown e atualização de lista não foram calibrados.

O binding `gladiator` declara `KEY_4`, evento `quick_menu_renew`, `btn_gladiator`; a primitiva do driver ainda não oferece tecla 4. `system_option.key_pvp.n_btn_1=ui_option_key_binding_5` referencia uma legenda, não o número da tecla. O acesso ao vivo usou o botão Arena observado no lobby e o Go da missão. O hub mostrou Rookie Arena e bloqueios de Rank 60 para World Arena/Tournament; isso não comprova acesso futuro desses modos na demo. A missão `guide_17_005_001` aceita estaticamente `normal;rta;npc;draft;rta_event;chaos` e conta partidas; as três variantes normal/NPC acima deram um crédito cada. Abortar e as demais modalidades não foram validados como prova de incremento.

<a id="consulta-por-operacao"></a>

### Consulta por operação

O assunto `notifications` também encaminha Side Story Alert a
`wnd/result_story_unlocked.csb` e à chave
`systemsubstory_unlock_popup_desc2` em `text/en/text.db`. A chave resolve
as duas linhas observadas, mas não tem ligação no índice de referências;
o CSB declara `/base/btn_close` e `window_frame/txt_desc` com outro texto
placeholder. A correspondência da variante atual continua parcial e a
entrada depende de corpo e controle reconhecidos na captura, nunca das
posições locais declaradas. `key_substory` é navegação no sistema de
opções; não foi encontrado binding de fechamento em `key_binding.db`.

O ponto de entrada é `tools/query_sources.py`, com roteamento em `data/catalogs/source-index.json`. Há assuntos para formação, Otherworld, Abyss, Arena, Auto de combate, melhoria de item/artefato, reforja, habilidades, crescimento, estrelas, missões, navegação, notificações e Marco Brilhante. As 33 famílias são consultadas diretamente de `operation-map.json` e `static-family-evidence.json`, somando fontes, referências e lacunas dos assuntos especializados relacionados; não há uma segunda cópia do catálogo de famílias.

```powershell
python tools/query_sources.py "trocar personagem"
python tools/query_sources.py "upar equipamento"
python tools/query_sources.py "andar abyss"
python tools/query_sources.py "npc challenge"
python tools/query_sources.py "ativar auto"
python tools/query_sources.py --family enhancement
python tools/query_sources.py --source wnd/formation.csb --find btn_remove --limit 3
python tools/query_sources.py --source db/level_enter_battle.db --find hcsc001 --limit 1
python tools/query_sources.py --asset img/hero_config_btn_change.png
python tools/query_sources.py --text-id chaosgate_ss3_name
```

A primeira consulta entrega fontes, referências e lacunas por assunto; `--family` resolve a família exata. `--source` resolve o caminho original no inventário e `details.normalized_file`, sem procurar arquivos hash manualmente. `--find` filtra nós/linhas e preserva seus campos declarados, callback, recursos e chave física da linha. O resultado informa total e truncamento: não escolhe um candidato como alvo. Sem filtro, retorna metadados/resumo em vez de despejar o arquivo inteiro. O limite padrão é cinco candidatos, configurável de 1 a 20.

O índice privado existente é aberto em modo somente leitura. `--asset` consulta `asset_refs` e `--text-id` consulta `text_refs`; correspondências continuam sendo referências literais, não um grafo semântico completo. A saída mantém extração e interpretação separadas, classes/células opacas e limitações. Caminho derivado fora de `interpreted/` ou identidade divergente é recusado. Sem extração local, a busca por assunto/família ainda funciona e marca a cobertura privada como desconhecida; inspeção de conteúdo requer os arquivos locais.

Para Auto, `wnd/inbattle_topbar.csb` contém `/base/top_right/n_miscs/n_top_auto/btn_top_auto`, com recursos normal/pressionado e letra A. O layout não exporta um valor booleano de Auto ligado: normal/pressionado não são on/off, e as setas podem animar. `wnd/hud_auto.csb` fornece o ramo de retratos automáticos e seletores de habilidade por herói, diferentes do toggle global. Os novos marcadores de HUD foram calibrados em capturas antes/depois da ativação, com máscaras/bordas, variantes de brilho e proveniência no catálogo existente de templates. Ausência ou conflito mantém o valor desconhecido. Controles selecionados de formação exigem o par remover/detalhes e geometria compatível, não a presença isolada de um ícone. Integração, consulta e limites em [architecture.md](architecture.md#operacoes-e-auto).

As pastas existentes `data/catalogs`, `data/input`, `data/layouts`, `data/missions` e `data/stages` organizam as referências por responsabilidade. `assets/local/full-pack/{files,interpreted}` mantém a organização auditada; a consulta aponta para ela. Acrescentar referências/aliases ao assunto pertinente ao descobrir uma composição nova, conferindo o inventário e registrando lacunas. O índice não contém progresso da conta, não abre a janela, não envia entrada e não habilita executores. A ordem atual é fechar o mapa operacional antes de ampliar os novos campos da `ui_tree`, preservando a árvore existente durante o levantamento.

O assunto `equipment_selection` encaminha `equipar todos`/`desequipar` aos controles de herói, popup individual e `equip_change_popup.csb`. A confirmação de habilidade acrescenta `skill_up_confirm.csb` ao assunto existente. `result_base.csb/Layer/n_hell/n_btns_normal/btn_hell_next` foi cruzado com a navegação observada Floor 32 → preparação Floor 33; o contador declara a previsão do próximo início. Textos de preview, confirmação e botão de aplicação são fases diferentes, sem callbacks executáveis inferidos.

### Ferramentas e reprodução

`tools/inspect_csb_layout.py` lê um CSB salvo. `tools/audit_pack.py` inventaria/extrai/verifica e interpreta, com destino vinculado ao hash do pacote e retomada que confere os arquivos já verificados; `--repair` revisita casos pendentes e `--reinterpret --extensions .csb` limita uma expansão de campos ao formato pertinente. `tools/inspect_db_table.py` lê células de um contêiner já decodificado. `tools/index_pack_references.py` reconstrói apenas os índices estáticos derivados.

Instale o extra local `.[audit]` para LZ4. O adaptador de entrada/chaves continua sendo o `e7_db_reader` da análise anterior, fornecido por `--reader-dir`; as chaves não foram copiadas para este repositório. Um novo pacote exige destino próprio. Os formatos reconhecidos têm validação de limites; formatos/campos desconhecidos preservam a origem e a lacuna. O histórico por arquivo em `interpretation_attempts` começa na expansão final; totais anteriores permanecem nos logs, sem alegar histórico individual completo desde a primeira tentativa.

### Calibrações da Wave 2

`assets/template-provenance.json` conserva os recortes e hashes de origem.
Quick Battle separa o ícone claro ativo e escuro inativo, sem executor alternativo.
Os espaços vazios da melhoria foram calibrados em cinco posições com animação,
slots ocupados e sobreposições como negativos; a correlação local é 0,75 e o MAE
continua 10. Não houve alteração de limiares globais. A confirmação de Equip All
só informa custo zero com o botão gratuito atual reconhecido na região calibrada.

As setas de reposição e os controles `+` de formação vêm dos renders históricos
de Otherworld de 26/10; a máscara verde exclui o fundo e conserva os glifos
amarelos. A janela atual de Spirit Altar foi usada para a ida/volta de Arbiter
Vildred em 28/10. O ponto superior (330,347) pertence à base visível, comprovado
por seleção nativa e detalhe do integrante; não foi deduzido do CSB. Posições
visuais, candidato destacado, integrante aplicado e ID de instância são conceitos
distintos. O vazio nativo está comprovado na esquerda; outros vazios continuam
lacunas. `formation.csb`, `unit_list.csb`, bindings e variantes da composição
continuam referências reutilizadas, sem uma lista de nomes obrigatórios.

## O que já está no repositório

- Templates pequenos derivados de capturas reais, com origem, recorte/transformação e SHA-256 em `assets/template-provenance.json`. Incluem variantes de escala, máscara de fundo, cadeado e marca de resgate. O inventário vigente de reconhecedores, estados e alvos está em `resources/epic-seven/vision.json`; evite copiar contagens dinâmicas para novos documentos.
- Quatro layouts CSB interpretados em `data/layouts/`: preparação de batalha, resultado, Orbis Guide e item de missão.
- `data/catalogs/quests.json`: roteiro estático derivado do pacote, com 877 tarefas catalogadas; não contém o progresso desta conta. Parte desse conteúdo não está disponível na demo.
- `data/stages/campaign-initial.json`: identidade, descrição e custo das 12 fases do episódio 2/capítulo 5. Veja [seleção de fase](campaign.md#selecao-de-fase).
- OCR inglês oficial `ppocr_v3/en_us`, instalado localmente por `tools/install_ocr.py`, com revisão e hashes em `assets/ocr-provenance.json`. Os modelos não são versionados.
- Capturas de teste e resultados anteriores em diretórios locais ignorados pelo Git. Imagens completas podem conter dados do perfil e não são necessárias ao bundle de execução.

Os templates de navegação atuais vêm de **recortes da tela**, não das texturas extraídas do pacote. As imagens do pacote e os layouts vão ajudar a encontrar candidatos, regiões de interesse e rótulos; ainda precisam de validação no render real.

Calibração do Orbis em 26/10/2026: o recorte original foi preservado; TemplateMatch exige correlação ≥ 0,94 e a confirmação de pixels compara os traços claros/neutros (`glyph_min=170`, MAE ≤ 12), evitando que o fundo animado do botão determine a fidelidade. O ícone escurecido por sobreposição continua sendo recusado. Essa calibração vale para a área cliente 1212 × 682; resultados e casos negativos estão em [validation.md](validation.md).

Na taberna ociosa, os recortes noturnos foram preservados e receberam variantes diurnas da parede com quadro e de um detalhe do barril. As regiões anteriores da prateleira/relógio variaram com os feixes de luz; as novas regiões foram comparadas entre capturas de momentos diferentes. A classificação continua exigindo as duas âncoras e ausência do HUD/Orbis; a fidelidade dos pixels foi apertada para MAE ≤ 10 para recusar os negativos escurecidos. `validated_template_match` avalia os candidatos já filtrados pelo Maa antes de escolher o de maior correlação que também passa nos pixels; uma variante antiga de correlação maior não elimina outra válida. Não são usados candidatos reprovados pelo Maa.

As caixas de notificação desmarcadas têm dois estilos: linha principal verde e itens individuais escuros. `checkbox_off_item.png` registra o segundo estilo, mantendo separados os templates de marcado e desmarcado. A leitura continua desconhecida quando nenhuma aparência passa ou ambas passam; nenhuma caixa desconhecida autoriza clique. Esses recortes têm origem/hash em `assets/template-provenance.json` e capturas completas privadas em `var/` e fixtures locais.

Os marcadores do menu rápido combinam o texto Music Player e o controle de fechamento; opções combinam título e seta de retorno; heróis combinam Search e o rótulo Hero Transmission. Esse último é apenas uma âncora de reconhecimento: não foi habilitado como alvo de ação. Categorias de batalha exigem Battle, Normal e Seasonal; há variantes para as duas abas selecionadas. As letras claras/cinzas usam fidelidade de pixels nos glifos, para preservar a recusa sob escurecimento. As capturas positivas, telas não relacionadas e escurecimentos sintéticos são exercitados pelo replay de navegação. Reconhecer uma categoria não identifica fase/custo nem autoriza executar seu modo.

## Limites dos arquivos do pacote

Textura, texto, animação e composição podem ser elementos separados. Um botão de 360 × 128 com escala 0,45 não aparece necessariamente desse tamanho no cliente final. Uma textura com 9-slice pode ser esticada; um atlas pode exigir recorte; idioma, hover e disponibilidade alteram a aparência.

No item de missão analisado, `btn_go` e `btn_reward` declaram a mesma posição local; a visibilidade alterna em runtime. Portanto, o nome do asset e o layout não distinguem sozinhos “ir” de “coletar”. A imagem atual deve resolver a condição.

## Extração local de um asset

`tools/extract_pack_asset.py` aceita caminhos explícitos de pacote, índice, chave já obtida na análise, nome interno e saída. Abre o pacote somente para leitura e limita a extração a um asset de até 64 MiB. Não distribui nem tenta descobrir chaves.

```powershell
python tools/extract_pack_asset.py --pack <data.pack> --index <inventario.json> --key <chave-local> --name img/_btn_gold_r_2.png --out assets/local/pack/btn_gold.png
```

Use arquivos locais reais no lugar dos argumentos entre `< >`. Índice e chave pertencem à instalação analisada. Não os trate como universais nem os versione. O índice tem 94.583 caminhos e o pacote analisado tinha 7.666.379.762 bytes.

`tools/import_session.py` migra somente os recortes, fixtures, layouts e catálogo que já produzimos; não altera a sessão de origem nem o HTML. Os recortes importados podem ser versionados neste repositório local; os direitos dos assets e do jogo permanecem com seus titulares. Publicação de material do jogo exige análise própria quando houver essa intenção.

<a id="apoio-as-familias"></a>

## Apoio às famílias

**Análise estática em 26/10/2026, antes de novas medições. Nenhuma entrada, captura ou missão ao vivo foi realizada nesta análise.** O relatório HTML anterior foi preservado. A especificação legível por ferramentas está em [static-family-evidence.json](../data/missions/static-family-evidence.json), ligada às 33 famílias do [mapa de operações](mission-operations.md). Nenhuma capacidade foi habilitada.

### Conclusão

Sim: layouts, imagens e DBs se corroboram e reduzem bastante a descoberta necessária. Permitem preparar identidade de alvos, requisitos, candidatos a templates e contratos de ação antes de abrir a tela. O benefício é maior em crescimento de heróis, produção, receitas de equipamento e Arena NPC. Algumas famílias têm apoio apenas parcial, especialmente quizzes, variantes sociais e condições que abrem outras missões.

Ainda não há uma medida de ganho de tempo ou de precisão para essas famílias. A evidência é de apoio estrutural, não de rotina pronta. A presença de uma tela ou tabela no pacote também não comprova acesso na demo nem desbloqueio nesta conta.

### O que cada fonte acrescenta

| Fonte | Uso antes das medições | O que continua dependendo do jogo |
|---|---|---|
| Condições e DBs | Requisito, IDs, quantidades, receitas, atributos, custos e horários candidatos | Progresso, inventário, preço efetivo, elegibilidade e disponibilidade |
| Layouts CSB | Componentes, ramos de tela, nomes de controles, tamanhos, posições locais e texturas | Ramo ativo, transformação até a imagem capturada, animação, botão habilitado |
| Imagens e atlas | Aparência de ícones/retratos/botões e sua relação com IDs | Recorte, escala, composição, tintura, estados positivos e negativos |
| Textos localizados | Nome legível e significado de chaves do DB | Texto dinâmico e número mostrado agora |
| Mapas de gamepad | Relações parciais de foco entre controles e subárvores | Navegação real, foco inicial e método de entrada funcional |
| Captura e logs recentes | Posteriormente, estado e transição observados | Logs não substituem a confirmação visual nem provam o contador da missão |

A ligação útil é **condição → entidade do DB → nome/ícone → componente de tela → estado observado → prova de conclusão**. Um nome de botão sozinho não fecha essa cadeia. O Maa continua responsável por reconhecimento, ações e transições; os dados servem para parametrizar esses fluxos.

### Alcance da inspeção

O inventário tem **94.583 entradas**, incluindo **2.287 CSB**, **1.037 DB**, **29.594 PNG**, **12.299 atlas** e **42 mapas de gamepad**. Esses números contam arquivos; não representam quantidades de telas ou operações independentes.

Nesta análise foram interpretados **32 layouts, 25 DBs e 9 mapas de foco**, além da inspeção visual de quatro PNGs originais. Os layouts lidos contêm 634 nós Button, incluindo variantes e repetições. O leitor não conseguiu interpretar `db/pvp_npcbattle.db` e `db/pvp_npcbattle_team.db`; `db/pvp_npcbattle_s2.db` foi interpretado com sucesso. Falha de leitura não prova que uma tabela seja obsoleta ou indisponível.

Os arquivos completos desta amostra permanecem locais em `assets/local/static-family-study/`, ignorados pelo Git. A síntese versionável registra fontes, contagens, campos e hashes dos layouts/mapas, sem incluir pacote, chaves ou dados da conta.

### Cruzamento com as 33 famílias

“Forte” abaixo significa ligação útil entre estrutura e dados estáticos. Não significa reconhecimento medido ou operação validada ao vivo.

| Grupo e famílias | Apoio encontrado | Falta resolver antes ou durante a medição |
|---|---|---|
| Comum a todas: ler missão, Go, resgate e recompensa de grupo | `growth_masterbook`, seus itens e o catálogo dos caminhos | Identidade da missão, variante ativa, contador atual e resgate efetivo |
| Campanha, outros combates, consecutivas, equipe e drops | `battle_ready`, `result_base`, `dungeon_home`; DBs de Hunt e Spirit Altar. Forte para estrutura compartilhada | Modo/fase, composição, custo, vitória e contador. Obter drop pode precisar de várias vitórias |
| Arena, Mock Arena e quizzes | `pvp_base`, `pvp_npc_chall`, `pvp_ready`; NPC S2 com 30 registros. Forte para identidade NPC, parcial para as demais variantes | Distinguir modalidades, entradas e cooldowns. Os cinco quizzes continuam sem condição preenchida no catálogo |
| Crescimento, habilidades, amizade, especialidade e apoiadores | `unit_detail`, `unit_up`, `unit_upgrade`, `unit_skill_renewal`, `unit_support`; requisitos de runas/habilidades e subquestões de especialidade | Herói e materiais selecionados, progresso, custo e expansão das subquestões |
| Melhorar, equipar, fabricar, converter, reforjar e descartar equipamento | `equip_base`, crafting e confirmação de alquimia; 395 registros de upgrade, 50 receitas de alquimia e categorias de crafting | Identidade, slot, qualidade, bloqueio e equipado. Descarte e extração precisam de operações próprias |
| Produção e gastos | Floresta, popup e sete funções produtivas com item, tempo, ícone e token. Forte para produção; parcial para gasto genérico | Distinguir produzir, coletar e comprar; quantidade e custo efetivo. Cada condição de gasto tem sua semântica |
| Lojas e invocações | Categorias, moedas e desbloqueios estáticos; popups de compra e `gacha_renew` com variantes simples/múltiplas | Oferta, estoque, banner e preço atuais; resolver os dados específicos de invocação antes de medir |
| Pets | Detalhe, síntese e cuidado; grau, afeto e limites de habilidades | Pet, recursos, limite de cuidado e habilidades preservadas. Cuidado e síntese não são o mesmo contrato |
| Connections, presentes e registros de história | `destiny`, `destiny_present`, nove categorias e 36 missões. Forte para entregas; parcial para registros | Desbloqueios e progresso; registros ainda precisam de sua tela específica |
| Guilda e World Boss | Atividades, presença, tipos/limites de doação, NPCs e ramo de resultado World Boss | Guilda atual, elegibilidade, horário e acesso na demo; layout não confirma disponibilidade |
| Rift, Trials e Theater | Entradas normal/difícil, atributos, condições de chefe; 96 registros de teatro com requisitos. Layouts e ramos próprios | Temporada, acesso, equipe, pontuação, ingresso, custo e prova exigida pelo caminho |
| Condições de tempo e atividades diárias | Conquistas, limites, reset e janelas em DBs pertinentes | Horário do servidor, elegibilidade e recompensa atual; campos antigos de horário podem coexistir com `is_always_open` |

As 11 linhas de grupos específicos distribuem as 33 famílias sem duplicação. A leitura comum do caminho é uma capacidade transversal. Não se deve inferir que toda família de uma mesma linha tem o mesmo nível de cobertura.

### Exemplos que já evitam exploração desnecessária

**Arena NPC:** `pvp_npcbattle_s2` liga nome, quatro membros de equipe e recompensas de vitória/derrota. O primeiro registro da amostra resolve para “Summer Memories”, com Holiday Yufine, Summer Break Charlotte, Melany e Helen. Os IDs dos heróis levam a atributos e retratos existentes no pacote. Isso permite preparar âncoras de identidade melhores que somente a posição de uma linha. Não prova que esse adversário esteja disponível agora. A tabela `pvp_npcbattle_lineup`, apesar do nome, trouxe apenas `id/export_id`; a composição confirmada veio da tabela S2.

**Penguin Nest:** `forest_spirit_function` liga a função ao nome, ícone, item produzido e token. O ícone `shop/shop_ma_penguin.png` mostra um ovo no ninho; os itens Newbie/Experienced/Epic Penguin usam outros ícones. Separar imagem da função e imagem do produto evita procurar o asset errado. Campos numéricos de produção/troca ajudam a formular hipóteses de custo; o significado e o custo efetivo precisam ser confirmados na tela.

**Connections:** na tarefa `de_4_c1087_03`, `destiny_give_count` com `count=1` é uma entrega. `give_code=to_honor` e `give_count=30` resolvem o requisito como **30 Brave Crests**, corroborado pelo texto localizado. Medir antes dessa ligação poderia produzir uma rotina com quantidade errada.

**Equipamento:** uma receita estática associa equipamento base/resultante, material, quantidade e ouro — por exemplo, uma entrada Wyvern registra 200 materiais e 350.000 de ouro para reforja. Isso ajuda a validar a proposta antes da confirmação. Não define qual item da conta deve ser escolhido nem substitui o preço mostrado.

### Ambiguidades que as medições precisarão resolver

- No item do caminho, `btn_go` e `btn_reward` compartilham posição local `[730,68]` e tamanho declarado. A visibilidade e a variante determinam se a ação é ir ou receber.
- Na floresta, `btn_cost_1` e `btn_shop_1` compartilham posição, tamanho **e textura verde**. Nem coordenada nem template desse botão isolado distinguem a operação.
- `result_base` inclui ramos diferentes para recompensa, Trials, World Boss, Arena NPC, outras modalidades e derrota. Um `btn_go` detectado sem contexto não identifica o destino.
- Em `unit_up`, um botão tem posição local `[-143,20]` sob `CENTER`. É uma posição relativa válida, não um ponto de clique na janela. Escalas, âncoras, pais e ajuste de resolução precisam ser considerados.
- O PNG verde inspecionado é apenas o fundo do botão. Os dois únicos campos de texto Button preenchidos nesta leitura contêm o placeholder “Button”. A amostra não fornece legendas finais suficientes: elas podem estar em outros nós, textos localizados ou conteúdo dinâmico.
- Os mapas de gamepad citam caminhos como `unit_detail/.../btn_zodiac` e adjacências, mas são parciais. Não são seletores de acessibilidade do Windows nem prova de entrada por teclado calibrada.

Esses casos favorecem **âncora da tela + identidade do alvo + estado habilitado + confirmação do destino**, com OCR onde necessário. Templates de aparência genérica devem ser limitados ao contexto correto, sem tratá-los como identidade da ação.

### Lacuna descoberta: subquestões de especialidade

O mapa original cobre **877 missões, 58 condições e 33 famílias dos caminhos catalogados**. `classchange_quest` acrescenta **96 subquestões**, com **23 condições distintas**, das quais **17 não aparecem entre aquelas 58**. O escopo dos números originais permanece o mesmo; essas linhas não foram incorporadas silenciosamente às famílias nem convertidas em operações executáveis.

Há condições adicionais de matar por raça/tipo/alvo, coletar materiais em determinados conteúdos, participar com herói específico, acampar, obter moedas e alcançar estados de heróis/equipamentos. A lista exata está em `specialty_nested_gap` na síntese JSON. Algumas podem reutilizar combates e crescimento, mas precisam de semântica e parâmetros explícitos antes de medir. O campo `btn_move` oferece uma pista de destino interno; não estabelece uma API de automação suportada.

### Preparação recomendada antes das medições

1. Resolver offline as ligações entre condição, alvo, quantidade, texto e asset; expandir primeiro as subquestões dos tipos que pretendemos testar.
2. Para cada operação escolhida, registrar a tela esperada, âncoras candidatas, variante, parâmetros, custo permitido e prova de conclusão. Mapear o alvo específico, sem transformar toda primitiva em rotina.
3. Separar lacunas de dados das lacunas visuais. Quizzes sem condição, estoque de loja e disponibilidade na demo não se resolvem apenas medindo coordenadas.
4. Quando autorizadas, fazer medições dirigidas: enquadramento/escala, estado positivo/negativo, controles habilitados, transição e latência. Reutilizar o que já foi validado no perfil de campanha sem generalizar sua validação a outros modos.
5. Validar uma unidade de ação e o contador da missão antes de compor uma rotina maior. Resgate e recompensa de grupo são etapas distintas, com reobservação após cada banner.

Uma boa primeira candidata continua sendo a produção na floresta, pela ligação entre função, item e moeda e pelo escopo curto; a ambiguidade produzir/comprar precisa ser resolvida. Arena NPC também tem boa preparação de identidade, mas depende de confirmar modalidade e acesso. Esta recomendação define a ordem de preparação; não inicia essas operações.


## Identidade estática do prólogo no roteiro — 27/10/2026

`data/stages/adventurer-prequel.json` contém 30 candidatos do episódio 0. A legenda antiga de `level_enter_adventure.db` não identifica sozinha o título de história atual: a resolução usa `mission_data.db` por `area_enter_id`, seguido das chaves de texto. O JSON preserva as chaves originais, localização, título, descrição, hashes das fontes e progresso da conta desconhecido. Exemplos, limites do executor e evidência ficam em [campanha](campaign.md).

Os novos recortes de Path of Heir, Covenant grátis, linha disponível e cabeçalho cinza de história têm origem e transformações em `assets/template-provenance.json`. São recortes do jogo, sem autoria atribuída ao projeto. A variante cinza depende do par Skip/histórico e não exige nome do personagem. Os resultados dos replays ficam em `var/`, e a [validação](validation.md#caminho-inicial-stove) distingue reconhecimento, envio e destino. A revisão posterior confirmou que `CHAPTER COMPLETE` já havia transitado ao capítulo 4; não há prova de que exigia controle de fechamento. Não atribuir o fechamento de `result_story_unlocked.csb` a esse aviso por semelhança de nome.

O assunto `spirit_altar` agora aponta para `wnd/dungeon.csb`, a composição observada do Altar, junto a preparação/formação e resultado comum. `dungeon_home.csb` permanece como fonte de outra composição, sem substituir o Altar. `data/stages/spirit-altars.json` liga 20 candidatos estáticos de elemento/dificuldade a rótulo, custo e proveniência; apenas Dark Easy cmon001 teve uma unidade validada neste bloco. Recortes de Receive, tick de resgate, CLEAR/rodapé e recompensa do grupo estão no mesmo catálogo de proveniência. Saldo, custo e nome de personagem são conteúdo atual e não devem virar âncoras fixas de composição.

A extensão estática do episódio 6 em campaign.json usa `adventure_ma`, mission_id `ma_N_M`, pais `machN`, textos e referências literais `ep6_ch*`. Foram examinadas 49 linhas: 32 fases principais e 17 subentradas tile sem missão/capítulo/ordinal próprios. História com tipo story e custo declarado 0 conserva esse custo; tile com 0 permanece null, sem inferir gratuidade. Hashes e limites da extração estão em episode6_extraction no catálogo; relatório privado var/admin-episode4-20261030af/episode6-extraction.json.


Repetição pelo rodapé (2026-11-01, somente preparo offline): consultado o índice
por “repetir fase try again” e o interpretado de `wnd/result_base.csb` (SHA-256
`ef5d2886d91e8df3cab4bc7578485f27c14394e6bf5b693841ee3d33c9101e0e`).
Há `btn_again`, `btn_next`, `btn_back` e `btn_lobby` em
`/Layer/n_buttons/CENTER/n_right_btns` e `n_left_btns`, além de nomes repetidos
sob `n_chaos` e variantes de derrota. A ação candidata usa o texto atual
Try again, junto ao template atual de Lobby, Leave e razão custo/saldo; as
posições declaradas não são usadas como coordenadas globais. A imagem fornecida
pelo usuário mostra a variante sem Next Difficulty, ainda sem captura nativa
calibrada desta sessão. O custo é numérico; a moeda e a identidade da fase
permanecem desconhecidas. `key_binding.db`/catálogo de hotkeys não fornecem
binding de Try again; a consulta `system_option.db --find auto` não encontrou
candidato (71 linhas, campos/plataformas preservados). Auto reutiliza apenas o
leitor visual e o gesto existentes. SDK local identificado: Maa v5.14.3; o novo
grafo reutiliza `ScreenTarget`, `LongPress` e `OperationBoundary` do driver.


Theater (02/11/2026): os recortes `theater_story_*` foram acrescentados ao
catálogo `assets/template-provenance.json`, com fonte, hash, caixa e máscara.
Há composições com Speed/History/Pause e com Play/History/Pause. As variantes
plain/forest usam máscara verde nos pixels externos aos glifos e TemplateMatch
método 3, threshold 0,85, seguido de MAE 18. A máscara plain também exclui
pixels que mudaram entre duas capturas do fundo animado. Positivos incluem
cenário normal, preto, personagem animado e floresta; negativos incluem menu,
confirmação, combate e CLEAR, além de escurecimento artificial dos positivos.
São assets do jogo recortados localmente; não há atribuição de autoria própria.
As capturas completas permanecem privadas em `var/`.


Theater, reconhecimento genérico (02/11): os novos nós nativos `*Shape` reutilizam
os glifos mascarados plain, sem novos recortes por cenário. Forma filtrada,
visibilidade/contraste e OCR atual da região compõem o reconhecimento; os antigos
matches de cor permanecem como evidência separada. Falhas reais de abertura do
ato 9 e diálogo em `var/runs/20261102T163949Z_29cd54d0` e
`20261102T170612Z_959b2b60` entraram nos positivos privados. A consulta ao assunto
theater foi preservada em `var/theater-generic-20261102/source-query.json`;
`wnd/story_theater_intro.csb` não consta no inventário consultado. A ancestralidade
da abertura continua desconhecida, sem atribuir a ela o layout do painel main.
