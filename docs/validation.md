# Validação

Os resultados abaixo são registros históricos de evidência, não uma instrução para repetir suítes completas durante cada ajuste. A estratégia atual é testes focados durante desenvolvimento/calibração e suíte completa no fechamento estabilizado, conforme [AGENTS.md](../AGENTS.md) e [procedimento técnico](architecture.md#preparacao-antes-da-calibracao). Não executar testes pesados junto da calibração ao vivo; alterações somente em documentação não exigem pytest.

## Perfil STOVE: conexão e primeiros controles — 26/10/2026

A sessão autorizada no launcher STOVE usa descoberta nova de `EpicSeven.exe`, título `Epic Seven` e classe `GLFW30`; versão observada `epicseven@stove_epic7live-1.0.999`. A janela inicial media 1280 × 720. O Windows recusou a primeira conexão com acesso negado: jogo elevado e driver não elevado. Após autorização explícita do usuário, somente o driver foi elevado. A conexão aplicou 1212 × 682 e bloqueio de tamanho; captura FramePool 2, mouse/teclado PostMessage 4. Não houve troca de cliente, identificação herdada, Computer Use ou alteração interna do jogo.

O perfil local `config/local.json` usa o bundle independente `resources/epic-seven`, sem catálogo de fases nem rotinas de campanha da conta Steam. `resources/epic-seven/model` referencia localmente o OCR oficial existente e é ignorado pelo Git. O transporte privado mantém o mesmo protocolo `agent`; a reconexão encerra normalmente o Runtime antes de redescobrir a janela, sem captura concorrente. O prazo da sessão e os pedidos ficam em `var/stove-session/`, sem virar contrato permanente.

O template antigo de Skip teve score 0,616 no recorte correto e foi recusado pelo limiar 0,9; o perfil novo possui recortes próprios e exige Skip + History. O modal exige pergunta de confirmação + Confirm, com negativos de fundo escurecido, filme e controles ausentes. Ausência de Skip não é classificada como introdução com clique mantido. O usuário confirmou o gesto mantido para cutscenes, mas esse gesto ainda não foi validado neste perfil.

Na execução `20261027T003836Z_6bfd84bc`, 000001→000003 confirma Skip por alvo abrindo o modal; 000006→000007 confirma a aceitação do Confirm observado e a saída para filme. Outro Skip foi aceito em 000009→000010 e confirmado em 000011. O primeiro ponto de confirmação em 000004 ficou fora do retângulo efetivo e não concluiu; a origem foi relida antes do ponto correto. A carta obrigatória foi resgatada uma vez e o resultado Received Reward observado em 000020 antes dos fechamentos. Não houve batalha iniciada nesse bloco.

O aviso de tutorial exige conjuntamente Skip Tutorial, Episode e a instrução específica; não é um reconhecedor de lobby genérico. Na execução `20261027T004547Z_58a7ec10`, 000001 reconheceu o aviso, 000002 enviou Skip Tutorial e 000003 confirmou o lobby sem o aviso. Pontos posteriores recusados por mudança visual não foram contados como entradas. Proveniência em `assets/template-provenance.json`; mapas, diagnósticos e replay privado em `var/stove-session/`. A suíte completa inicial passou com 210 testes; as unidades posteriores de modal/tutorial passaram em testes focados e validação estrutural, sem promover o restante das telas STOVE.

O fallback explícito de mouse 64 permitiu combate manual neste perfil; captura 2 e teclado 4 foram mantidos. `skill-double-tap` usa dois cliques em um único nó Maa, separados por 80 ms, com contexto de combate e as guardas originais de janela, idade e compatibilidade global/local. Na execução `20261027T020703Z_0dc452c4`, 000003→000004 e 000006→000007 confirmaram habilidades por dano/recarga; 000009→000010 confirmou a troca de onda. O retorno da chamada não comprova esse efeito sozinho. A suíte completa após o gesto passou com **232 testes em 238,62 s**; o teste nativo verifica dois cliques no contexto positivo e nenhum no negativo. As falhas de compatibilidade preservam quadro atual, métricas e `input_sent=false`, sem relaxar limites.

Os resultados de três batalhas do primeiro capítulo do prólogo STOVE foram confirmados com 3★: `20261027T012018Z_f4ee88cc/agent_000011`, `20261027T021700Z_167013b0/agent_000008` e `20261027T024311Z_f1c0e142/agent_000034`. O último também validou ao vivo a projeção `campaign_result`: CLEAR, desenho de três estrelas e três checks atuais, com os rótulos de objetivos lidos na mesma captura. Isso não identifica a fase nem a recompensa recebida por inferência. Cada batalha teve uma única entrada; equipes de história não foram tratadas como inventário da conta. O perfil então tinha 37 nós, validação sem erros e 18 testes focados do incremento de leitura. O Auto não foi confirmado nos testes unitários anteriores, e sua disponibilidade permanece desconhecida; não houve repetição de toggle na mesma batalha.

Na execução `20261027T031057Z_dcdc3935`, a unidade de formação confirmou vaga→lista (000007→000010), `+` do cartão→destinos (000012→000013) e `+` roxo→Victorika presente na formação (000015→000016). O CP passou de 12.486 para 16.222 como evidência auxiliar; a presença foi conferida na imagem, e a instância e o ID do slot continuam desconhecidos. A preparação 000019 foi seguida por uma única entrada; o resultado 000065 confirmou 3★. A projeção de formação foi calibrada offline depois desse percurso, sem retroatribuir o reconhecedor à entrada manual. Com avisos de herói, capítulo 2 e formação parcial, o bundle chegou a 43 nós, zero erros de validação e **254 testes passando em 245,21 s**. O estudo de bordas de S1 falhou em positivos independentes e não foi promovido a alvo ou executor; ausência de recarga continua sem comprovar prontidão.

O início de `dap005` precisou de um alvo nativo de identidade restrita após três recusas de coordenada, todas com `input_sent=false`. O estado `prequel_preparation_dap005` exige Ready, âncora local/título, OCR exato de Corrupted Forest e An Unpermitted Future, custo 8 com saldo suficiente e uma única caixa atual de Start Quest. Quatro positivos e doze negativos/ablações passaram sem baixar limites. Em `20261027T034529Z_6b3c4cd0`, 000001 reconheceu a preparação; o único clique em 000002 abriu a vinheta Act 5. A espera de seis segundos por `story` expirou durante a vinheta, mas 000003 confirmou a história: não houve repetição de Start. O resultado 000054 confirmou 3★. O bundle de 48 nós validou sem erros, e **256 testes passaram em 256,16 s**. Esse alvo não é um executor geral de campanha ou autorização para outra fase.

Na mesma execução, a seleção unitária de aliado foi exercitada em combate: Iseria S2 em 000082, seleção de Krau em 000085, recarga/novo buff em 000086 e S3 de Krau novamente disponível em 000089. Ruele S2 foi selecionada em 000100; um ponto no corpo de Iseria foi recusado sem entrada, e o clique na barra de vida observada em 000105 foi seguido por 1.226/1.249 de vida, barreira e troca de turno em 000106. O veneno ainda estava visível, sem conclusão de remoção durável. Os IDs de instância permanecem desconhecidos; recargas atuais da variante NPC não foram substituídas pelos valores estáticos. `dap006` terminou em 000148 com 3★ apesar da queda de Iseria; o requisito observado era um ou mais sobreviventes. Não houve derrota da fase nem repetição da entrada.

Na execução `20261027T045511Z_1ec60bbf`, o fechamento da aquisição de Victorika foi confirmado por alvo nativo em 000001→000002→000003, chegando ao prêmio de história. O estado exige identidade e apresentação de aquisição; a presença isolada de Confirm também ocorre em anúncios e não autoriza esse alvo. O bundle de 55 nós validou sem erros e a suíte passou com **258 testes em 262,30 s**. O TAG obrigatório de `dap007` foi observado em 000030→000032→000033, trocando Iseria por Rinak; a origem estática correta é a variante NPC `c1168_dap007`, não a ficha genérica. HP e contador são fatos visuais; instância, prontidão e semântica de recursos sem prova permanecem desconhecidos. Os resultados 000054 e 000083 confirmaram 3★ em `dap007` e `dap008`, com uma entrada por fase, sem derrota nem novo toggle de Auto. Os avisos posteriores confirmaram desbloqueios de Orbis Guide e Summon.

O protocolo `agent` conserva agora o ID do pedido quando a validação de argumentos falha, permitindo ao transporte distinguir a recusa de uma resposta alheia. O teste de regressão verifica zero captura/entrada para o comando inválido e a aceitação da leitura seguinte; os 17 testes da sessão passaram. Na falha original da sessão privada, a entrada inválida não chegou ao jogo, o transporte encerrou normalmente e uma nova conexão redescobriu a janela.

O anúncio de Renoa ganhou um alvo próprio de fechamento, sem semântica de aquisição: nome, Ranger/Dark, descrição, botão normal e OCR atual de Confirm são exigidos juntos. Três positivos e dez negativos passaram; em `20261027T055624Z_d8a1e216`, 000001→000002→000003 confirmou apresentação→clique único→tutorial no lobby. As duas recusas anteriores por variação global da animação enviaram zero entrada. O bundle de 59 nós validou sem erros e a suíte completa passou com **265 testes em 273,36 s**.

Um indicador de notificação cobriu parte da referência do menu do lobby. A variante seguinte ignora apenas a área desse indicador e mantém vitral, Episode e exclusões de sobreposição. O alvo `milestone_lobby_entry` exige também ícone/título atuais: quatro positivos reais, duas variações do indicador e quatorze negativos passaram. Em `20261027T060242Z_390d2724`, 000001→000002→000003 confirmou a entrada no Marco Brilhante; a loja foi observada em 000010. O bundle de 60 nós validou sem erros e **266 testes passaram em 281,78 s**. A loja disponível não implica saldo, compra ou equipamento obtido.

Nessa execução, o tutorial de `tar002` anunciou explicitamente Auto-Battle e Battle Speed (000136). Após fechar o tutorial, o HUD manual 000139 recebeu um único clique no Auto em 000141; habilidade automática e avanço de ondas foram comprovados em 000142–000144, sem entradas de habilidade. O brilho azul imediato não é indicador persistente: em 000144 o ícone superior já estava branco e girando, enquanto os quatro retratos/checks do HUD de Auto estavam presentes. A leitura automática exige composição completa e mantém cenas antigas bloqueadas, transições e animações como desconhecidas. O CLEAR 000152 mostrou visualmente três estrelas e três checks; nessa captura a projeção ainda omitiu o total por falha conservadora de um reconhecedor. Não houve repetição de Start nem de toggle. Isso valida uma batalha, não todos os modos ou uma cadeia geral STOVE.

O alvo `arbiter_roster_row_10` foi limitado à tela de equipamento de Victorika nível 15 e à composição observada da lista, com três positivos e dezesseis negativos. O nome parcialmente coberto não foi promovido a OCR confiável nem a ID de instância. Em `20261027T065733Z_52d8869f`, 000001→000002→000003 confirmou a seleção de Arbiter Vildred nível 10 após recusas de coordenadas sem entrada. Equip All continuou sendo prévia (000075), Change abriu a confirmação (000078) e uma aplicação produziu os dois itens e os atributos esperados (000081). O resultado de nível 000093 e a leitura 000096 confirmaram um único gasto e o nível efetivamente obtido, sem confundir a previsão de EXP com resultado nem os atributos base com equipamento removido.

O incremento de leitura do Marco Brilhante separa tela principal, candidatos do seletor, seleção visível, confirmação proposta, apresentação Obtained e recibo de item. NEW isolado não comprova aquisição. Custo e saldo usam OCR com candidato único explícito; duplicidade ou baixa confiança mantêm o valor desconhecido. Progresso, moeda sem leitura válida, instância e habilitação continuam desconhecidos. Esse incremento não cria controles executáveis. O bundle de **84 nós** validou sem erros; **280 testes passaram em 334,38 s** após as leituras, a seleção restrita e o reconhecimento de Auto.

O Skip do tutorial de equipamento foi limitado à instrução observada e ao cartão de Victorika nível 15: quatro positivos e quatorze negativos, sem ampliar o template nem os limites de entrada. Em `20261027T074608Z_0b4c4ba2`, 000001 reconheceu o tutorial, 000002 enviou um único Skip e 000003 confirmou a página de herói sem a sobreposição. Nenhum equipamento foi movido nessa transição. O bundle de 86 nós validou sem erros; **281 testes passaram em 346,46 s** após a validação ao vivo.

O menu da página de Victorika recebeu um alvo restrito à aba Hero, nível 15 e cartão selecionado, reutilizando o recorte do grid. Três positivos e dezessete negativos passaram; `20261027T080001Z_4bad03e5/000001→000002→000003` confirmou a abertura ao vivo após duas recusas de coordenadas sem entrada. O bundle de 87 nós validou sem erros e **282 testes passaram em 365,79 s**. Na mesma execução, `tar004` teve uma única entrada (000032), com Arby 42, Victorika 15 e Tenebria 6 atribuídos pelo Auto Assign observado. O Auto permaneceu ligado, sem novo toggle; 000036 mostrou três retratos/checks. A história posterior foi seguida por CLEAR de três estrelas e três checks (000044), com os três integrantes sobreviventes. A projeção conservadora ainda omitiu o total de estrelas; a comprovação nesse caso foi visual. O resultado 000046 confirmou Victorika 16 e Tenebria 9. Um banner de amizade bloqueou a confirmação seguinte, sem novo gasto ou início de batalha.

O fechamento do banner de amizade exige título, badges 1 e 2 e Tap to close, com três positivos e quinze negativos. `20261027T081838Z_d968bc8e/000004→000005` confirmou a remoção da sobreposição e o retorno às recompensas. Uma captura intermediária recusou entrada por estado desconhecido; o botão Confirm abaixo do banner não foi usado para fechá-lo. A rota de fontes passou a incluir `result_intimacy.csb /Layer/btn_close`. O bundle de 91 nós validou sem erros e **283 testes passaram em 382,81 s**. A composição de Auto com três heróis permanece como estudo privado; a leitura canônica atual de ligado ainda exige a composição calibrada de quatro retratos/checks.

O grupo Path of Heir 1 foi observado no STOVE com seis etapas. O uso anterior de pinguins já satisfazia a primeira condição, mas o grupo ainda marcava 0/6. Um Receive produziu recibo de 50.000 de ouro e 1/6 (`20261027T081838Z_d968bc8e/000094→000096→000097→000099`). A tela de Summon aberta pelo Go dessa missão exibiu um banner limitado; nenhuma invocação foi enviada nessa navegação. O alvo `summon_quickmenu_recruit` foi restrito à sobreposição observada sobre Summon e validou três positivos e dezesseis negativos. `20261027T084618Z_f4017642/000001→000002→000003` confirmou Recruit aberto; o bundle de 95 nós validou sem erros e **284 testes passaram em 394,24 s**. Nessa execução, G com pressão de 100 ms a partir de lobby reconhecido abriu o Diary (000020→000021); a aba Path of Heir precisou ser selecionada explicitamente.

O diálogo e a apresentação da Free Spirit Tieria receberam alvos restritos à identidade e à composição atual, preservando o Skip e o Confirm comuns. O bundle de 98 nós passou em **285 testes, 397,61 s**; o de 101 nós, em **286 testes, 425,39 s**. A missão de Connections exigia a fase já concluída `tar006`; Receive mudou 0% para 100% e Connection Complete abriu a apresentação. A aquisição foi comprovada por Connections 1/9 e pela heroína no elenco, nível 1/40 e habilidades +15 (`20261027T091000Z_a714adef/000003`, 000006, 000012 e 000015). A apresentação isolada não foi usada como único comprovante de posse.

Os alvos de entrada de Awaken e Level Up da Tieria apenas navegam e exigem nome, elemento/classe e composição de Hero. Não dependem do nível 1 nem aplicam materiais. O bundle de 105 nós validou sem erros e **287 testes passaram em 446,31 s**. Em `20261027T091912Z_5e4ad40e`, a prévia 000009 mostrou 10/8 Runas de Luz, com ordem disponível/necessário; um único Awaken (000011) produziu o resultado 000013: eficácia 0%→6%, ataque 76→96 e vida 262→322. A árvore de despertar 000016 e a página de herói 000022 mostraram a primeira estrela despertada, ainda no nível 1/40. O ouro permaneceu 1.258.703. O saldo restante de runas não foi relido e não é apresentado como medição. Em 000031, as duas tarefas do Caminho estavam 1/1 com Receive; um único resgate produziu os dois itens em 000034 e o grupo 3/6 em 000036. O recibo de itens e o contador do grupo foram conferidos separadamente.

A sessão STOVE encerrou automaticamente no prazo de 27/10/2026 às 09:30 UTC (06:30 America/Bahia). O observador registrou `disconnected`, o estilo original da janela foi restaurado, o tamanho 1212×682 foi preservado e a trava de sessão foi liberada. Uma solicitação manual de desconexão que chegou após esse encerramento ficou sem processamento e foi arquivada como expirada; não houve reconexão. A consolidação posterior da `ui_tree` usa somente evidências salvas. Relatório privado: `var/stove-session/deadline-cleanup-report.json`.

<a id="consolidacao-stove-ui"></a>

## Consolidação das telas STOVE na árvore — 27/10/2026

A integração posterior ao prazo é exclusivamente offline. Os adaptadores `operational_stove*` consomem a observação corrente e produzem painéis, itens e controles na `ui_tree` existente. Incluem configurações, lobby/menu, avisos/resultados, hub Recruit, Connections, Moonlight's Blessing, apresentações, inventário/correio e suas confirmações, loja do Marco Brilhante, Summon, equipamento, nível e despertar. Os adaptadores compartilhados de formação, Equip All, coreloop e combate foram preservados. Path of Heir e Diary usam a ancestralidade canônica de grupo/missão/controle, sem relatório paralelo nem catálogo como progresso atual.

O manifesto privado `var/stove-session/stove-ui-final-consolidation-map.json` organiza 39 famílias de telas, distintas das 33 famílias de operações. A lista contém escopos parcialmente reconhecidos e desconhecidos explícitos; não significa 39 executores ou classificação integral das 1.076 capturas do inventário. O replay nativo e as árvores reconstruídas ficam em `var/stove-session/final-native-replay/`; os arquivos de origem permanecem intactos.

Os testes de consolidação verificam prévia versus resultado do despertar, custo 10/8 como disponível/custo, atributos atuais no recibo, ausência de identidade herdada, prioridade de sobreposições, perfis incompatíveis, OCR ambíguo/baixo e controles consultáveis sem habilitação presumida. Path of Heir 1 mostra o contador atual 1/6 e depois 3/6; Receive sem contador lido mantém a condição desconhecida. A linha cortada do Spirit Altar não recebe contador inventado. O recibo não é associado a IDs de missão ou quantidades por inferência.

O marcador de baú foi exercitado no Maa 5.14.3, sem controlador de janela: três positivos usados como origem dos recortes, treze negativos reais de outras telas e três negativos escurecidos. Exige também o prompt atual para criar o painel; remover o prompt mantém a composição desconhecida. Não há positivo independente para generalizar cada variante a novas animações, nem novo alvo de clique, estado visual ou executor. A estrela rosa do despertar e o Auto com três heróis continuam sem promoção; o segundo carece de outro positivo independente. Instâncias, seleção, saldos/quantidades sem vínculo e habilitação sem prova continuam nulos. Layouts não vinculados permanecem sem referência.

O replay inclui 132 artefatos: 124 observações completas geraram árvores válidas, com 122 projeções operacionais/de missão ou valores de Auto e duas leituras de Auto conservadas como desconhecidas. Oito resultados de ações sem OCR/janela brutos foram contabilizados separadamente. São 50 valores distintos de painel operacional e os grupos `group_guide_01`/`observed_diary`, sem equiparar esse inventário a cobertura de todas as variantes. A projeção `ui.quest_view` e os eventos 1/6 → 3/6 foram exercitados pelo observador compartilhado sem captura ou reconhecimento adicional; desconexão continua invalidando o snapshot.

As validações estruturais passaram sem erros: perfil Steam com 135 nós e perfil STOVE com 106 nós. O nó adicional STOVE é somente reconhecimento com `DoNothing`; `target_states` e executores não foram ampliados. Nenhuma conexão ao jogo, gasto ou entrada foi realizado nesta consolidação.

A suíte completa passou com **324 testes em 443,17 s**, registrada em `var/stove-session/full-tests-ui-consolidation-complete.log`. A revisão final separou o número do cabeçalho do Diary de `group_counter`: o número permanece em `header_number`, enquanto o contador de missões fica desconhecido. Essa alteração de campo, posterior ao início da suíte completa, passou nos **54 testes focados** de consolidação e sessão do agente. Os dois testes anteriores de preparação também passaram após preservar a composição nativa do prólogo diante de Skip Tutorial.

Na revisão posterior solicitada pelo usuário, os leitores passaram a usar composição e controles da tela em vez de exigir nomes conhecidos ou a biografia da Tieria. Os 12 casos adicionais verificam nomes fora do catálogo, descrição alterada, ausência de identidade, remoção dos reconhecedores específicos e recusa de uma composição incompleta. As trocas são feitas no OCR de fixtures e estão identificadas como sintéticas; não comprovam renderização ao vivo de todos os heróis. Os 49 testes focados e sete testes dos alvos legados passaram; 124 observações salvas foram reconstruídas. Resultados de atributos, recibos de equipamento, remetentes e banner também leem os rótulos atuais.

O usuário autorizou nova conferência no jogo depois do prazo anterior. Na execução `20261027T121820Z_dd807e2e`, a descoberta foi renovada e o driver local foi elevado após acesso negado. FramePool 2, mouse 64 explicitamente configurado e teclado 4, em 1212 × 682. As leituras 000001/000002/000004/000007/000008 confirmaram o lobby genérico com o fundo ilustrado atual. A tecla C e um clique de navegação foram recusados por `global_frame_changed`, ambos antes de entrada; a guarda não foi relaxada. A conferência de outras telas depende de abertura manual. Não houve recrutamento, despertar, summon ou consumo. Evidências e relatório: `var/ui-readers-live/`.

A revisão genérica passou na suíte completa com **336 testes em 430,46 s**, com validações Steam/STOVE sem erros. A última leitura ao vivo 000009 continuou no lobby; não foi obtida prova ao vivo das telas de outros heróis. O driver foi desconectado normalmente e a liberação da trava/restauração do estilo da janela foram conferidas; o transporte privado também terminou. O relatório distingue os positivos reais, as alterações sintéticas de OCR e a conferência que ainda requer navegação manual.

<a id="animacao-navegacao"></a>

## Navegação com animação e variantes do pacote — 27/10/2026

A guarda de navegação passou na suíte completa com **353 testes em 430,14 s** e em 84 testes focados. Steam (135 nós) e STOVE (106 nós) validaram sem erros. Os dados extraídos foram usados para conferir composição, bindings, separação entre legenda e botão e variantes de constelação; a prova atual continua vindo da árvore e da captura.

Em `20261027T130729Z_f185d7f2`, uma referência do lobby com oito segundos de intervalo foi aceita para uma única tecla C: erro global **18,531**, acima do limite anterior 12, com painel/controle atuais e glifos das âncoras aprovados. 000009 confirmou Arby aberto depois de 000008. O classificador legado continuou `unknown`; a navegação não o promoveu artificialmente. Os testes negativos incluem escurecimento, alvo coberto, mudança de painel/janela, movimento/duplicação de controle e entrada sem papel de navegação.

A conferência também cobriu lobby → Arby → despertar de Leão → Arby → lobby e a abertura/saída do painel de nível do Arby. A primeira tentativa no texto Awaken não abriu o painel: o CSB declara o botão circular 95 × 97, separado da legenda, e o Maa forneceu a região interna atual [772,577,48,47]. A entrada nessa região abriu o despertar em `20261027T130439Z_84857abb/000003`; o selo Awaken em Leão está em posição diferente de Virgem e o leitor foi corrigido para a região da constelação, sem nome específico. Os marcadores existentes de ícones foram reutilizados, sem ampliar os `target_states` legados.

As capturas imediatamente após entrada ainda mostraram transição/origem e retornaram revisão sem confirmação; leituras posteriores comprovaram os destinos, sem repetir a entrada. Um toast sobre o cabeçalho de pinguins manteve o nível como desconhecido até desaparecer; 000012 então leu Arby 42. Duas referências expiradas foram recusadas antes de entrada. Não houve aplicação de nível/despertar, recrutamento, summon, resgate ou batalha. A sessão voltou ao lobby e terminou por desconexão normal, com estilo restaurado e trava liberada. Relatório, entradas, prova por âncora e limites em `var/animated-navigation-live/report.json`.

## Integração das telas validadas à árvore — 26/10/2026

Após a manutenção da demo, o usuário pediu concluir o mapeamento com um subagente dedicado à `ui_tree`. Todo o incremento de código foi validado offline, sem reconectar ou gerar outra captura do jogo. O transporte terminou normalmente em `agent_000305` da sessão `20261026T232625Z_eef54186`, e o observador foi invalidado como `disconnected`.

O bloco inclui equipamento do herói, popup individual de arma/artefato, seleção para Equip, prévia/segunda confirmação de Equip All, confirmação de habilidade, resultado de habilidade do artefato, resultado NPC Quick Match, resultado NPC em combate normal e lista de Arena com cabeçalho de sequência. As regiões de EXP/custo/Enhance foram corrigidas com os textos nativos salvos; ambiguidades mantêm o campo desconhecido. Equip All é navegação para prévia; Unequip All e confirmação de troca são aplicações. Next Floor do resultado normal de Abyss é navegação para preparação, com prova Floor 32→33 sem redução de energia nesse clique.

`campaign_objective_nodes` usa o OCR existente e expõe os rótulos de objetivos da preparação, com interpretação limitada de conclusão, sem Continue e elemento. `completed`, estrelas obtidas e condição global continuam desconhecidos; `stage_id` depende da identidade verificada na mesma observação. O CLEAR de três estrelas de `epi009` continua prova visual de uma unidade, não leitura automática de conquista nem planejador de estrelas. Não foram inferidos IDs internos, seis slots completos, habilitação ou seleção de materiais. Confirmações têm precedência sobre os controles do fundo.

As novas variantes de HUD manual de Arena mantiveram o teto de erro 14 e os filtros nativos. O replay Maa inclui positivos manuais 222/264 e automáticos 267/297, com negativos de preparação, confirmação, resultado, HUD escurecido/oculto e entrada em animação. A captura 226 continua desconhecida pelo contexto visual; o classificador não foi relaxado. Isso não comprova uma execução live do grafo condicional com os novos recortes.

**Verificação:** suíte completa com **209 testes passando em 256,26 s**. Depois do ajuste final de Equip All para navegação, **33 testes focados passaram em 0,87 s**. `validate`: **135 nós, zero erros**, compilação de capítulo preservada com 350 nós. O índice por operação tem 15 assuntos, com rota própria de equipamento e referência da confirmação de habilidade. A auditoria recompôs **230 observações salvas**, identificou **30 painéis adicionais** onde não havia painel operacional, preservou IDs e hashes dos arquivos de origem e teve zero erros. A contagem inclui leituras sem OCR/painel e não representa cobertura das 33 famílias, taxa de reconhecimento ao vivo nem benchmark de tokens/latência. Artefatos privados: `var/ui-tree-integration-audit.json` e `var/ui-tree-final-tests.log`.

O launcher normal e a conta desde o zero permanecem como próxima etapa: é necessário descobrir/calibrar seu próprio perfil de janela, versão e captura/entrada e validar as telas iniciais. A evidência Steam não foi promovida a validação desse cliente; naquela etapa, a autorização ampla de gastos referia-se à demo. A sessão STOVE posterior recebeu autorização própria, registrada no bloco acima.

## Herdeiro 17, estrelas e melhorias — 26/10/2026

O usuário autorizou continuar a progressão nesta mesma conta, testar equipamento e 3★ nas próximas fases e, posteriormente, usar recursos da demo conforme necessário ao objetivo. A execução `20261026T232625Z_eef54186` usou cliente 1212 × 682, FramePool 2 e PostMessage 4/4, sem fallback. As operações foram escolhidas após consulta das fontes existentes, com evidência atual e limites em `heir17-plan.json`.

`epi009` teve preparação com três objetivos e Sigret Ice na equipe, CP 506.208. Uma entrada consumiu 16 de energia, 1.012→996; `018_Finish.Clear.png` marcou os três objetivos, e `agent_000004` confirmou retorno ao mapa após histórias. Não houve Continue. O bloqueio anterior por inventário cheio em `20261026T232415Z_779607cb/live.png` não confirmou entrada: sua reserva conservadora foi mantida. A capacidade foi resolvida pelo usuário, que pediu novo início; a autorização posterior de gastos não foi usada para atribuir ao agente essa expansão manual. Não é prova de um planejador automático de 3★.

Duas aplicações unitárias de Lesser Artifact Charm no Daydream Joker equipado da Sigret confirmaram +0→+3→+7 e habilidade do artefato 1→2→3. Cada aplicação custou 17.280 de ouro; saldos 9.683.301→9.666.021→9.648.741. A primeira prévia/aplicação/resultado estão em 000043/000045/000047; a segunda, 000077/000079/000081; o popup 000085 confirmou +7. Contadores da mesma missão `guide_17_002_001`: 0/2 em 000014, 1/2 em 000061–62, 2/2 em 000114; resgate 000116. A cópia Max Up selecionada em 000035 foi removida em 000037, sem consumo; os charms foram localizados por rolagem, conforme orientação do usuário.

Muwi recebeu +1 em Leap Strike, Coldhearted Management e Wind Cutter, cada aplicação com confirmação explícita de 120 Stigma/2.000 ouro. Confirmações/resultados: 000104/000107, 000140/000143, 000149/000152. Stigma 66.166→65.806 e ouro 9.648.741→9.642.741. Missão `guide_17_003_001`: 0/3 antes, 1/3 em 000114 e 3/3 em 000159; resgate 000160 e grupo 3/5 em 000165. Abrir o menu de Sigret após o retorno não aplicou melhoria; sua tela mostrou Enhancement Complete, e Muwi foi reselecionado antes de continuar.

Três variantes de Arena foram exercitadas, uma entrada por variante e uma bandeira por entrada. Phantom CIC's Training em NPC Quick Match: preparação 000177, aviso de herói baixo 000180, vitória 000184 e missão 0/3→1/3 em 000199–200. Opponents sem Quick contra Dcry: preparação 000214, combate/HUD manual 000222, um clique de Auto 000225 e HUD de retratos/ataque 000226, vitória 000227 (+25, 557 pontos), retorno 000231 e missão 1/3→2/3 em 000240–241. NPC sem Quick contra Rose Apostles Worship Service: preparação rápida 000253, alternância única 000255 e Start/quick=false em 000256, HUD manual 000264, um clique Auto 000266, HUD automático/ataque 000267, vitória 000268, retorno 000271 e missão 2/3→3/3 em 000280. Resgate 000281; grupo 4/5 em 000284. Bandeiras 5/5→4/5→3/5→2/5. A causa do delta zero de Arena na execução anterior permanece desconhecida; este teste confirma crédito nos estados observados.

As guardas de Auto recusaram HUD ainda carregando/variante não calibrada antes de enviar entrada. Os dois cliques exploratórios foram escolhidos após inspeção positiva do HUD manual com três habilidades e observação recente, com um clique máximo e prova posterior; não foram toggles repetidos. A calibração adicional da árvore é verificada separadamente, sem retroatribuir reconhecimento automático a esses cliques. Nenhum novo início foi usado só para gerar fixture.

Abyss: grupo 17 em 4/5 e requisito 31/40 confirmados em 000284. A preparação 000292 identificou Floor 32, equipe própria de CP 359.632 e custo 10/996. O combate manteve Auto já ativo (000297); CLEAR Floor 32 em 000298 e energia 986. Next Floor (000300) abriu a preparação Floor 33 em 000301, mantendo 986 e custo de entrada 10: nessa variante o controle navega, sem iniciar nem consumir. A tentativa de Start 33 em 000303 não confirmou combate; 000304 mostrou `Maintenance`, relógio 00:00:00 e Reconnect/Patch Preview. O usuário informou o fim da demo e mudou o foco para integração offline; desconexão normal em 000305. Não houve nova tentativa, Reconnect, derrota presumida ou sucesso de Floor 33. Abyss 40 e o fechamento do grupo 17 ficaram pendentes, distintos da conclusão das quatro outras missões.

## Equipar, desequipar e Equip All — 26/10/2026

Execução privada `20261026T231721Z_98aecbed`, cliente 1212 × 682, FramePool 2 e PostMessage 4 para mouse/teclado, sem fallback. O usuário autorizou o teste nesta conta, incluindo o controle de equipar todos. Fontes consultadas antes das entradas: `equip_base.csb`, `unit_detail.csb`, `item_detail.csb`, bindings e opções. Os controles `center_equipment/btn_equip` e `btn_unequip` da composição de herói são distintos da aplicação de candidatos em `equip_base/n_side_base/btn_change`; nomes do pacote não foram tratados como seletores de runtime.

Na Sigret, `agent_000015` preservou CP 106.177, atributos e conjuntos Destruction/Penetration. O popup 000018 identificou a arma Hellish Essence Orb, nível 85, +15, ataque 500, ataque 17%, velocidade 8, chance crítica 4%, dano crítico 14% e score 80. Uma remoção confirmou slot vazio, CP 77.532 e perda do conjunto Destruction em 000021. A arma sem retrato de equipado foi localizada na lista rolada; seus atributos foram conferidos em 000035. Equip confirmou o retorno dos atributos, dos conjuntos e do CP 106.177 em 000038.

Equip All com seis slots preenchidos informou `There is no better Equipment.` em 000041. Um Unequip All confirmou os seis slots vazios, CP 25.832 e artefato preservado em 000045. Equip All abriu a prévia 000048 com seis candidatos e CP 106.177; Change abriu uma segunda confirmação em 000051. A confirmação única restaurou slots, níveis, atributos, conjuntos e CP em 000054; 000055 preservou a leitura seguinte. O ouro permaneceu 9.652.261 durante o teste. Não se generaliza gratuidade para outros estados ou perfis.

Limites: validação unitária por primitivas com conferência visual, sem IDs internos de instância, reconhecedores novos, executor genérico ou prova de incremento de missão de equipamento. CP isolado não identifica os itens: o vínculo usou slot, ícone, nível, atributos da arma e composição final. A confirmação de um clique pode chegar depois da primeira captura; as releituras evitaram repetir a ação por uma imagem transitória. Evidência estruturada: `var/runs/20261026T231721Z_98aecbed/equipment-validation.json`. Nenhum combate ou melhoria de item foi usado para validar este bloco.

<a id="combate-e-arvore"></a>

## Combates unitários e integração operacional na árvore — 26/10/2026

O usuário autorizou fechar a validação de combate de Abyss/Arena e depois integrar o bloco mapeado à `ui_tree`; durante a partida também pediu a ativação e a capacidade reutilizável de Auto. Execução de combate `20261026T213404Z_9a757f4e`, cliente 1212 × 682, FramePool 2, mouse/teclado PostMessage 4, sem fallback. O plano privado delimitou uma entrada de Abyss 31, até 10 de energia, e uma de Arena normal, até uma bandeira; sem recarga, replay ou resgate de missão. A recompensa de batalha decorreu da conclusão, sem clique de coleta de missão/grupo.

| Unidade | Evidência `agent_*.json/png` | Resultado |
|---|---|---|
| Contadores e preparação de Abyss | 000013, 000020, 000023 | Linhas completas das duas missões e seus contadores iniciais registrados no relatório privado. Abyss Floor 31, equipe própria preservada, custo de 10 de energia e saldo suficiente. |
| Início/combate/resultado | 000025, 000027, 000028 | Um Start; combate reconhecido e Auto já ativo. CLEAR Floor 31, recompensa e consumo de 10 de energia confirmado. Next Floor não acionado. |
| Retorno e avanço | 000030, 000031, 000044 | Back retornou à lista, o próximo andar ficou disponível e a missão do mesmo ID incrementou uma unidade, ainda incompleta. |
| Arena Opponents | 000059, 000062, 000065 | Modalidade de adversários da Rookie Arena, não NPC Challenge. Linha selecionada, Challenge abriu a preparação; custo de uma bandeira, equipe própria preservada. |
| Confirmação intermediária | 000067, 000068, 000070 | Um Start abriu Low Level Hero. Confirm prosseguiu com a mesma entrada; Do Not Display não acionado. A estrutura candidata foi consultada em `pvp_unequipped_hero.csb`; legenda de layout era placeholder diferente. |
| Auto e vitória | 000072, 000073, 000075, 000076, 000077 | HUD manual observado; um clique no Auto global mostrou HUD automático e ataque sem selecionar habilidade. VICTORY, +25 pontos. Nenhum novo Start. |
| Resultado, retorno e contagem | 000079, 000081, 000098, 000101 | Confirm retornou à lista; consumo de uma bandeira conferido visualmente, pontos e contador semanal de partidas incrementados. A missão de Arena não incrementou, com linha completa e conferência visual. |

**Divergência preservada:** `mission-comparisons.json` confirma delta +1 de Abyss e delta zero de Arena entre as mesmas missões/grupo. Vitória em Opponents/Rookie, custo e retorno estão validados; sua equivalência com `pvptype=normal` do critério e a causa do não crédito não foram provadas. Não declarar essa missão concluída nem executar outra partida para forçar o contador. NPC/Quick Match seguem sem validação de crédito. O log posterior tinha contexto `pvp_sa_lobby` com idade explícita, tratado apenas como pista auxiliar.

Houve bloqueio de Go de Arena por linha parcialmente visível na releitura, sem entrada; o acesso foi feito pelo lobby. Uma primeira troca de grupo retornou revisão e conservou o grupo 16; a leitura posterior identificou essa origem e a troca seguinte confirmou o 17. Não foram usados contadores de um grupo diferente. A execução terminou no lobby e desconectou normalmente.

`operational_ui.py` acrescenta à árvore os painéis e controles calibrados, com proveniência por campo, sem novo loop de captura/OCR: Otherworld hub/preparação/resultado; Abyss hub/andares/preparação/resultado; Arena hub/listas/preparação/aviso/resultado; comparação de equipamento; melhoria de item; quantidade e habilidades. O par nativo remover/detalhes expõe seleção de formação, mantendo integrante e slot desconhecidos. `enabled`, IDs de instância, seleção de candidato e campos sem prova não são inferidos. A projeção textual é derivada da árvore; o classificador legado pode permanecer unknown. [Contrato e comandos](architecture.md#operacoes-e-auto).

Auto usa correspondências positivas de HUD automático/manual, sem inferir pelo ângulo das setas ou pela ausência de um marcador. Capturas nativas de desligado/ligado, transição desconhecida e negativos de preparação, confirmação e resultado passaram; versões escurecidas e HUD encoberto foram negativas nos testes. O comando `battle-auto on` é idempotente quando ligado, recusa desconhecido e usa um grafo Maa com um clique máximo quando desligado. O grafo de conclusão ganhou a mesma guarda condicional. A ativação manual ao vivo e o reconhecedor foram validados; o novo grafo condicional não foi exercitado em um terceiro combate. Seus resultados tardios ou variantes de HUD não calibradas não são sucesso presumido.

Na conexão da integração `20261026T221340Z_80963d03`, Auto foi recusado fora de combate antes de enviar entrada. As leituras 000011, 000014, 000017, 000020, 000023, 000026, 000029, 000035, 000038, 000041 e 000047 conferiram hubs, andares, custo, preparação, formação e listas de Arena; as leituras conhecidas sem inspeção explícita retornaram `image.required=false`. A lista preservou um andar concluído selecionado ao abrir; o controle Move to Floor levou ao disponível, confirmando que o cartão do hub não basta para determinar a seleção. Nenhuma segunda batalha ou troca de equipe. Opponents restaurado, lobby e desconexão confirmados em 000049–000050.

O corpus privado reconstrói 35 observações sem recapturar: 34 painéis identificados e um negativo de Orbis, com 17 variantes operacionais. O par de formação passou em dois positivos e cinco negativos nativos. Nomes/pontos de Arena foram separados após a conferência ao vivo: pontuação não é candidato de adversário, e linhas quebradas permanecem fragmentos sem ID. A versão final foi reaplicada às evidências e testada. Referências de capturas, comparações e hashes finais ficam nos relatórios privados; os templates pequenos e sua proveniência permanecem no catálogo existente. Recursos e limites do percurso longo continuam separados deste escopo unitário.

Verificação final: **187 testes passaram em 265,26 s**, incluindo adaptadores, ancestralidade, ambiguidade, contadores, overlays, máscara, guardas de Auto e reconhecimento Maa offline. `validate`: **135 nós, zero erros**; capítulo compilado com 350 nós, mantendo seus limites anteriores de inícios/energia. Onze fingerprints de código, reconhecimento, pipelines e testes foram conferidos após a suíte. A auditoria verificou 102 respostas/71 imagens de combate e 49 respostas/24 imagens de integração, sem divergência de identidade e com desconexões confirmadas. As 11 leituras operacionais sem inspeção explícita dispensaram imagem na resposta, sem benchmark de economia. O índice tem 14 assuntos, 33 famílias e 104 fontes inventariadas; consultas de Auto/Abyss/NPC passaram, sem modificar o banco privado. Links canônicos conferidos. Relatório privado: `var/runs/20261026T213404Z_9a757f4e/combat-and-tree-analysis.json`.

## Consulta de fontes antes das operações — 26/10/2026

Na validação inicial, `tools/query_sources.py` passou em dez testes offline: roteamento por operação e pelas 33 famílias, composição além do shell, ausência de extração local, classes/linhas parcialmente interpretadas, chave física diferente do ID, truncamento, confinamento de caminhos, identidade/hash divergentes, referências literais, índice ausente e abertura SQLite somente leitura. O índice então resolvia 83 caminhos únicos do pacote, todos presentes no inventário privado. Sete consultas reais cobriram personagem, equipamento, família, botão CSB, entrada de batalha, asset e chave de texto. O tamanho e o instante de modificação de `audit.sqlite` permaneceram iguais; essa validação offline não conectou janela nem enviou entrada. Os testes também verificam recusa de escrita no banco e preservação de seu hash no fixture.

`validate`: 125 nós e zero erros; não houve alteração no reconhecimento, pipelines ou `ui_tree`. O índice encaminha às fontes e não converte referências em seletores nem declara os novos mapeamentos concluídos. Resultado privado em `var/source-query-validation.json`; uso e limites em [consulta por operação](assets.md#consulta-por-operacao). A ordem atual registrada em AGENTS.md é concluir o mapa operacional de famílias/capacidades compartilhadas e depois integrar seus novos campos/controles à árvore canônica.

<a id="abyss-arena"></a>

## Abyss e Arena: seleção, custos e retorno — 26/10/2026

Execução privada `20261026T210140Z_aa3f45d7`, cliente 1212 × 682, FramePool 2, mouse/teclado PostMessage 4, sem fallback. `doctor` redescobriu a janela; a sessão JSONL consultou a árvore existente, abriu imagens na calibração e usou observações recentes para pontos. O plano limitou o escopo a menus, seleção, preparação e retorno, com zero entradas em partida, gastos, refresh, Purify, resgates ou trocas de equipe. A alternância unitária de Quick Match foi registrada com restauração obrigatória.

| Unidade | Evidência `agent_*.json/png` | Resultado e limite |
|---|---|---|
| Entrada de Abyss | 000008, 000011, 000015, 000019 | Categorias Normal, rolagem horizontal e hub Abyss confirmados; normal disponível e Challenge Mode bloqueado. Lista abriu no próximo andar disponível. |
| Andar bloqueado | 000022, 000025 | Selecionar o próximo andar bloqueado exibiu Cannot proceed e Move to Floor; esse botão voltou ao disponível, sem abrir combate. |
| Preparação de Abyss | 000027–000031, 000039–000043 | Select Team abriu `battle_ready`; identidade Floor 31, custo atual 10 de energia, equipe própria do modo e ausência de apoiadores lidos. Retorno e uma reabertura conservaram custo e CP; Start não acionado. Os nomes de todos os integrantes não foram ligados automaticamente. |
| Andar concluído | 000034, 000037 | Conquered e recompensa já recebida distinguidos do disponível; Replay apenas observado. Move to Floor mudou de posição e voltou ao andar disponível. |
| Hub de Arena | 000058, 000098 | Rookie Arena e bloqueios de Rank 60 para World Arena/Tournament lidos. A primeira leitura tinha fundo ainda carregando; a posterior confirmou a composição completa. Draft e modos bloqueados não foram abertos. |
| Arena normal | 000062, 000065, 000068, 000071 | Sem seleção, Challenge estava cinza; selecionar a linha a marcou e habilitou o botão. Challenge abriu preparação com adversário correspondente, equipe de Arena e Start com custo de uma bandeira. Retorno conservou 5/5. |
| NPC Challenge | 000074, 000077, 000080 | Aba/lista lidas, Phantom CIC's Training selecionado e preparação aberta. O título corresponde ao candidato estático `npc_06`; adversário e quatro sprites conferidos. Quick Match estava ativo, custo de uma bandeira e limite diário visíveis. Nenhuma partida. |
| Variante rápida e restauração | 000083, 000086 | O seletor lateral alternou Quick Match para Start e voltou a Quick Match. Custo, bandeiras, CP e limite diário conservados. Não usar esse teste como prova de resultado ou incremento em missão. |
| Reabertura de NPC e saída | 000089, 000092, 000095, 000098, 000100–000102 | Seleção do NPC persistiu na volta; uma reabertura confirmou mesmo título, custo e configuração rápida restaurada. Retorno ao hub e lobby, desconexão normal. |

**Limites:** o mapa e a preparação de Arena continuam `unknown`; o estado genérico de preparação de Abyss não comprova por si só andar ou integrantes. Não houve campos novos na `ui_tree`, reconhecedores, pipelines ou habilitação de executores. Três pedidos foram bloqueados antes da entrada por mudança entre lobby/ocioso/desconhecido; novas observações e restauração do lobby permitiram seguir, sem relaxar guardas. Não foram testados vitória/derrota, avanço de andar, cooldown, boost, recompensas ou incrementos das missões. O critério estático aceita normal/NPC, mas a contagem de Quick Match não foi exercitada.

As fontes e os candidatos estão em [assets.md](assets.md#abyss-arena-fontes) e no índice por assunto. `wnd/dungeon_hell_tower.csb` sozinho não contém os controles da lista; `dungeon_hell.csb` completa a composição. `pvp_npcbattle_s2` fornece candidatos, enquanto duas tabelas antigas vazias não provam ausência de NPC. `KEY_4` é um binding estático de Arena e continua fora das teclas aceitas pela primitiva; nenhum atalho 4 foi enviado. Proveniência e achados de conta ficam em `static-source-audit.json` e `mapping-analysis.json` na execução privada.

A auditoria conferiu 101 respostas e 82 imagens referenciadas, com uma identidade de janela/cliente e métodos 2/4/4, sem divergências de pedido, arquivo ou árvore/observação. Vinte comparações de texto/estado passaram, incluindo custo repetido, saldos, configuração restaurada, retorno e bloqueios sem entrada; seleção/identidade visual permanecem conferências separadas. O índice tem 13 assuntos, 33 famílias e 102 fontes únicas presentes no inventário; cinco consultas reais passaram sem modificar `audit.sqlite`, preservando os assuntos anteriores. Onze testes da consulta passaram; `validate`: 125 nós, zero erros; links locais conferidos. As mudanças desta unidade foram de referências e documentação; a suíte completa de 172 testes do bloco anterior não foi repetida.

<a id="mapeamento-reversivel"></a>

## Remoção, equipamentos e habilidades: mapeamento reversível — 26/10/2026

Execução privada `20261026T201921Z_d656a3d9`, cliente 1212 × 682, FramePool 2, mouse e teclado PostMessage 4, sem fallback. As fontes foram consultadas antes das operações, e `mapping-plan.json` limitou o teste a remoção/reinserção e prévias sem confirmar gasto. O cliente JSONL conferiu pedido, argumentos e arquivo; as transições abaixo foram confirmadas por tela de destino, não apenas pela aceitação da entrada.

| Unidade | Evidência `agent_*.json/png` | Resultado e limite |
|---|---|---|
| Categorias e Otherworld | 000004, 000007, 000017, 000023, 000027, 000030 | Normal/Seasonal e rolagem horizontal lidos; retorno das categorias reinicia a posição horizontal. Um clique errado abriu o menu Abyss, depois houve retorno e abertura correta de Otherworld. Nenhuma batalha ou nova entrada consumidora. |
| Remover/reinserir Muwi | 000030, 000033, 000036, 000039, 000042 | Remoção única confirmou slot vazio; `+` da lista abriu destinos; `+` roxo vazio reinseriu Muwi. Brieg à frente, Furious e Sigret preservados, CP original restaurado. Identidade visual, sem ID interno de instância. |
| Artefato/material/prévia/limpeza | 000051, 000054, 000057, 000060, 000063 | Daydream Joker e um Lesser Artifact Charm: prévia de EXP, nível, atributos e custo lida; clique no slot reservado limpou a seleção e restaurou quantidade, EXP e custo zero. Enhance não acionado. Cópias “Max Up” apenas observadas. |
| Seleção das três habilidades | 000071, 000074, 000077, 000080 | Navegação abriu Skill Enhance; seletores mostraram Leap Strike, Coldhearted Management e Wind Cutter, com custos atuais. Botão consumidor Skill Enhancement não acionado. |
| Candidato de equipamento | 000089, 000092, 000095 | Arma não equipada selecionada em Manage Equipment; comparação alterou CP de prévia, e Enhance abriu a melhoria. Change não acionado. |
| Quantidade de pó/prévia/limpeza | 000098, 000101, 000104 | Pó abriu Select Ingredients; quantidade um foi selecionada e a prévia lida. Remover do slot restaurou quantidade, EXP e custo zero. Enhance não acionado. |
| Descartar troca e retornar | 000107, 000110, 000113, 000116, 000124–000126 | Reset descartou candidato; equipamentos e CP originais de Muwi, equipe e CP da formação foram relidos. Lobby confirmado, desconexão normal. |

Os incrementos de EXP das duas prévias diferiram dos valores brutos do pacote; não houve atribuição de causa nem criação de uma fórmula. Os valores e comparações ficam no relatório privado. `item_equip_upgrade.db` foi identificado como receita de reforja, e o índice passou a separar esse assunto da melhoria comum. A definição de Muwi foi localizada em `character_player_grade3.db`, ausente da tabela player principal; as variantes player e skill agora têm rotas explícitas. O vínculo de receita em `skill_upgrade` permanece desconhecido quando há custos iguais.

**Limites:** as telas novas continuam `unknown` e exigiram inspeção visual e observações recentes; não há reconhecedores novos nem campos novos na `ui_tree`. Uma leitura durante a animação do gerenciador foi descartada em favor da tela estabilizada. Uma tecla Escape sem estado/observação foi recusada antes de enviar entrada; o retorno usou nova observação. Não foram confirmados upgrades, trocas de equipamento, resgates, compras, recargas ou combates. Seleção e limpeza não validam consumo, incremento de missão, repetição curta ou todas as variantes de item/herói. Relatório e auditoria de identidade em `mapping-analysis.json` no diretório privado da execução.

A auditoria conferiu 125 respostas, 94 imagens referenciadas e a identidade da árvore/observação, sem divergências; quinze comparações de texto/estado confirmaram prévias, limpeza, CP, retorno e desconexão. As conferências visuais de identidade/posição permanecem separadas dessas comparações. O índice atualizado tem 11 assuntos, 33 famílias e 93 fontes únicas presentes no inventário; seis rotas e três consultas de fonte/referência passaram sem modificar `audit.sqlite`. Onze testes específicos passaram, incluindo variantes player, distinção EXP/reforja e propagação das lacunas para a consulta por família. A suíte completa posterior passou com **172 testes em 192,95 s**. Os controles estáticos anteriores foram preservados; somente o registro de remoção manual foi atualizado, sem habilitar runtime. Links locais conferidos; `validate`: 125 nós, zero erros.

<a id="otherworld-e-formacao"></a>

## Otherworld Breach, formação e leitura dos objetivos — 26/10/2026

Execução privada `20261026T192147Z_72af049c`, cliente 1212 × 682, captura FramePool 2, mouse e teclado 4, sem fallback. Após intervenções manuais no começo, o usuário confirmou que havia parado de operar a janela; as etapas abaixo usam observações novas. O cliente JSONL conferiu identidade do pedido, argumentos e arquivo de evidência. Não houve alteração em reconhecedores ou pipelines nesta calibração.

| Unidade | Evidência `agent_*.json/png` na execução | Resultado observado |
|---|---|---|
| Controles da formação | 000048, 000051, 000057, 000063 | Seleção mostrou remover/detalhes e setas; Brieg trocou de posição com Árbitro Vildred. A lista e o botão `+` são etapas distintas. |
| Substituições e formação final | 000067, 000076, 000079, 000082 | Furious substituiu Árbitro Vildred; Muwi substituiu Tieria; Brieg à frente e Sigret preservada. CP e nível foram apenas sinais auxiliares. A instância de Brieg nível 1 não foi usada. |
| Início único / combate | 000083–000086 e `otherworld-plan.json` | Normal, `hcsc001`; custo observado 1/1 Spectral Core antes e 1/0 depois. Um Start enviado, combate e portal de recompensa observados. Sem recarga, compra, repetição ou início da próxima dificuldade. |
| Resultado e retorno | 000089, 000091 | Clear Reward e seis equipamentos de recompensa; Lobby retornou ao estado reconhecido. Os botões Next Difficulty/Try again não foram acionados. |
| Missão e resgate | 000008, 000093–000101 | Contador passou de 0/1 para 1/1, Receive ficou disponível, houve um resgate e Received Reward, grupo passou de 4/5 para 5/5; marca de resgate da tarefa conferida visualmente após rolar. Recompensa final do grupo não resgatada. |
| Três objetivos da próxima fase | 000104, 000107, 000108 | Identidade Hidden Plan/Secluded Laboratory e três textos iguais ao catálogo de `epi009`. Retorno ao mapa, sem combate, escolha de equipe ou reparo de fases antigas. Não prova conquista de 3★. |
| Retomada das famílias | 000115, 000116, 000118, 000121 | Cinco tarefas do grupo 17 lidas em regiões sobrepostas, com linha completa antes de aceitar contador. Nenhuma melhoria, Arena ou Abyss executados pelo agente. |

**Limites encontrados:** o estado genérico `battle_ready` não identifica os integrantes/slots nem o alvo de uma troca. O corpo animado de um personagem pode reprovar a guarda de compatibilidade da primitiva por coordenada; ela não foi relaxada. O arraste enviado não demonstrou troca. Uma tentativa de `hold` de 100 ms foi recusada por exigir no mínimo 300 ms, sem entrada; as trocas efetivas usaram cliques. Esses casos não são prova de falha geral do mouse 4.

As telas de combate e recompensa específicas de Otherworld permaneceram `unknown` e foram operadas por pontos escolhidos em imagens recentes, com nova observação a cada etapa. A entrada aceita não foi tomada como resultado: a confirmação veio do Clear Reward, do retorno e do contador da missão. O resgate inicialmente retornou `needs_review`; a leitura posterior encontrou Received Reward, sem novo clique de resgate. Depois da rolagem, o OCR leu `0therworld` em uma captura e não vinculou a linha ao catálogo; o tick foi validado visualmente, sem inventar um nó automático. A comparação automática do incremento usa as leituras anteriores em que o título foi vinculado corretamente.

Uma abertura pontual de Orbis não confirmou destino; após nova leitura do lobby ocioso, restauração e G de 100 ms confirmaram o painel. A conexão terminou normalmente no lobby e invalidou o observador como `disconnected`. Reconhecimento/pipelines não foram alterados; a última suíte completa anterior permanece separada. Relatório, comparação e auditoria das fontes em `otherworld-analysis.json`, `otherworld-counter-comparison.json` e `formation-static-audit.json` no diretório privado da execução.

Verificação do registro: 122 arquivos de resposta tiveram ID, argumentos e caminho conferidos; a comparação automática confirmou incremento de uma unidade; as três strings de objetivo coincidiram com o catálogo; os cinco contadores do grupo seguinte foram lidos em linhas completas. Os sete controles estáticos existentes foram preservados, dez candidatos de formação foram acrescentados sem habilitar runtime, e os links locais dos quatro documentos passaram. `validate`: 125 nós e zero erros. Não houve nova suíte completa, pois as alterações foram de referências estáticas e documentação.

## Base operacional concluída — 26/10/2026

A meta [ALE-179](https://linear.app/akxl/issue/ALE-179) fecha a base operacional de navegação, preparação e leitura textual. Famílias de missão ficam para ALE-185. O usuário informou que desativou manualmente os avisos da demo e dispensou a ocorrência positiva neste fechamento; a revalidação quando reaparecerem fica em [ALE-186](https://linear.app/akxl/issue/ALE-186), sem reativá-los. As seções abaixo desta são registros históricos dos incrementos, com as limitações existentes em cada momento.

A execução final `20261026T163700Z_febc21e9` completou **10 ciclos, 133 comandos e uma conexão persistente**, em 231,527 s, sem abrir imagens no modelo ou solicitar imagem de exceção. Cada ciclo confirmou a rotina nativa lobby → Orbis → lobby, G → Orbis, seleção explícita de Heir quando o guia abriu em Diary, leitura de grupo e missões pela árvore, cinco consultas ao snapshot, Esc → lobby e uma das outras cinco hotkeys com retorno. A preparação inicial e final confirmou Public/Guild desligadas; nenhum nó de alternância de checkbox foi executado. Não houve visita à terceira aba de notificações, chat enviado, batalha iniciada, gasto ou resgate. O encerramento confirmou lobby, saída normal do processo, observador invalidado como `disconnected` e restauração do estilo original da janela.

Perfil medido: cliente 1212 × 682, captura FramePool 2, mouse 4 e teclado 4, sem fallback; teclas e os cliques de navegação calibrados usam ações nativas de 100 ms. As **50 consultas** mantiveram o mesmo ID da observação e acrescentaram **zero capturas, reconhecimentos ou publicações**. Usaram `--max-age-ms 5000` somente para leitura; idades observadas: 764–1269 ms. O padrão continua em 500 ms e ações exigem nova observação. A contagem instrumentada da execução foi 235 capturas do driver, 307 reconhecimentos/publicações e 50 cache hits; ela não contabiliza todas as capturas internas do Maa.

| Medição por tipo de pedido | Observações (21) | Snapshots (50) | Ações (62) |
|---|---:|---:|---:|
| Tempo de pedido p50 / p95 | 1086 / 1415 ms | 18 / 23 ms | 1715 / 5516 ms |
| JSON completo de referência, UTF-8 compacto | 1.063.417 bytes | 2.331.661 bytes | 34.742 bytes |
| Resposta textual do agente, UTF-8 compacto | 197.094 bytes | 475.163 bytes | 351.867 bytes |

As leituras observadas reduziram o texto em 81,47%, e snapshots em 79,62%. Nas ações, a resposta com árvore e eventos é maior que o recibo antigo da ação; não se reivindica redução para essa categoria. O baseline usa o resultado completo de cada comando, ou o snapshot completo quando não há resultado. São tempos de pedidos de um percurso programado, sem inferência/decisão do modelo; não são medição de tokens, cobrança, FPS ou desempenho de campanha. O reconhecimento somou 128,59 s de parede e 593,48 s de CPU do processo (bibliotecas paralelas); a publicação instrumentada somou 275 ms, sem incluir gravação em disco. Nenhuma das 133 respostas perdeu eventos; o export final consultado desde sequência zero indica histórico truncado, conforme o buffer limitado a 64 eventos.

**Lobby ocioso (ALE-180):** preservadas as duas âncoras noturnas e acrescentadas duas diurnas, ambas com MAE ≤ 10 e reconhecimento pareado. O matcher valida os pixels dos candidatos já filtrados pelo Maa antes de escolher a variante; não recupera candidatos rejeitados pelo reconhecedor. Replay atual: 54 casos, oito positivos (noturno e sete amostras diurnas) e 46 negativos, incluindo demais telas, escurecimentos e oclusão. A execução final entrou deliberadamente em `lobby_idle` e confirmou a restauração pelo pipeline, sem imagem no modelo. Não se generaliza para toda iluminação ou sobreposição.

**Retorno do Orbis (ALE-181):** o nó de saída exige o conteúdo Heir observado, além do estado Orbis, e estabilidade Maa de 400 ms, timeout 3000 ms. Open/Back têm até duas tentativas guardadas pelo estado reconhecido; a conclusão exige lobby observado. Os dez percursos finais concluíram, incluindo uma repetição delimitada de `Orbis.Open`; nenhum comando terminou em falha. Isso não transforma envio aceito em conclusão nem autoriza retry de operações consumidoras.

**Preparação (ALE-182):** caixas principal e individuais usam seus estilos próprios com fidelidade MAE ≤ 6; estado desconhecido/ambíguo impede ação. Public/Guild exigem categoria correspondente, com seleção e saída delimitadas e nova leitura. A preparação inicial/final foi idempotente: notificações já desligadas, sem alternância ou terceira aba. A ausência de avisos foi observada. Os testes cobrem identificação de aviso/confirmador conhecido e recusa de desconhecido, mas não substituem a ocorrência positiva ao vivo adiada pelo usuário para ALE-186.

**Hotkeys (ALE-183):** a configuração de teclado do jogo foi consultada sem modificar bindings. Tab → quick menu, G → Orbis, C → heróis, O → opções, 1 → mapa de episódio e 3 → categorias de batalha tiveram origem/destino confirmados no jogo, com retorno por Esc ou Tab para fechar quick menu. As cinco últimas telas do percurso rotativo foram exercitadas duas vezes cada; G/Esc também em todos os ciclos. Marcadores pareados diferenciam quick menu, opções, heróis e categorias (Normal/Seasonal); essas telas não comprovam fase ou custo. A validação vale para esta configuração e perfil, não para Esc em qualquer diálogo. Fontes: `data/input/hotkeys.json` e `var/hotkeys-100ms-live.json`.

**Verificação final (ALE-184):** 129 testes passaram em 201,74 s, incluindo replay com Maa real sobre fixtures privadas, guardas, transporte persistente, candidatos de template, checkboxes, menus, teclas e avisos conhecidos/desconhecidos. `validate`: 125 nós e zero erros; a compilação estática de campanha permanece separada da navegação ao vivo. Evidências privadas: `var/base-operational-tests-complete.log`, `var/base-operational-10-cycles.json`, `var/base-operational-audit.json` e os 133 `agent_*.json` da execução final; 30 frames foram preservados com hashes para auditoria, sem serem abertos no modelo.

As tentativas anteriores permanecem arquivadas e não entram nos números de sucesso. Elas expuseram destinos não atingidos após entrada aceita, retorno incompleto e a abertura em Diary em vez de Heir. Uma tentativa teve associação incorreta de pedidos no cliente de medição e foi descartada por inconsistência de identidade; o cliente final confere IDs e diretório de evidência por pedido. Os ajustes finais usam ações nativas de 100 ms, conteúdo observado antes de sair, limites finitos e confirmação de destino. Não se atribui uma causa exclusiva a todas as falhas anteriores.

## Retrospectiva da meta ALE-179 — 26/10/2026

Análise solicitada pelo usuário antes da próxima meta, cruzando tentativas preservadas, layouts/DBs extraídos, leitor CSB e documentação da versão MaaFramework 5.14.3. As medidas e propostas abaixo não acrescentam validação ao vivo nem iniciam famílias de missão.

**Diagnóstico:** o principal retrabalho veio da ordem da integração. O percurso longo começou enquanto entrada, reconhecimento e transições ainda recebiam ajustes. Cinco tentativas com intervalos próprios terminaram antes dos dez ciclos: quatro em pipelines sem destino confirmado (tentativas 1/3/4/6) e uma por presumir grupo Heir ao abrir Diary (5). Somam 273,635 s de execução registrada, sem contar calibração, correções ou recuperação. Outra tentativa foi descartada por erro de identidade no cliente de medição; seus timestamps reutilizados não são uma medida independente. Esses números não sustentam uma porcentagem de tempo recuperável da meta inteira.

| Ponto | Evidência e possibilidade de antecipação |
|---|---|
| Hotkeys | `db/key_binding.db`, em `data/input/hotkeys.json`, já fornecia tecla, contexto, evento e caminho do controle, inclusive Tab de abrir/fechar e exclusão de combate. Permitiria preparar a matriz origem/destino/retorno antes do teste. Não comprova overrides da conta ou funcionamento da entrada. |
| Aba do Orbis | `data/layouts/growth_masterbook.json` contém ramos daily/weekly, growth guide, challenge e outros. Abrir o painel não seleciona um ramo por contrato. O erro da tentativa 5 era uma suposição evitável do roteiro; observar/selecionar Heir deveria ser pré-condição desde o início. O layout não informa a aba ativa da conta. |
| Notificações | `chat_filter.layout.json` distingue Public, Clan, Keyword, checkbox principal e individuais. Isso permite planejar guardas de categoria e uma matriz por tipo de caixa. Não comprova que um clique trocou de aba nem a aparência renderizada de cada estado. |
| Fidelidade de variantes | A amostra `62_lobby_idle_day.png` expôs a escolha do candidato de maior correlação antes da validação de pixels. Era um defeito do adaptador, evitável com o caso de teste de duas variantes antes de ampliar a calibração; não faltava dado do jogo. |
| Entrada e conteúdo pronto | As falhas de Tab, abertura e retorno pediam um diagnóstico isolado de entrada/duração/destino antes da repetição longa. A duração eficaz de 100 ms e as condições de estabilidade precisaram de prova no jogo. Reconhecer um cabeçalho cedo não comprova conteúdo pronto. |
| Cliente de medição | Helpers persistentes reutilizaram conexão/relatório anteriores. Esse erro é do nosso instrumento, independente do jogo e dos layouts. Um teste curto de correlação pedido→resposta→diretório, com estado isolado por execução, deveria preceder o benchmark. |
| Ordem dos testes | Suítes completas de cerca de 3–4 minutos foram executadas durante a calibração. Uma passou com 108 casos, mas a amostra nova ainda expôs a falha entre variantes. Um replay focado após cada ajuste, preparação/ida-volta curtas e só então a suíte completa e dez ciclos reduziriam integração prematura. Não foi provado que concorrência de testes causou falhas de entrada. |

**Lacuna do extrator confirmada nesta retrospectiva:** o leitor `inspect_csb_layout.py` da sessão de origem exportava textura normal/pressionada apenas para a classe `Button`. A ferramenta ampliada deste repositório e a cobertura posterior estão em [assets.md](assets.md#cobertura-da-extracao). O resumo de `chat_filter` contém oito `CheckBox` e 12 `ImageView`, mas não suas texturas específicas. A releitura somente leitura de `wnd/chat_filter.csb` no pacote confirmou referências a `img/cm_checkbg.png` e `img/cm_checkicon2.png`; são candidatos, sem associação completa aos estados ou calibração visual nova. O hash e as referências estão em `var/retrospective-pack-references.json`. A ação proposta é completar a extração das classes necessárias à operação, incluindo estados visuais e vínculos de textura, antes de procurar controles apenas na tela. Não se demonstrou que isso eliminaria os dois estilos renderizados ou permitiria usar as texturas sem transformação.

Um exemplo adicional de cuidado semântico: o arquivo local extraído de `db/option.db` traz campos `item_special_value`, `item_id`, `grade_rate` e registros de equipamento. Seu nome não o transforma no banco de configurações de teclado. É evidência de risco de classificação pelo nome, não uma causa demonstrada de falha nesta meta.

**O que a documentação permitia antecipar:** o [protocolo Maa 5.14.3](https://github.com/MaaXYZ/MaaFramework/blob/v5.14.3/docs/en_us/3.1-PipelineProtocol.md) oferece `LongPressKey` com duração, espera de estabilidade, composição de reconhecimentos e limite `max_hit`. Isso permitia preparar um diagnóstico nativo curto. A especificação não fornece a duração correta para Epic Seven. Os [métodos Win32](https://github.com/MaaXYZ/MaaFramework/blob/v5.14.3/docs/en_us/2.4-ControlMethods.md) documentam compatibilidade variável, portanto não bastava o Maa aceitar o envio. A escolha final de 100 ms, regiões e marcadores veio das observações locais. Não há base para atribuir toda falha anterior à mesma causa.

**Calibração que continuava necessária:** iluminação diurna/noturna, feixes animados, composição/fundo das caixas, transformação de coordenadas locais até o cliente, aba ativa, configurações da conta e latência efetiva. O pacote descreve possibilidades. Texturas, visibilidade declarada e caminhos internos não são estado vivo, seletor de acessibilidade ou coordenada pronta. No lobby, colher algumas amostras temporais antes de escolher as âncoras poderia reduzir a troca posterior de recortes, mas não dispensaria o teste visual.

**Sequência proposta para a próxima meta:** primeiro resolver offline condição→entidade→controle/variante→resultado observável, marcando campos que o extrator não lê. Depois preparar positivos/negativos e um diagnóstico isolado de entrada. Em seguida validar uma ida/volta e repetição curta, com o cliente de evidência já conferido. Só então executar a suíte completa e o percurso longo, em condições registradas. Manter os passos de reconhecimento/ação no Maa e distinguir retry de navegação guardado de repetição de gasto/resgate/início.

O resultado de árvore/eventos foi demonstrado: zero imagens no percurso aprovado e 50 consultas sem captura/reconhecimento adicional. Ainda há oportunidade de reduzir texto repetido: as respostas de ações incluem árvore/eventos e são maiores que os recibos antigos. Uma projeção por intenção ou por mudanças merece avaliação separada, mantendo a árvore completa, validade e proveniência disponíveis. A retrospectiva não afirma ganho de tokens/cobrança ou aceleração de campanha.

## Auditoria integral do pacote e registro do método — 26/10/2026

Ordem da retrospectiva aceita pelo usuário e registrada em AGENTS.md: preparar offline → calibrar uma operação → validar ida/volta curta → suíte completa/percurso longo. O procedimento técnico está em [architecture.md](architecture.md#preparacao-antes-da-calibracao), os conhecimentos sobre bindings/layout/SDK e a matriz de cobertura em [assets.md](assets.md#cobertura-da-extracao). A auditoria foi ampliada pelo usuário para todo o pacote e acompanhada em ALE-187.

**94.583 entradas extraídas e verificadas**, 7.661.495.628 bytes de payload. O SHA-256 do pacote original de 7.666.379.762 bytes foi idêntico antes/depois: `96baeaebdd9c368351eb876c03d9957c09da907efcf8f09c3858cb6228e769c5`. Cada saída teve tamanho e leitura de volta conferidos com hash. A fase de extração/interpretação inicial levou 1.283,12 s; isso não mede o trabalho total de auditoria ou o desempenho do agente.

Interpretação final: **59.771 estruturas lidas, 34.811 arquivos parcialmente interpretados e um conteúdo opaco** (`bin64/game.bin`). Não há erro pendente nos formatos reconhecidos. Essa classificação mantém as lacunas: classes/campos CSB, frames, payloads SCSP/SCA, pixels SCT, linhas opacas de sete tabelas e semântica dos modelos/eventos. Ela não equivale a compreender toda a lógica do jogo. Fontes e profundidade por formato/arquivo estão em [pack-coverage.json](../data/catalogs/pack-coverage.json) e no índice privado.

O índice de referências percorreu as 94.583 entradas e produziu 142.774 candidatos literais de assets (130.173 destinos existentes), 324.744 ocorrências de chaves de texto e 394.070 regiões de atlas. Uma consulta de integridade confirmou zero destinos resolvidos fora do inventário. A ligação `chat_filter → cm_checkbg.png` e os sete controles da navegação foram conferidos; `O (alphabet)` foi corroborado entre configuração/texto. Referências são estáticas, sem prova adicional de estado da conta ou acesso na demo.

A revisão final encontrou divergência entre uma versão salva da ferramenta e a versão anteriormente carregada nos testes. As correções foram consolidadas, cópias e fingerprints finais foram preservadas, e a suíte foi repetida sobre a versão em disco. **161 testes passaram em 182,63 s**; 32 deles exercitam a inspeção/auditoria, incluindo corpus privado, tabelas sem `id`, chave física diferente do ID, linhas opacas, variantes de índice, limites de contêiner, retomada, identidade do pacote e caminhos de saída. Os hashes das fontes salvas permaneceram iguais aos conferidos antes da suíte. `validate`: **125 nós, zero erros**; reconhecimento/pipelines de gameplay não foram alterados por esta auditoria.

Evidências privadas: `assets/local/full-pack/{inventory.json,audit.sqlite,summary.json,reference-summary.json}`, `var/full-pack-*.log`, `var/pack-audit-tests-consolidated.log`, `var/pack-audit-validate.json` e `var/pack-audit-final-sources.json`. Pacote, chaves, assets integrais e dumps permaneceram locais e ignorados pelo Git. Nenhuma nova entrada no jogo, inferência dos modelos internos ou validação positiva dos avisos ocorreu; ALE-186 mantém o escopo adiado pelo usuário.

## Sessão do agente: árvore e eventos primeiro — 26/10/2026

O comando `agent` foi exercitado com uma única conexão persistente, 31 pedidos e encerramento explícito, usando captura 2, mouse 4, teclado 4 e cliente 1212 × 682, sem foco. O agente consultou respostas textuais; três imagens foram abertas somente para a exceção já conhecida da taberna ociosa, que continuou classificada como desconhecida. A restauração do HUD usou uma primitiva por ponto escolhido na imagem recente, com as guardas normais; a calibração do lobby ocioso permanece pendente.

O percurso positivo confirmou **G: lobby → Orbis**, leitura do painel de missões pela árvore (41 nós) e **Esc: Orbis → lobby**. Cinco consultas sequenciais à mesma leitura de missões acrescentaram **zero capturas e zero reconhecimentos**, mantendo o mesmo ID da observação e sem abrir imagens. Foi usado explicitamente `--max-age-ms 30000` nessas consultas somente leitura; as idades reais ficaram entre 1092 e 1196 ms. Isso não altera o padrão de 500 ms nem as observações atuais exigidas pelas ações. O OCR do painel levou a leitura além de 500 ms, e a resposta inicial corretamente marcou a expiração.

Para aquela leitura, o JSON completo de observação tinha 49863 bytes e a resposta do agente 9508 bytes, ambos serializados compactamente em UTF-8: redução de **80,9% no texto**. Não foi medido consumo de tokens, cobrança de imagens ou ganho numa campanha longa. A resposta mantém referência à árvore completa e sua proveniência. Evidências privadas: `var/agent-session-live.json` e `var/runs/20261026T144453Z_dfa4ca2b/agent_*.json`. O observador terminou invalidado como `disconnected`.

Houve recusas conservadoras ao iniciar a rotina com lobby ocioso desconhecido. Em uma execução nativa, o Orbis abriu e o Maa registrou o envio de Escape, mas não houve confirmação do lobby; o pipeline terminou em falha. Pedidos posteriores com origem incompatível foram recusados. A nova observação e uma primitiva explícita de Escape confirmaram o retorno. O envio aceito pelo Maa não foi tratado como conclusão; a falha do retorno na rotina permanece a revalidar, sem mudar seus templates, limites ou método de entrada neste incremento. Não houve início de combate, resgate, gasto ou chat enviado.

`data/input/hotkeys.json` registra `orbis` como validado com G na configuração atual, incluindo retorno por Esc. Isso não comprova os demais defaults do DB nem Esc em diálogos. Tab, C, O, 1 e 3 ainda precisam de validação de origem/destino; quick menu, heróis e opções ainda não têm estados calibrados no perfil atual.

A suíte completa passou com **104 testes em 162,42 s**. Após o ajuste de cursor explícito no transporte, a verificação específica final passou com **36 testes**, incluindo os três casos adicionais de expiração/mudança de janela e replay de cursor. Cobertura: uma conexão, snapshot sem captura, nulos e proveniência, preservação de imagem de exceção, falha sem retry, nova observação antes de agir, eventos, EOF e desconexão. `validate` confirmou 114 nós e zero erros. Log da suíte: `var/agent-session-tests.log`.

## Orbis e observador compartilhado — 26/10/2026

O ícone Orbis foi revalidado em **3 ciclos completos lobby → Orbis → lobby**, com captura 2, mouse 4 e teclado 4, sem fallback, cliente 1212 × 682. A correlação ficou entre 0,991 e 0,993; o erro dos traços ficou entre 0,699 e 0,818. A captura antes recusada por MAE global 18,647 passou com MAE dos traços 1,053 e correlação 0,987. O replay de **37 casos** passou: 3 positivos e 34 negativos, incluindo dois escurecimentos sintéticos do mesmo ícone. Evidências: `var/orbis-calibration-live.json` e `var/orbis-calibration-replay.json`. A restauração inicial da taberna ociosa ainda exigiu uma primitiva por ponto observado porque os templates antigos de lobby ocioso não reconheceram essa iluminação; isso é separado da calibração do ícone visível.

O observador foi exercitado no mesmo percurso reversível, sem combate, resgate ou gasto. Cinco observações explícitas consumiram 5 capturas/5 reconhecimentos em 1696 ms; cinco consultas recentes consumiram **0 capturas/0 reconhecimentos adicionais**, em 3,79 ms. A consulta CLI externa confirmou a mesma revisão sem abrir outra conexão. Durante o pipeline, os callbacks publicaram as transições, incluindo estados intermediários desconhecidos e conclusão. Do início da ação até a publicação da árvore: cerca de 797 ms na abertura e 1057 ms no retorno. Esses intervalos incluem transição do jogo, espera, reconhecimento e instrumentação; não são latência desde o aparecimento visual da tela nem benchmark de FPS.

Nesta amostra, CPU do processo foi 1641 ms nas cinco observações; as consultas ficaram abaixo da resolução do contador de CPU usado (retornou 0 ms, sem comprovar custo nulo). A soma instrumentada do reconhecimento foi 3580 ms de parede/17359 ms de CPU no processo, compatível com trabalho paralelo das bibliotecas; esses totais não são utilização percentual nem custo exclusivo do observador. A instrumentação de publicação em memória somou cerca de 5 ms; gravação em disco está incluída no tempo total das operações, não nessa parcela. Não foi medido o número de capturas internas do Maa. Evidência: `var/shared-observer-live.json`, execução `20261026T141414Z_3a83259e`.

Guarda de tela mudou e bloqueou uma tentativa inicial de restaurar o HUD, sem enviar o clique. A nova observação permitiu o teste posterior. Snapshots de callback com timestamp de captura desconhecido não foram considerados atuais; consultas após desconexão ficaram inválidas. Os testes do observador cobrem expiração, mudança de relógio/janela, ausência de timestamp, cópia isolada, eventos limitados, callback tardio, recusa de captura concorrente e preservação da observação atual antes da ação. O ganho demonstrado é evitar leituras redundantes de um estado recente; não se conclui que a campanha completa ficará mais rápida nem que a árvore estará continuamente atualizada.

Verificação final: **91 testes passaram em 173,63 s**; `validate` confirmou 114 nós e zero erros. A falha intermediária estava na construção de um dado do teste sem proveniência; foi corrigida preservando a validação obrigatória por campo da árvore.

## Perfil fixo de janela — 26/10/2026

Conexão real com o jogo aberto, sem entrada de gameplay: área cliente propositalmente ajustada para 1213 × 682 antes da conexão; Runtime corrigiu para 1212 × 682 e removeu os controles de redimensionamento/maximização. Ao desconectar, o estilo original foi restaurado e a área cliente permaneceu calibrada. A janela ficou sem foco durante o teste. Evidências: `var/window-profile-live.json`, `var/window-profile-resize-live.json` e `var/runs/20261026T135753Z_b5780328/window_profile.json`.

Os testes de `test_window_profile.py` cobrem aplicação/liberação do perfil, limpeza idempotente, rollback de falha, recusa de janela minimizada, HWND reutilizado, dimensão sem calibração e bloqueio de entrada após alteração externa. O bloqueio atua nos controles normais da janela durante cada conexão; não comprova proteção contra redimensionamento por outro programa nem restauração após encerramento forçado do driver. Apenas 1212 × 682 está calibrado.

Verificação final deste incremento: **82 testes passaram em 179,63 s**; `driver-epic-seven validate` confirmou 114 nós e zero erros. Esses totais incluem os recursos já presentes de preparação da sessão; a execução ao vivo descrita nesta seção valida especificamente o perfil da janela.

## Migração para a estrutura padrão — 26/10/2026

`ui_tree` passou a ser produzido por `observe`, OCR geral, leitura de missões, inspeção de fases e callback ScreenTarget dos pipelines. Alvos de navegação, histórias/resultados e fases usam os adaptadores e projeções comuns. Relatórios antigos permanecem como fonte/compatibilidade; novos consumidores não os usam como estado paralelo. As evidências dos callbacks vinculam a árvore à captura e ao arquivo efetivamente gravados.

**76 testes passaram** na verificação final em 199,44 s (a execução intermediária também passou, em 174,91 s). Incluem replay de histórias/resultados, retry delimitado de confirmação, encadeamento de duas fases, parada por derrota, LongPress, custo/orçamento e início único em controlador simulado. `validate` confirmou 90 nós e zero erros nos perfis padrão e campanha. Os logs locais são `var/standard-migration-tests-final.log` e `var/standard-migration-tests.log`.

Durante a migração, foram realizados os seguintes testes no jogo, com FramePool 2, mouse 4 e teclado 4, cliente 1212 × 682:

| Parte | Resultado e evidência local em `var/runs/` |
|---|---|
| Observação geral e navegação | Lobby → Orbis → lobby confirmado, com alvos resolvidos da árvore (`20261026T124917Z_84890581`) |
| Missões e menu do modo | Grupo/contador lidos pela projeção; Go confirmado como menu, sem identidade de fase/custo (`20261026T125529Z_889cac63`) |
| Mapa e recusa conservadora | Episódio/capítulo e linha reconhecidos; banner da demo cobriu a descrição selecionada e a guarda interrompeu prepare antes de Ready (`20261026T125803Z_4c38e942`) |
| Inspeção de preparação | Ready visível aberto por primitiva observada; título Hidden Plan corroborado na seleção de apoiador (`20261026T125950Z_85f0cbf2`) |
| Prepare desde apoiador identificado | Pipeline prepare concluiu sem Start; fase epi009/Hidden Plan, custo 16 e saldo 1182 confirmados (`20261026T130009Z_be60816d`) |
| Retorno | Saída da preparação e retorno ao lobby (`20261026T130047Z_e38a2d9b`, `20261026T130203Z_d79e840f`) |
| Aba/setas integradas | Aba Heir e grupos 16 → 15 → 16 consultados pela árvore, retorno ao lobby (`20261026T130817Z_3cbd6f5c`). A abertura foi uma primitiva observada porque o marcador do Orbis havia sido recusado pelo classificador; nenhum limiar foi alterado |

Não houve início de batalha, resgate ou compra; nenhum fallback foi necessário. A guarda de descrição do mapa não foi enfraquecida: o percurso automático desde aquele mapa permanece limitado pelo banner. O teste positivo de prepare começou no painel de apoiador com identidade confirmada. Na conferência final, a taberna estava visível, mas o marcador do Orbis não atingiu o critério calibrado; a guarda recusou a abertura. Uma primitiva com captura recente abriu somente o guia, antes da validação das setas. Isso preserva uma limitação de reconhecimento, sem promover tela desconhecida a lobby por suposição. Histórias, resultados e inícios foram revalidados em capturas/controladores simulados, sem combate ao vivo neste incremento. A síntese está em `var/standard-migration-live.json`.

A documentação ativa em `docs/` foi reduzida de 13 para 5 arquivos, com links/âncoras conferidos. As fontes anteriores foram preservadas em backup local `var/docs-before-standard-migration.zip`; regras estão em AGENTS.md e contrato técnico em architecture.md. A política atual de mouse é 4 padrão, 64 fallback explícito, inclusive para os perfis de campanha. O relatório HTML anterior foi preservado.

## Árvore observada no jogo — 26/10/2026

Depois da validação offline do contrato v1, o percurso ao vivo confirmou captura, abertura do Orbis, aba Heir, consulta por grupo/missão/controle, marca de resgate já existente, grupos adjacentes, rolagem e Go até o menu de modo. A árvore foi reconstruída a cada observação e não reteve controles do grupo ou da região anterior. Categorias de batalha, menu do modo e identidade de fase/custo permaneceram separados.

Métodos: FramePool 2, mouse PostMessage 4 e teclado PostMessage 4, cliente 1212 × 682. Nenhum fallback foi necessário. A captura inicial estava sem foco; não se generaliza essa condição a todas as telas. Foram registradas 14 verificações entre navegação/leitura e guardas sem envio de entrada. Detalhes e fontes estão em [contrato da árvore observada](architecture.md#arvore-observada); síntese local em `var/observed-ui-live-validation.json`.

Não houve resgate, compra, seletor ou início de batalha. A sessão terminou no lobby (`var/runs/20261026T120417Z_9fa72a80/live_tree_final_lobby.json`). Não houve alteração funcional de código ou pipeline neste teste; a suíte de 72 testes é a verificação offline anterior, não foi contada como execução ao vivo.

## Contrato da árvore observada — 26/10/2026

[Contrato versão 1](architecture.md#arvore-observada) implementado e integrado à saída de `quest read`, à consulta offline `quest query` e à resolução dos alvos de missão antes das guardas existentes. Reconhecedores, pipelines, métodos de entrada e permissões de execução foram preservados.

**72 testes passaram** na suíte completa (145,26 s); **26 testes focados** no leitor/contrato passaram (8,56 s). Incluem o replay das oito capturas locais, consulta sem inicializar o Runtime vivo, persistência com captura simulada, campos desconhecidos, proveniência por campo, caixas, relações e recusa de alvo divergente. `validate`: 90 nós, zero erros. Nenhuma captura nova, clique ou tecla no jogo neste incremento; a validação é offline e não acrescenta prova de transição ao vivo.

## Base comum de missões — 26/10/2026

Contrato e evidências: [primitivas de missão](mission-operations.md#primitivas-de-missao). Foram acrescentadas consultas do catálogo, OCR geral, leitura vinculada ao task_id, navegação pontual, resgate delimitado, comparação e swipe. A classificação diferencia categoria/modo de uma fase/preparação identificada.

**58 testes passaram** na suíte completa (144,70 s). Após os últimos ajustes de metadados, **23 testes de missões e guardas passaram** (7,65 s). O replay novo usa oito capturas locais; não conecta ao jogo. `validate`: 90 nós, zero erros, nenhuma nova rotina de família promovida.

Ao vivo: um Receive coletou quatro missões já satisfeitas no grupo 16, levando-o de 0/5 a 4/5. Foram verificadas leitura, marca de resgate, reorganização da lista, rolagem, grupos adjacentes e Go até um menu de modo; nenhuma batalha foi iniciada. Resgate final de grupo continua sem teste positivo neste incremento. As ações dos demais caminhos não foram calibradas.

Preferência confirmada pelo usuário: mouse 4 padrão, 64 fallback explícito após nova observação; 64 move/restaura o cursor. Uma abertura de Orbis não confirmada com 4 foi repetida com 64 somente após releitura do lobby, sem duplicar transação. Registro: `var/runs/20261026T113609Z_bafab495/input_fallback.json`. A sessão terminou no lobby. Os registros seguintes preservam o histórico de calibração anterior.

Data: 25/10/2026. Perfil: Steam Demo, Windows, cliente 1212 × 682, MaaFramework 5.14.3. Ambiente instalado de forma editável em `.venv/`. O projeto foi iniciado como repositório Git local na branch `main`, sem remoto configurado.

## Fundação: testes offline iniciais

`python -m pytest -q`: 12 testes, incluindo reconhecimento por Maa em cinco capturas locais. Os casos visuais incluem lobby, Orbis, lobby ocioso, confirmação de saída e uma janela cobrindo o jogo. A confirmação de saída e a cobertura devem resultar em `unknown`.

Os demais testes cobrem troca de processo, resolução incompatível, diferença entre primeiro/segundo plano, observação vencida, ambiguidade visual, sobreposição escurecida, ponto fixo restrito ao lobby ocioso, bloqueio de rotina em rascunho, contratos dos recursos, nomes de callbacks em arquivos de evidência e preservação do registro de envio sem repetir um clique quando a pós-condição expira.

O teste de visão usa a API C pública do Maa para associar apenas um recurso ao Tasker. Não conecta ao jogo nem envia entrada. A distribuição Python utilizada não trouxe a biblioteca opcional do `DbgController`; não há dependência desse componente para o teste.

## Percurso com pipeline Maa nativo

`driver-epic-seven run orbis_roundtrip` concluiu o caminho:

```text
Orbis.Start → Orbis.WakeLobby → Orbis.Open → Orbis.Back → Orbis.Done
```

Estado inicial `lobby_idle`, final `lobby`. Os cinco nós concluíram. Duração observada do pipeline e verificação final: aproximadamente 2,15 segundos, sem contar inicialização do driver e observação inicial. Evidência local: `var/runs/20261025T234209Z_c6fb698f/`.

Isso confirma a migração para `Tasker.post_task`, reconhecimento customizado integrado ao Maa e ações/encadeamento nativos. O percurso incluiu a recuperação do HUD ocioso; não foi necessário um clique preparatório externo.

## Primitivas independentes

Em uma segunda execução foram confirmados:

- Clique por alvo reconhecido → Orbis Guide.
- Escape vinculado ao estado → lobby.
- Clique por coordenada derivada da captura e vinculada a uma observação recente → Orbis Guide.
- Escape vinculado a uma observação recente → lobby.

Todas as quatro transições tiveram a pós-condição visual confirmada. Evidência local: `var/runs/20261025T234308Z_4039d0bd/primitive_validation.json`. Captura final mostrou o lobby; energia e skystones visíveis continuaram 920/221 e 3.856. O teste não coletou recompensas nem iniciou batalhas.

O método configurado foi `FramePool` para captura e `PostMessage` para mouse/teclado. O teste anterior com cobertura e confirmação explícita do foco permanece separado em `assets/local/baseline/covered_and_background.json`.

## Assets e estrutura

O importador preservou o conteúdo de origem e gerou cinco templates, cinco fixtures locais, quatro layouts e o catálogo estático de quests. O extrator somente leitura foi exercitado com `img/_btn_gold_r_2.png` e `img/_btn_green_r_2.png`; ambos abriram como PNG de 200 × 128. As extrações estão em `assets/local/pack/`, fora do Git. A diferença entre a textura 200 × 128 e a largura 360 declarada no layout reforça a necessidade de calibrar a composição final.

As duas skills canônicas passaram no validador `skill-creator`. O CLI `validate` confirmou o bundle e as referências do registry. O projeto usa `AGENTS.md` e `.agents/skills/`; não contém a estrutura de configuração do Claude Code nem modifica configurações globais do Codex.

## Pendências na fundação

Combate, história, resultado, identificação de fase/equipe/custo, recursos de repetição, OCR, rolagem e arraste permanecem para calibração. Os rascunhos não podem ser iniciados pelo CLI. Não foram testadas outras resoluções, idiomas, minimização ou sessões prolongadas. Este registro não substitui evidência nova quando uma dessas condições mudar.

## Incremento: batalha e seleção de fase

Ainda em 25/10/2026, uma batalha real de `pen001` (Outside the Walls) foi iniciada por primitiva vinculada à observação. Resultado: 3 estrelas, incluindo Story Clear; energia 920 → 912; progresso do capítulo 0/36 → 3/36; `pen002` liberada. Skip e confirmação foram acionados e a entrada em combate foi observada. Uma tentativa posterior de Skip foi recusada antes do envio por mudança da tela. Não houve segunda entrada em combate.

Evidência local:

| Verificação | Diretório em `var/runs/` |
|---|---|
| Preparação e início único de pen001 | `20261026T001048Z_a56a321a` |
| Confirmação de Skip e destino de combate | `20261026T001130Z_bf3f28be` |
| CLEAR com 3 estrelas | `20261026T001327Z_d2c8c353` |
| Próxima fase liberada e energia 912 | `20261026T001643Z_6aa2cd74` |
| Recusa de pen001 quando Ready mostrava pen002 | `20261026T003409Z_99ee862b` |
| Pipeline completo de preparação de pen002 | `20261026T003826Z_75f0c2dc` |

Os nomes dos diretórios usam UTC; a data local desses testes é 25/10/2026. No pipeline final, todos os cinco nós concluíram: Entry, Row, OpenReady, Supporter e CheckReady. A fase foi confirmada por local + história; custo 8, saldo 912, zero inícios. O fluxo aguardou o carregamento e a estabilidade do painel de suporte. Foram calibradas duas variantes do rótulo Start Quest para a animação de entrada.

`prepare_stage` foi promovida a `validated` com escopo explícito no registry. `start_stage` permanece `experimental`: o teste offline usa um controlador simulado e capturas reais, exige exatamente um clique e reconhece a história seguinte; o início real por pipeline parametrizado ainda não foi exercitado. Os rascunhos genéricos de combate/história/próxima fase continuam desabilitados.

## Verificação final e reinicialização

`python -m pytest -q`: **27 testes passaram**, sem skips nesta máquina, incluindo reconhecimento em 18 capturas locais, OCR de identidade/custo, cadeado, recusa de fase errada e repetição, orçamento, carregamento de suporte e início único no controlador offline. `driver-epic-seven validate`: válido, zero erros, 52 nós. O bundle contém 27 PNGs e 12 estados visuais. Os testes offline não conectam ao jogo nem gastam energia.

Depois da queda de energia, `doctor` redescobriu a nova janela na mesma resolução. Uma primeira captura mostrou seletor de herói com habilidade aberta (`unknown`), sem entrada. A captura posterior confirmou a taberna ociosa (`lobby_idle`), inclusive sem foco. Evidência: `var/runs/20261026T005747Z_d22de9a3/`. Os logs nessa captura tinham aproximadamente 27 segundos e foram marcados como antigos. Não houve entrada após a queda; recursos e progresso atuais precisam de nova leitura antes de continuar a missão.

Permanecem pendentes: navegação automatizada desde a taberna até o capítulo, escolha/otimização de equipe, combate e história como sequência geral, recuperação de interrupções, avanço automático, outras resoluções/idiomas e minimização. A missão Citylord do Path of Heir 15 não foi concluída por este teste.

## Campanha e avisos — atualização de 26/10/2026

Os registros acima descrevem os testes iniciais. Posteriormente, o capítulo 5 do episódio 2 foi concluído, incluindo encadeamento nativo das fases 11 e 12 em uma única tarefa Maa (`20261026T015611Z_7e9079d7`). A fase 9 foi executada manualmente pelo usuário. Os capítulos 6, 7, 8 e 9 foram concluídos durante a meta de campanha, sem derrotas registradas; as reservas, entradas e vitórias estão em `var/campaign_attempts.json`.

O perfil explícito de campanha passou a usar mouse 64 após comparação documentada com os modos 4 e 1. Captura FramePool 2, teclado 4, demo Steam em inglês, 1212 × 682. O resultado de uma chamada de entrada continua insuficiente sem a transição visual.

Casos adicionais exercitados: Rank Up 38; fechamento de amizade de herói por Tap to close; aviso Connection Unlocked de Tamarinne; LongPress de 1500 ms em introdução de história; preparação com No Record e resultado com objetivo No Continues. A fase `dis003` foi vencida com duas estrelas e a cadeia avançou para a seguinte. Não foi repetida para obter mais estrelas.

Após a adaptação da preparação de `dis003`, **42 testes passaram** em 120,72 s. Incluem capturas locais positivas/negativas, identidade exata com releitura de linhas, limites persistentes de três entradas, início único, encadeamento de duas fases, múltiplos avisos e soltura do mouse após LongPress. O CLI `validate` confirmou 86 nós e zero erros. Simulações offline não provam aceitação de entrada pelo jogo; os casos ao vivo são registrados separadamente. Outras resoluções, idiomas, minimização, escolhas de equipe e generalização para outros modos permanecem pendentes.

<a id="descobertas-iniciais"></a>

## Descobertas iniciais e contexto histórico

### Arquitetura observada

Executável Windows AMD64 `EpicSeven_Steam.exe`, janela `Epic Seven`, classe `GLFW30`. A análise estática encontrou OpenGL, GLFW, Cocos2d-x/Yuna, Steam/STOVE, FMOD, Sentry e WebView2. São evidências de componentes, não uma API pública para controlar o jogo.

UI Automation expôs um elemento de janela e os padrões Window/Transform, sem os botões internos. Nomes de nós CSB não são AutomationIds utilizáveis pelo Windows. O controle por imagem e entrada Win32 foi a superfície prática testada.

### Sessão de 25/10/2026

| Método | Amostra | Resultado |
|---|---:|---|
| Controlador nativo: captura de desktop e SendInput | 3 ciclos | Orbis aberto e retorno ao lobby confirmados por imagem |
| Maa FramePool + Seize + TemplateMatch | 3 ciclos | Mesmo percurso confirmado, com alvo localizado automaticamente |
| Captura com janela coberta | 1 condição | Desktop mostrou a cobertura; FramePool continuou mostrando o jogo |
| Maa FramePool + PostMessage, sem foco | 1 ciclo | Orbis aberto e fechado; foco ficou na janela de cobertura e cursor permaneceu no mesmo ponto |

Área cliente de 1212 × 682. Jogo e controlador estavam em nível de integridade médio, sem elevação. Não houve coleta de recompensa ou gasto de recurso nesses testes de navegação. Esse resultado não comprova funcionamento em todas as telas, com janela minimizada ou em combate.

Medianas de abertura/retorno no protótipo: nativo 963/954 ms; Maa 468/472 ms. O nativo incluía espera fixa de 600 ms e gravações adicionais. Portanto, a diferença **não mede o ganho isolado do framework**. O ganho demonstrado foi a integração de reconhecimento, captura por janela e entrada em segundo plano.

Os JSON anteriores foram preservados em `assets/local/baseline/`. A evidência da implementação deste repositório fica em `var/runs/`; consulte também `docs/validation.md` para os testes executados na criação.

### Casos que afetam o agente

- O HUD do lobby desapareceu após inatividade. Foco e movimento do cursor não bastaram nesse caso; um clique em área vazia o restaurou.
- `scene=lobby` pode coexistir com Orbis Guide. Escape pode mudar a tela sem atualizar o último botão nos logs.
- Uma correlação visual alta não identifica toda sobreposição. O driver acrescenta comparação de pixels e recusa classificação ambígua.
- Recortes de tela estão calibrados para o perfil observado. Outra resolução, idioma ou tema pode exigir novos templates.
- O `.pack` fornece catálogo, textos, condições e recompensas, sem o progresso atual da conta. O roteiro anterior tem 93 grupos e 877 tarefas; 25 tarefas RTA foram marcadas como indisponíveis na demo.
- A seleção/preparação de `pen002` foi validada com OCR e pipeline nativo. Um combate de `pen001`, Skip com confirmação e telas de resultado foram observados por primitivas. Isso ainda não valida uma sequência geral de combate/história ou avanço automático.

### Teste de capítulo 5 e retomada

Uma entrada em Outside the Walls (`pen001`, episódio 2/capítulo 5) terminou com 3 estrelas e Story Clear. A energia passou de 920 para 912; o capítulo passou de 0/36 para 3/36 e liberou Permeating Darkness. Citylord é a quinta fase do catálogo; a missão do Path of Heir 15 ainda não foi concluída neste teste.

O pipeline de preparação de `pen002` selecionou a linha, confirmou a descrição, abriu Ready e Select Team e verificou nome/local/custo. Ele parou antes de iniciar. Um pedido da fase errada na preparação foi recusado. Veja [seleção de fase](campaign.md#selecao-de-fase) e [validação](validation.md).

Depois de uma queda de energia, o driver redescobriu novos PID/HWND e capturou a nova sessão. Uma tela de seleção de herói permaneceu `unknown`, sem entrada; depois a taberna foi reconhecida como `lobby_idle`. A observação funcionou sem foco. Progresso pós-reinício ainda precisa ser relido antes de continuar o capítulo.

### Fontes

- [Post usado como referência de organização](https://x.com/lincolixavier/status/2037588026394587330); imagem consultada em 25/10/2026.
- [MaaFramework](https://github.com/MaaXYZ/MaaFramework), versão Python fixada em 5.14.3.
- [Epic Seven Demo no Steam](https://store.steampowered.com/app/5129800/).
- [Yuna Engine, publicação Smilegate](https://newsroom.smilegate.com/en/eng/Epic_Seven_YUNA_Engine_EN).

A disponibilidade e o escopo da demo são próprios da versão analisada; não generalize os dados para o cliente completo. A criação deste repositório não alterou o relatório HTML anterior.


<a id="caminho-inicial-stove"></a>
## Caminho inicial STOVE e mouse 4 — 27/10/2026

Janela redescoberta por processo EpicSeven.exe, título Epic Seven, classe GLFW30, área cliente 1212×682. Captura FramePool2, teclado4. Mouse64 foi usado inicialmente; após o usuário notar o cursor, o driver foi desconectado normalmente e o perfil local mudou para mouse4. Nenhum retorno automático a 64.

- `20261027T224237Z_68eb8f17`: Wish List recomendada aplicada e painel Covenant 14/14, disponibilidade gratuita 1/1 observada.
- `20261027T224519Z_8c20e80f`: um envio Covenant, custo observado zero; apresentação Angelica. Minimização interrompeu o fluxo e não gerou repetição. `20261027T225008Z_82ff224a/004_Path.Open.Done.png` mostra a missão em Receive após retorno ao Caminho; condição/contador ilegível permanecem desconhecidos no leitor.
- `20261027T230452Z_fb40b735`: uma entrada tar007, 8 de energia, mouse64; pausa em Rank Up. `20261027T231038Z_be088a78`: retomada com zero Start, 3★ e mapa 12/15.
- `20261027T232155Z_ca18ef16`: mouse4, Escape preparação→mapa e seleção/Ready de tar008, destino confirmado sem iniciar.
- `20261027T232446Z_72392ffe`: mouse4, uma entrada tar008 de 8 de energia. Parada para calibrar variante cinza de história; reserva preservada.
- `20261027T233054Z_89604c75/agent_000003.json`→`agent_000004.json`: um LongPress1500 de mouse4 no Skip observado abriu a confirmação exata. Positivos, controles cobertos, imagens escurecidas e modais são exercitados no replay nativo de história.
- `20261027T233853Z_ffcd0b4e/006_Path.Campaign.tar008.Clear.json`: três estrelas e três checks; recompensas prosseguiram, depois aviso de Abyss. O leitor do aviso exige título, corpo específico e fechar, incluindo a falta de espaço OCR em Tapto close. Primitiva curta expirou antes da conclusão; não tratar timeout como prova de falha universal do mouse4.
- `20261027T234516Z_92a91eb4`: aviso fechado por grafo, Story Clear recebido, mapa com 15/15 e 846 de energia. Surgiram ainda Received Reward e CHAPTER COMPLETE. O encerramento terminal do grafo precisa distinguir esses avisos do retorno estável; não declarar toda a cadeia concluída por uma captura intermediária.

A entrada tar008 ocorreu uma vez. As retomadas não possuem Start e não gastam nova energia. O novo diário recusa um pedido novo para uma fase já registrada; a trava foi exercitada offline com estados reserved, sent, victory, returned e defeat. Resultado observado, envio de entrada e término do grafo são provas separadas.

Ao encerramento desse bloco, o grupo 1 ainda não estava concluído; o fechamento posterior está registrado abaixo. O compilador por nível e a instalação portátil permanecem pendentes. Os 65 grupos e os 751 registros são cobertura de roteiro, não de execução. A nova compatibilidade Steam/STOVE é uma premissa aprovada, sem teste Steam nesta sessão.


A suíte usa capturas privadas quando instaladas. Na simulação de seleção/combate, o resultado nativo de Vision é reutilizado somente para pixels de fixture exatamente idênticos; verificações específicas da fase, seletores, contagens e ações continuam executadas. Isso reduz OCR repetido no teste e não altera Runtime nem demonstra ganho de desempenho no jogo. O relatório completo e diagnósticos intermediários ficam em `var/path-level-live/`.


A preparação preserva CP e outros campos legíveis quando o custo ou Start não podem ser lidos, desde que Ready/equipe, localização/título e a composição de preparação estejam comprovados. Localização/título continuam necessários para distinguir formação do shell compartilhado Ready/Team. Custo ambíguo fica desconhecido; os testes conferem que isso nunca habilita Start. O histórico gráfico compartilhado com a variante cinza também não expõe o alvo genérico de história no diálogo específico de Connection. Diários explícitos de contas/perfis distintos têm teste de isolamento; trocar para Steam não apaga nem reaproveita as reservas STOVE.


Verificação final deste bloco: `python -m pytest` — **372 passed**, 431,86 s, sem skips nesta máquina com fixtures privadas; `driver-epic-seven validate` — Steam 135 nós, STOVE 112 nós, ambos válidos. Resultado e manifesto de fontes em `var/path-level-live/validation-summary.json`. O driver foi desconectado normalmente e o transporte encerrado, com mouse4 mantido no perfil. O término do Caminho e a tela CHAPTER COMPLETE não foram declarados validados por esses testes offline.

<a id="fechamento-altar-resgates"></a>
## Altar, recompensas e revisão do Caminho 1 — 27/10/2026

Mesmo perfil STOVE 1212×682, FramePool2, mouse4 e teclado4; uma conexão por vez. As execuções UTC abaixo ocorreram na noite de 27/10 em Brasília/Bahia.

**Correção da leitura de CHAPTER COMPLETE:** `20261027T234916Z_c3c3dce7/agent_000001/2.json` guardava a tela intermediária; a evidência posterior imutável `002_recognition_Custom_40a1730f-44fd-421e-bd9e-59daa45093f2.json/png` já mostrava o capítulo 4, sem outro clique de fechamento. Uma captura intermediária foi confundida com o alias mutável posterior. A transição ocorreu; não há prova de que aquela tela exigia toque ou gesto de segurar.

| Evidência privada | Resultado observado |
| --- | --- |
| `20261028T005525Z_65af4a70` | Dark Spirit Altar Easy cmon001: um Start, 9 de energia (846→837), Auto mantido ligado, vitória CLEAR. Nenhum reinício quando o primeiro grafo esperou a variante errada de resultado. |
| `20261028T005525Z_65af4a70/agent_000004→000005→000006` | CLEAR genérico seguido de uma pressão observada e recompensas. Fontes `dungeon.csb` e `result_base.csb`; modo e estrelas não inferidos pelo banner. |
| `20261028T010406Z_67288c42` e `20261028T011335Z_07cce166/agent_000001` | Retomadas com zero Start, avisos/recompensas e saída para lobby. O rodapé final tem precedência sobre o HUD persistente. |
| `20261028T011335Z_07cce166/agent_000003` e `010_Path.Claim.Done.json/png` | Um Receive coletou as três missões prontas, 3/6→6/6, recibo confirmado. Um contador de condição ilegível não impediu o controle Receive positivamente reconhecido. |
| `20261028T012258Z_711fed77/agent_000001` | Um envio da recompensa final e recibo; houve aviso Rank e depois Maximum Energy 161→172 sobre o Caminho 2. Grafo parou finitamente nessa variante sem repetir o resgate. |
| `20261028T012258Z_711fed77/agent_000003→000004→000010` | Após restauração da janela, aviso fechado pela primitiva observada; banner Rank 10 também fechado, sem compra. Reabertura confirmou Path of Heir 2 em 0/5. Diário reconciliado com envio único, recibo e leitura limpa do grupo seguinte. |
| `20261028T012258Z_711fed77/agent_000013`, `000021` e `000026` | Checkpoint: Marco Brilhante com 73 essências/custo 60, Arby 42/50, equipamento CP 24400 e três rótulos No set effect. IDs de itens/slots e campos não lidos continuam desconhecidos. Não houve baú, seletor ou melhoria aplicada. |

A leitura do Marco falhava porque um template de composição continha o saldo antigo 64. Esse match passou a ser auxiliar; título/header/Receive atuais identificam a composição e números continuam com unicidade e confiança mínima .98. O replay da árvore sobre a mesma captura confirmou saldo 73/custo 60. A variante Maximum Energy foi integrada ao `rank_up_result` e ao reconhecimento de confirmação já existentes; não houve novo teste consumindo recompensa só para reproduzi-la.

**Limites:** uma unidade Altar e os resgates foram observados, com retomadas de calibração. Ainda falta validar o ciclo ininterrupto completo em outro grupo legitimamente pronto, executar a preparação/melhoria escolhida no checkpoint, fechar os executores necessários ao grupo 2 e preparar instalação. A revisão do agente usou leitores e primitivas existentes; não é um executor dos 65 grupos. O relatório privado é `var/path-closure-live/checkpoint-report.json`.

**Tempo evitável identificado:** três suítes completas intermediárias somaram 21 min 13,92 s; outra foi interrompida após aproximadamente 13 min. Há sobreposição com trabalho paralelo, portanto isso não mede todo o tempo perdido. OCR repetido de pixels idênticos em fixtures, confusão entre evidências de tempos diferentes e a rota genérica `dungeon_home` também atrasaram o diagnóstico. A rota específica do Altar agora aponta para `dungeon`; o mapa das outras modalidades foi preservado. Política atual: testes focados durante ajustes, suíte completa uma vez no fechamento estabilizado e nenhuma bateria pesada concorrendo com calibração ao vivo.

## Normalização do perfil único — 27/10/2026

`config/epic-seven.json`, `resources/epic-seven/` e `assets/template-provenance.json` são as fontes únicas atuais. A descoberta aceita ambos executáveis; os adaptadores seguem a composição atual da tela, sem selecionar lógica por cliente. Os catálogos correntes são `data/catalogs/quests.json`, `data/stages/campaign-initial.json` e `data/stages/campaign.json`. Os conjuntos anteriores foram retirados dos caminhos ativos e preservados privadamente em `var/path-closure-live/before-normalization/`. O diário atual foi copiado, sem apagar reservas, para `var/current-account/path-actions.json`.

As variantes preservam nó, recorte, limiares e regras nativas; o bundle também preserva `default_pipeline.json`, incluindo o threshold .88 legado. A primeira calibração focada detectou a ausência desse arquivo na cópia, que alterava o reconhecimento de fase já concluída; o arquivo foi restaurado, sem alterar os limiares. O resultado de melhoria de artefato já mapeado foi movido para antes do bloqueio genérico de sobreposição, mantendo composição e campos, pois os dois leitores agora atendem a ambos executáveis. Essas correções foram verificadas nos casos focados existentes, sem novos gastos.

`doctor` encontrou EpicSeven.exe por meio da configuração única e consultou o SDK 5.14.3; a janela estava minimizada, sem conexão, captura ou entrada. `validate` confirmou 258 nós e zero erros. Suítes intermediárias foram interrompidas diante da mudança de escopo e dos conflitos encontrados; seus logs parciais não são aprovação final. O driver permanece desconectado e `var/STOP` preserva o encerramento da janela finita de validação.

Os testes focados da unificação cobriram o Ready específico com OCR, as exclusões de chefes/resultados do HUD genérico, captions escurecidos e o lobby histórico agora reconhecido pelo pacote único. Para Auto ligado, o recorte antigo de um check virou `auto_single_check_hint`, sem alvo/valor Auto: MAE dos positivos e negativos se sobrepunha, portanto não foi criado um limiar artificial. Capturas antigas 76/267 ficam desconhecidas; 27/297 e as atuais com quatro checks seguem reconhecidas. Os dois replays de Auto e todos seus negativos passaram no bloco de 25 testes em 38,99 s; o prólogo/contextos e guardas passaram em 16 testes, 42,99 s. Detalhes em `var/path-closure-live/auto-alternative-probe.json` e nos logs focados.

**Fechamento da versão normalizada:** `python -m pytest -q --durations=10 --maxfail=1` — **471 passed em 625,20 s**, sem skips ou warnings. `driver-epic-seven validate` — **258 nós, zero erros**. Log final: `var/path-closure-live/pytest-normalized-final.txt`; os logs intermediários falhos/interrompidos não substituem esse resultado. Os maiores casos individuais foram replays nativos de Marco (43,02 s), corpus inicial (38,34 s) e confirmação de aquisição (37,00 s); são tempos de teste, sem equivalência a FPS/latência ao vivo. Os campos e limites de composição foram conferidos em capturas salvas; não houve entrada ao vivo depois da normalização.

<a id="grupo2-fechamento"></a>
## Fechamento do grupo 2 — 28/10/2026

Mesmo perfil 1212×682, FramePool2, mouse4/teclado4; driver elevado por autorização do usuário. O transporte privado JSONL mantém uma conexão e não escolhe ações. A árvore e os eventos foram a interface principal; imagens foram abertas em falhas, telas desconhecidas e na conferência do Auto ainda não coberto pelo leitor.

Check-in Collaboration `3 /28` e New Player `Success!` reutilizam os leitores e Confirm existentes. O contador passou de 0/5 para 1/5 com um Receive da missão de nível 15; o recibo e o incremento são a prova quando a linha coletada desaparece/reordena. A navegação Diary→Heir remove a duplicação do mesmo controle semântico. As histórias gratuitas ijp001/ijp004 retornaram ao mapa; ijp002/003/005/006 obtiveram 3★. O segundo check de resultado precisou validar os pixels verdes do template existente sobre o fundo animado, preservando o filtro Maa .94 e o limite MAE14; positivos, escurecidos e cobertos foram testados. O chefe ijp007 usa uma variante nativa de disponibilidade com caveira, com proveniência no catálogo.

`20261028T100303Z_c171dda2` preserva a entrada bloqueada com apenas Genesis Ras convidado e a inclusão observada de Arbiter Vildred. O usuário confirmou que a preparação permaneceu aberta sem intervenção e corrigiu o requisito: ao menos um herói possuído naquele caso, sem regra de equipe cheia. O diário preserva a primeira entrada como `blocked_team` e a segunda entrada única, ligada à correção explícita e à mesma janela/energia/CP.

Em `20261028T104056Z_9b87074e`, o Skip/Confirm mapeado chegou ao combate; uma colisão de compartilhamento na substituição de `observer.json` interrompeu o acompanhamento. A gravação de evidências agora repete somente o rename atômico por até 500 ms em PermissionError, sem repetir captura ou entrada. Em `20261028T104229Z_734b9fef`, o leitor Auto não reconheceu o HUD manual de Ras: o template desligado atual é limitado às skills de Vildred. Um clique exploratório único no controle observado foi seguido por conferência da captura: dois retratos azuis com checks e combate avançando sozinho. Esse caso não foi promovido a leitura genérica de Auto. A restauração da janela foi seguida de nova observação.

`20261028T104542Z_eaf541ac/agent_000001.json` comprova a retomada de ijp007, zero Start, Skip/Confirm intermediários, 3★, recompensas e retorno ao mapa 15/15. O grafo anterior de retomada tinha arestas para nós removidos e foi recusado; a espera indevida por job_id=0 foi corrigida. A entrada sem ação também aguarda o resultado quando o combate já está em Auto. Os testes de grafos fechados/sem Start e rejeição imediata passaram, assim como os testes de compartilhamento/observer (18 casos no bloco focado); `validate` confirmou 259 nós sem erros.

**Fechamento ao vivo do grupo 2:** `20261028T105459Z_f0bfc893` preserva o aviso Ras disponível, o recibo exato de ijp008 (The Final Fight, Sanctuary, Chapter 4), a abertura do Episódio 1 e Skip Tutorial. A missão de capítulo foi relida com Receive. O diário da entrada única de ijp008 foi reconciliado por essas evidências, sem replay. O aviso Ras precisou de uma primitiva observada porque o leitor legado de ingresso ainda exige os textos de Victorika; a composição posterior de tutorial de Episódio 1 também precisou de intervenção. Esses dois leitores permanecem pontos da revisão, sem promoção de reconhecedores por nome de personagem.

| Evidência privada | Resultado observado |
| --- | --- |
| `20261028T105459Z_f0bfc893/agent_000014→000016` | Skip Tutorial de Abyss reutilizado pelo acknowledge compartilhado; proposta Auto Assign reconhecida e confirmada por primitiva observada. Preparação do andar 1 com equipe CP 39638. Um primeiro pedido não enviou Start porque o CP com ponto estava desconhecido; leitura numérica corrigida sem baixar a confiança. |
| `20261028T110752Z_934de0ce` | Um Start registrado, energia 969→959, Auto positivamente ligado e mantido, vitória Floor 1. O primeiro avanço não saiu da tela, pois o banner CLEAR genérico encobria o resultado específico com Back/Next Floor. |
| `20261028T111230Z_8ff3f1fd/agent_000001` | Correção da precedência e retomada com zero Start: Back do resultado, andar 1 Conquered e andar 2 Available. Nenhum Next Floor. |
| `20261028T111230Z_8ff3f1fd/agent_000009` | Um Receive e recibo, contador 1/5→3/5, capítulo e Abyss resgatados. |
| `20261028T112001Z_b231004c/agent_000001→000002` | Equip All de Arby: prévia e confirmação 24400→28070, uma aplicação, CP final e aviso da missão. A coluna de CP foi separada do delta; o ícone ativo de Equip All substitui a legenda como alvo. Recorte nativo .94/MAE14 com glyph_min210 passou positivo e rejeitou escurecido/coberto. |
| `20261028T112001Z_b231004c/agent_000006→000015` | Hellish Essence Orb Lv85: menor opção Auto Select (+3), 5 pós e 1 Lesser Charm, custo 22400. PostClick aceito não aplicou: ouro, EXP e seleção permaneceram iguais. Após essa prova, uma única pressão Maa de 300 ms no mesmo alvo aplicou +3; ouro 1383934→1361534, EXP final 31/1050, ataque 100→160, score 32→40 e Enhance Success. O popup posterior confirmou +3. Diário preserva a tentativa sem efeito e a aplicação efetiva, sem nova melhoria. |
| `20261028T112939Z_26854028/agent_000004→000005` | Equipar e melhorar relidos com Receive; melhoria 1/1. Um resgate com recibo levou 3/5→5/5. |
| `20261028T112939Z_26854028/agent_000006` | Uma recompensa final e recibo, grupo 3 confirmado em 0/5. Missão de herói nível 20 já mostra Receive, sem novo gasto ou resgate no grupo seguinte. Conexão encerrada normalmente neste checkpoint. |

**Limites preservados para revisão:** o grupo 2 foi concluído com unidades Maa e intervenções do agente; não foi uma validação ininterrupta de `run-group`. O executor de melhoria parou antes de aplicar porque faltam os campos da composição atual e a escolha do submenu Auto Select. A aplicação acima usou primitivas observadas e orçamento finito; não habilita esse executor sobre campos desconhecidos. As saídas de Abyss, popup de equipamento e o lobby renovado também exigiram primitivas; faltam contratos de retorno para o grafo completo. O novo ponto do container de arma foi calibrado no painel 1212×682 com Equip All nativo e conferência do popup Weapon; não identifica instância nem seleção de todos os slots. Nenhuma compra de Marco/baú ou melhoria adicional foi feita.

Os pontos de releitura, custos de reconhecimento, input aceito sem efeito, atualização de evidências e retomadas estão na pauta de revisão em [mission-operations.md](mission-operations.md#roteiro-por-nivel). A suíte completa desta versão ampliada é executada após o fechamento e a desconexão; os 471 testes acima pertencem à versão anterior.

**Fechamento consolidado:** `python -m pytest -q --durations=10 --maxfail=1` — **510 passed em 584,52 s**, sem falhas/skips; uma execução completa após as alterações funcionais estabilizadas e o encerramento da conexão. `driver-epic-seven validate` — **260 nós, zero erros**. Logs em `var/group2-final/pytest-final.txt` e `validate-final.json`; checkpoint em `var/group2-final/checkpoint.json`. Esse resultado de regressão não promove o compilador de grupo ou a melhoria a ciclos autônomos validados; os limites ao vivo acima continuam aplicáveis. Próxima etapa acordada: revisão e estruturação da refatoração, antes da interface MCP.
