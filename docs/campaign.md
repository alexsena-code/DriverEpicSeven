# Campanha até um bloqueio

**Entrada vigente:** mouse 4 como padrão em `config/campaign.json`; fallback 64 apenas de forma explícita em `config/campaign-fallback.json`, após nova observação. Registros abaixo que mencionam 64 descrevem o histórico da madrugada. Nenhuma ação consumidora com resultado incerto deve ser repetida para testar outro método.

O usuário autorizou avançar a campanha até não conseguir progredir, com no máximo três entradas por fase; depois disso, pesquisar e testar outros tipos de quests dos caminhos e produzir um HTML enxuto. O limite não é autorização para repetir uma batalha de resultado desconhecido. Não há recargas ou compras automáticas.

Use o perfil explícito `--config config/campaign.json`. O catálogo `data/stages/campaign.json` deriva do pacote e inclui 382 fases de episódios 2 a 5. Isso não comprova que todas estejam acessíveis na demo. Custo `null` significa desconhecido; a compilação recusa esses trechos até haver calibração, em vez de supor entrada gratuita.

```powershell
driver-epic-seven --config config/campaign.json chapter --from-stage ake001 --max-energy 84 --timeout 900
```

`var/campaign_attempts.json` persiste as reservas antes do clique de início e eventos Maa posteriores: envio, entrada reconhecida e CLEAR de vitória. Uma reserva é conservadora e não prova derrota nem consumo. O limite permanece ao criar outra instância do driver. Ao falhar reconhecimento ou conexão, confira imagem, eventos e energia antes de retomar. Nunca apague o registro para contornar o teto.

Cada fase do grafo permite um início. Novas tentativas após derrota precisam do resultado observado e de um novo trecho dentro do limite persistente. Depois de até três derrotas reais na mesma fase, encerre a progressão de campanha e passe ao levantamento das outras quests. Bloqueio de conteúdo da demo, falta de recurso ou pré-requisito também deve ser documentado de forma distinta de derrota.

Foi observado retorno à taberna depois de vitória. O fluxo agora reconhece a taberna, restaura o HUD se necessário e reabre Episode antes de continuar a próxima fase. Uma retomada com `--finish-current` pode realizar somente essa recuperação antes dos novos inícios do plano.

O usuário informou que cutscenes podem exigir manter o mouse pressionado. A primitiva `hold --point X Y --observation <arquivo> --duration-ms 1500` usa LongPress nativo Maa e as mesmas guardas de uma observação recente; a duração é limitada a 300–5000 ms. O uso em cutscene precisa de observação real e verificação do destino. Diálogos comuns continuam com Skip/confirmar.

Títulos de capítulo e história podem ocupar várias linhas. A comparação mantém texto completo e score mínimo. Apenas em um sufixo romano explicitamente esperado (I, II ou III), os glifos finais `l` e `1` podem representar `I`; o prefixo do título e a quantidade de glifos precisam ser exatos, e o local também deve corresponder. O método usado fica na evidência.

O relatório final deve separar rotina validada ao vivo, navegação/entrada parcial, caso simulado e candidato ainda baseado apenas no pacote. Capturas completas, progresso e registros operacionais permanecem locais em `var/`.

## Incrementos observados em 26/10/2026

- O perfil de campanha usa explicitamente mouse `PostMessageWithCursorPos` (64), teclado `PostMessage` (4) e captura `FramePool` (2). O modo de mouse 4 deixou de produzir uma transição de Confirm nesta sessão; 64 foi validado antes da troca. Não há fallback automático. A comparação está em `var/input_method_comparison.json`.
- `Rank Up` é um aviso informativo: reconhecer título e mensagem de energia, aguardar a animação, clicar no rodapé e observar a próxima tela. Foi fechado ao vivo no Rank 38; a energia concedida pelo jogo não é uma recarga solicitada pelo agente.
- `Connection Unlocked` tem reconhecimento próprio e botão OK. O aviso de Tamarinne foi fechado; isso não significa que a personagem foi recrutada.
- Cutscene sem Skip visível: `LongPress` nativo de 1500 ms, com soltura do mouse, foi exercitado no capítulo 8. O destino observado foi a confirmação de pular a história.
- Algumas preparações têm `No Record` e objetivo `Clear with No Continues`. O título secundário de recorde não integra a identidade da fase. Local e título continuam exatos, com releituras de recortes quando necessário. A vitória exige o cabeçalho CLEAR e os controles reconhecidos; não depende de o segundo objetivo ser Story Clear.
- O limite global de um trecho pode chegar a 3600 s; isso não amplia a quantidade de inícios. Um timeout sem resultado visível não conta como derrota nem autoriza nova entrada.
- O capítulo 1 do episódio 3 foi concluído em uma única tarefa Maa (`20261026T043404Z_bf880e70`). Ervalen foi vencido na primeira entrada após uma fase de mais de seis minutos. As esperas de história/combate nos nós Entry, Skip, ConfirmSkip e HoldIntro passaram a 600 s; o prazo total do comando continua independente e finito.
- Em `pow005`, o pacote nomeia o local `2.5 District B Gate`, mas o painel Ready mostra `District B Gate`. Somente essa entrada foi calibrada pela captura, preservando `location_source_text`; o comparador continua exato. Não remover números indiscriminadamente: `6th District Camp`, por exemplo, permanece intacto. A recusa ocorreu antes de iniciar a fase.
- `wis010` teve a primeira derrota real da meta. O resultado foi registrado; Leave retornou ao mapa, e a nova seleção passou novamente por identidade/custo e reserva persistente. A segunda entrada venceu e abriu o capítulo 4. O capítulo 3 terminou em 30/30 estrelas. Não houve uso de Continue nem quarta entrada. Evidências: `20261026T061414Z_f07b881a` (FAILED), `20261026T061916Z_8f98fd3d` (Leave → mapa), `20261026T062006Z_047e0a0d` (segunda entrada/vitória).
- Na preparação da segunda tentativa de `dra007`, o recorte antigo de energia cortou o primeiro dígito: OCR 6, catálogo/tela 16. O custo divergente impediu a reserva e o clique de início. O recorte foi ampliado para `[912,602,110,50]`; a leitura 16/1106 foi confirmada e adicionada ao teste. A recusa de reconhecimento não foi contada como nova tentativa.

<a id="selecao-de-fase"></a>

## Seleção de fase

Perfil validado: demo Steam em inglês, área cliente 1212 × 682, MaaFramework 5.14.3, FramePool e PostMessage. Data local: 25/10/2026.

### Contrato

O agente informa um ID do catálogo em `data/stages/campaign-initial.json`. O catálogo cobre as 12 fases do episódio 2, capítulo 5, Restless City. Os dados do pacote fornecem identidade e custo; o estado da conta sempre vem da tela atual. Título da história e nome do local são campos distintos do pacote e não devem ser trocados.

| ID | História | Local | Energia |
|---|---|---|---:|
| pen001 | Outside the Walls | Northern Outskirts of Perland | 8 |
| pen002 | Permeating Darkness | Silver Fox Territory | 8 |
| pen003 | Hard Times | Fighter's Heart | 8 |
| pen004 | Thieves and Swindlers | Round Goblet Plaza | 8 |
| pen005 | Citylord | King's March Hall | 8 |
| pen006 | Eye of the Storm | Cold Snakes Territory | 12 |
| pes001 | Cold Reality | Dreaming Pioneer Hall | 8 |
| pes002 | Lone Wolf | Magic Research Agency | 8 |
| pes003 | A Gentleman's Deception | Golden Arrow District | 8 |
| pes004 | Conspiracy | Sparkling Feather District | 8 |
| pes005 | Within the Walls | Southern Stronghold | 8 |
| pes006 | Counterattack | Southern Outskirts of Perland | 12 |

```powershell
driver-epic-seven stage inspect pen002
driver-epic-seven stage prepare pen002
```

O primeiro comando só observa. O segundo termina na tela Ready, sem clicar em Start Quest. O ponto inicial aceito é o mapa desse capítulo ou a preparação da fase pedida; navegar desde a taberna não faz parte deste pipeline.

### Reconhecimento e execução

```text
Mapa: episódio + capítulo + linha com número/nome + ausência de cadeado
  → selecionar a linha
  → conferir descrição da história selecionada
  → abrir Ready
  → conferir local + nome da história
  → aguardar painel de suporte carregar e estabilizar
  → Select Team
  → conferir local + nome + custo em duas observações
```

O Maa executa os nós e suas ações. O Python fornece descoberta da janela, validações, OCR e evidência. Há rolagem limitada em cada direção, escolhida pelo número solicitado e pelos números de linhas legíveis na tela. Os cliques de seleção/preparação/início têm no máximo um disparo; cada direção de rolagem admite até três. Falha não causa repetição automática do início.

Se a fase já está selecionada, a descrição e o contexto do capítulo podem confirmar a seleção sem clicar novamente na linha. Isso evita depender exclusivamente do OCR do nome na lista; a preparação ainda precisa confirmar local e título antes de iniciar. Foi observado `Conspiracj` na lista enquanto a descrição da fase 10 estava correta; não foi introduzida aproximação de nomes para contornar isso.

O OCR inglês usa `ppocr_v3/en_us` do MaaCommonAssets. A aceitação exige score mínimo 0,90 e igualdade exata após normalizar maiúsculas, pontuação e espaços; não há aproximação por nome parecido. Esse score é uma medida do modelo, não uma taxa de acerto demonstrada. Quando a detecção das duas linhas falha, a região da linha conhecida é relida diretamente, mantendo igualdade e score. Na preparação, local e história precisam corresponder juntos.

Foram necessárias duas variantes reais do rótulo Start Quest e espera de estabilidade: a animação de entrada altera tamanho e posição do controle. Também foi observado Select Team visível durante carregamento; o driver aguarda o carregamento e a estabilidade antes do clique.

### Início e limites

```powershell
driver-epic-seven stage start pen002 --max-energy 8
```

Esse comando autoriza no máximo um clique de início dentro da execução. Exige identidade confirmada, custo igual ao catálogo, orçamento suficiente e saldo suficiente. Fase já concluída é recusada sem `--allow-replay`, que só deve ser usado quando repetir fizer parte do objetivo. Não há recarga automática, compra, escolha automática de heróis ou otimização da equipe. Uma falha após enviar entrada exige nova observação; não reenvie o comando presumindo que nada aconteceu.

O início parametrizado passou em controlador offline com capturas reais e depois ao vivo em várias fases deste capítulo. O início de `pen001` na validação inicial usou a primitiva vinculada à observação. Na progressão seguinte, as fases foram iniciadas uma vez cada; a fase 9 foi iniciada manualmente pelo usuário após ajustar o time.

Para encadear o trecho restante sem novos comandos por fase, use `chapter --from-stage <id> --max-energy <soma>`. A compilação cria um conjunto de nós por fase e conecta cada retorno ao mapa ao próximo início. [Contrato do encadeamento e retomada](campaign.md#fluxo-de-batalha).

### Evidência real

- `pen001`: uma batalha concluída com 3 estrelas, incluindo Story Clear; energia 920 → 912; progresso do capítulo 0/36 → 3/36; `pen002` liberada.
- Skip e sua confirmação foram acionados por primitivas; o destino de combate foi observado. Uma tentativa posterior foi recusada antes da entrada porque a tela havia mudado.
- Pedido de `pen001` enquanto a preparação mostrava `pen002` foi recusado antes da entrada.
- Preparação completa de `pen002` pelo pipeline: `Stage.Entry → Stage.Row → Stage.OpenReady → Stage.Supporter → Stage.CheckReady`. Todos os nós concluíram; energia 912; zero inícios.

Evidência local da preparação: `var/runs/20261026T003826Z_75f0c2dc/`. A validação cobre esse percurso observado; não prova os mesmos resultados nas outras fases, resoluções ou idiomas.

### Reinicialização e retomada

Após a queda de energia, o jogo voltou com novos PID/HWND. A descoberta encontrou a nova janela na mesma resolução. Um seletor de herói foi classificado como `unknown`; uma captura posterior confirmou `lobby_idle`, com os controles da taberna ocultos. Foram feitas somente observações após a queda.

Não retome pela última etapa salva. Redescubra a janela, descarte observações antigas para entrada e observe novamente. O combate anterior está documentado, mas progresso e recursos após reiniciar precisam ser relidos antes da próxima ação. Logs Sentry são auxiliares e podem estar antigos mesmo com a cena correta.

<a id="fluxo-de-batalha"></a>

## Fluxo de batalha

`driver-epic-seven finish-battle --timeout 300` acompanha uma batalha que já está em história, combate ou resultado reconhecido. Não escolhe nem inicia a próxima fase. A próxima entrada usa novamente `stage start <id> --max-energy <custo>` e suas verificações de identidade, energia e repetição.

O motor permanece no Maa: `resources/epic-seven/pipeline/battle_finish.json`. O driver faz preflight, fornece reconhecimento, salva evidência e exige mapa observado no encerramento.

### Reavaliar após cada ação

| Tela reconhecida | Ação |
|---|---|
| História com Skip disponível | Skip; tratar confirmação; procurar novamente história, combate ou resultado |
| Confirmação de Skip | Confirmar; só repetir se a mesma confirmação continuar reconhecida |
| CLEAR | Continuar para o resultado |
| Acquired Items | Confirmar após estabilidade do controle |
| Pedido para adicionar apoiador como amigo | Cancel, conforme preferência do usuário; nunca Send |
| Side Story Alert | Fechar por Tap to close |
| Story Clear Reward | Fechar e reconhecer novamente |
| Received Reward | Fechar e reconhecer novamente; outro banner pode aparecer |
| Aviso informativo com Tap to close | Localizar o texto por OCR e fechar; regras específicas têm prioridade |
| Mapa | Aguardar 1,2 s e reconhecer novamente antes de concluir |

História também pode reaparecer depois do combate ou do resultado. As listas `next` incluem essas alternativas; o fluxo não presume que existe apenas um Skip ou um banner. `Finish.VerifyDone` é a condição final, depois do intervalo no mapa. Não basta enviar o clique ou encontrar o mapa uma única vez durante uma transição.

### Esperas e retries

O teste real encontrou Confirm visível antes de o jogo aceitar o clique. O pipeline aguarda estabilidade da região e acrescenta uma breve espera antes de agir. Depois do clique, há tempo para a transição. Se a mesma confirmação continuar reconhecida, o Maa pode voltar ao nó; cada nova tentativa passa por reconhecimento.

Os limites por fase são finitos: até 12 acionamentos de Skip/confirmar Skip, 3 de CLEAR/resultado/amigo/Side Story Alert e 10 de cada tipo de banner ou aviso com Tap to close. O limite total de `finish-battle` é configurável entre 1 e 600 s. `var/STOP`, mudança de janela, falha de reconhecimento ou timeout interrompem o driver. Não há repetição automática do início da batalha nem recarga de energia.

### Avisos genéricos e decisões específicas

Quando nenhuma tela específica é reconhecida, o driver procura por OCR o texto exato `Tap to close`, com ponto final opcional e score mínimo 0,90, numa região de avisos já observada. O clique usa a caixa do texto reconhecido. Isso tratou o aviso Hero Friendship Level Increase sem cadastrar o título nem a imagem do herói. Um score não é uma taxa de acerto medida.

Estados específicos, como confirmação de Skip e pedido de amizade, são resolvidos primeiro. Se não houver estado específico nem o texto de fechamento, a tela permanece desconhecida. A regra genérica não escolhe opções de compra, seleção ou envio. Avisos novos com fechamento em outra região exigem nova observação.

`Rank Up` possui regra própria, pois pode exibir somente uma seta no rodapé. O OCR exige o título RANK UP e a mensagem de energia recebida; o número do Rank e a quantidade de energia são variáveis. Após 500 ms, o clique usa a caixa dessa mensagem, aguarda 800 ms e reavalia a tela; permite até três acionamentos enquanto o mesmo aviso continuar reconhecido. O caso Rank 38 foi fechado ao vivo e incluído no teste da sequência de avisos.

Rank Up e outros avisos também podem preceder o CLEAR. Em `dra008`, Rank Up → Tap to close → CLEAR revelou uma transição ausente no nó genérico. `Finish.TapToClose` passou a aceitar `Finish.Clear` como próximo estado. O novo teste de sequência reproduziu a falha antes da correção e concluiu os cinco fechamentos até o mapa depois dela; não há início de batalha nesse percurso.

### Encadear fases sem comandos intermediários

```powershell
driver-epic-seven chapter --from-stage pes004 --max-energy 28 --timeout 600
```

Esse exemplo compila as fases 10, 11 e 12 em um único grafo e faz uma única chamada `Tasker.post_task`. Ao verificar o mapa depois de uma vitória, o Maa segue para a seleção e início da fase seguinte. Cada fase tem nós próprios, identidade/custo verificados e limite de um início. O orçamento vem da soma dos custos do trecho; não há início depois da última fase catalogada no capítulo.

Para retomar de um resultado/aviso pendente da fase anterior, sem repetir seu início:

```powershell
driver-epic-seven chapter --from-stage pes005 --max-energy 20 --finish-current
```

Nesse caso, um prefixo do grafo apenas conclui a batalha/resultado atual e volta ao mapa; os únicos novos inícios são 11 e 12. O Python compila o plano e valida a evidência; as transições e ações continuam pertencendo ao Maa. Falha não dispara outro trecho automaticamente: observe o estado e selecione a próxima fase pendente antes de retomar.

### Controles com fundo variável

O fundo de uma história pode aparecer através dos controles. Comparar todos os pixels do recorte causou recusas em histórias intermediárias. O template de Skip usa a máscara verde nativa do Maa para excluir o fundo, preservando letras e bordas; a verificação adicional de pixels compara os glifos. O ícone History continua registrado como evidência auxiliar. Há capturas positivas e uma captura escurecida negativa nos testes locais.

Origem e transformação estão em `assets/template-provenance.json`. A opção de máscara e o ciclo de reconhecimento/ação são descritos no [protocolo oficial do MaaFramework 5.14.3](https://github.com/MaaXYZ/MaaFramework/blob/v5.14.3/docs/en_us/3.1-PipelineProtocol.md).

Em `wis008` (episódio 3/capítulo 3), o fundo azul elevou a diferença média dos glifos do Skip para 19,812, acima do limite anterior 18. O template Maa continuava com score 0,991728. A captura foi incluída na bateria positiva/negativa; o limite de pixels passou a 22 e as capturas negativas continuaram recusadas. A entrada já enviada foi preservada e o trecho foi retomado com `--finish-current`, sem novo início dessa fase. Esses valores são critérios locais de reconhecimento, não uma taxa de acerto estatística.

Em `dra004`, o fundo branco produziu erro 24,087 com score Maa 0,997843. A nova captura positiva foi acrescentada; o limite atual é 28. As capturas negativas avaliadas na posição desse controle tiveram erro acima de 60 e o teste de classificação continuou passando. A espera após o clique único de Start passou de 30 a 90 s; o comando isolado de início permite até 120 s no total. Esses prazos ampliam a observação, preservando `max_hit=1` no início.

### Evidência e limites

O teste offline simula clique ignorado em confirmação e resultado, histórias antes/depois do resultado, Side Story Alert, pedido de amizade e dois banners iguais consecutivos. O percurso real de Citylord executou quatro Skips, cancelou a oferta de amizade e retornou ao mapa; a fase 6 também concluiu o percurso completo. Os novos avisos foram inicialmente tratados por retomada do mesmo resultado, sem repetir combate.

`live.json` e `live.png` na pasta da execução são atualizados aproximadamente a cada três segundos durante reconhecimento. São uma observação recente para acompanhamento; não substituem as guardas e capturas vinculadas a uma ação. Capturas e dados da conta permanecem fora do Git.

### Derrota observada

Em `wis010`, a tela FAILED foi observada ao vivo. O reconhecimento exige três elementos: cabeçalho, Leave e Try again. O OCR do cabeçalho estilizado produziu `FAIVLED`; essa grafia observada é aceita junto de FAILED, com score mínimo 0,90 e os outros dois controles obrigatórios.

`Finish.Defeat` encerra o grafo com DoNothing e registra a derrota na mesma reserva de entrada. Não aciona nenhum dos botões dessa tela. A primitiva `defeat_leave_text` foi validada ao vivo para retornar ao mapa; uma nova entrada precisa passar pela seleção, identidade, custo e limite persistente. O teste offline exige zero entradas de interface no percurso de derrota.

Ícones de combate também têm fundo variável: a captura local apresentou score 0,86544 para pausa e erro de glifos 1,5. O limiar do template passou a 0,84 e a comparação de pixels de pausa/ajuda usa os glifos; ambos continuam obrigatórios. A captura e os negativos foram incluídos nos testes.

Esta capacidade não escolhe melhorias de equipe, não resolve inventário cheio, falta de energia ou alertas com decisão nova. Uma tela nova exige inspeção e calibração dentro do objetivo autorizado.

<a id="planejamento-de-tres-estrelas"></a>

## Planejamento de três estrelas — próximo incremento

Acompanhamento: [ALE-190](https://linear.app/akxl/issue/ALE-190), parte da [ALE-185](https://linear.app/akxl/issue/ALE-185).

**Estado em 26/10/2026:** navegação, início único, combate/história, retorno e encadeamento de aventura foram validados no escopo de [validation.md](validation.md). Aventura com 3★ em todas as fases continua **parcial**: `dis003` terminou com duas estrelas e a cadeia avançou; o driver não lê todas as condições/estrelas nem escolhe a equipe para satisfazê-las. Vitória e três estrelas são critérios diferentes. O episódio 2 foi concluído e o episódio 3 abriu; isso não comprova todos os objetivos de estrela.

**Escopo escolhido pelo usuário:** obter 3★ durante a progressão das próximas fases, preparando as condições antes da entrada. Não auditar nem reparar agora estrelas de fases já concluídas; `dis003` é apenas evidência histórica da lacuna.

**Unidade ao vivo posterior:** `epi009` (Hidden Plan, Secluded Laboratory) foi concluída com os três objetivos marcados no CLEAR em `var/runs/20261026T232625Z_eef54186/018_Finish.Clear.png`. A preparação confirmou Initial Clear, Clear with No Continues e Have 1 Ice Hero in the Team; Sigret Ice estava na formação de CP 506.208, sem troca necessária. Uma entrada consumiu 16 de energia (1.012 → 996), com Auto, Skips e retorno ao mapa confirmados; não houve Continue. Essa unidade valida planejamento e conferência visual manual por primitivas/pipeline existente, não um planejador genérico de estrelas na árvore. Uma solicitação anterior foi bloqueada por inventário de artefatos cheio antes da entrada; sua reserva `sent` foi preservada, sem promovê-la a derrota ou apagar o histórico. O usuário resolveu a capacidade e pediu novo início. A meta continua preparar próximas fases conforme a progressão do Herdeiro nesta mesma conta.

### Fontes e diagnóstico

[star-requirements.json](../data/stages/star-requirements.json) cruza `level_enter_adventure.mission1..3`, `mission_data` e textos para as 382 entradas de `steam-campaign.json`. Há 1.092 condições: 379 de conclusão, 273 sem Continue, 199 de elemento, 165 de sobrevivência e 76 de história. São ocorrências de condições, não quantidades de fases distintas. Dezoito entradas têm as três referências vazias e permanecem parciais.

- `lfs001`: conclusão + sem Continue + ao menos um herói Fire (`attribute=fire,count=1`).
- `dis003`: conclusão + sem Continue + ao menos três heróis sobreviventes (`aliverole=all,count=3`). A vitória de duas estrelas é evidência histórica; investigar ou repetir essa fase não faz parte do objetivo atual.
- Fora desse recorte, o pacote também tem requisitos por classe, eventos e limite de turnos. Não ampliar uma regra de elemento a todas as condições.

### Lógica proposta, ainda não implementada

Conferência pontual em 26/10/2026: a seleção de apoiador de `epi009` (Hidden Plan, Secluded Laboratory) exibiu exatamente `Initial Clear`, `Clear with No Continues` e `Have 1 Ice Hero in the Team`, iguais às três referências estáticas. A tela mostrava `No Record`; os ícones dourados ao lado dos textos não foram interpretados como objetivos já conquistados. A leitura foi encerrada sem selecionar equipe nem iniciar a fase. Isso confirma os textos antes da entrada, não a obtenção de 3★ nem a integração automática dos objetivos na árvore. Evidência privada: `var/runs/20261026T192147Z_72af049c/agent_000107.{json,png}`. O `16 AP` mostrado nas recompensas não é prova de custo de energia.

1. **Resolver a próxima fase do percurso e ler seus três objetivos antes da entrada.** Preservar identidade, cada estrela/objetivo e estado `completed`, `pending` ou `unknown`, com origem e idade. Usar o pacote para preparar a leitura e conferir o texto atual; divergências ou condições desconhecidas impedem prometer 3★.
2. **Planejar os três objetivos para a mesma entrada.** Traduzir condições conhecidas em restrições: quantidade por elemento/classe, sobreviventes mínimos, história, Continue e turnos. Confirmar como apoiadores/trocas/heróis de teste contam antes de depender deles. O plano não deve depender de acumular objetivos em repetições nem fazer levantamento de pendências antigas.
3. **Ler o elenco real e propor a menor troca de equipe.** Cruzar IDs e `ch_attribute`/`role` de `character_player` com instâncias possuídas e observadas. Preferir preservar o núcleo capaz de vencer e trocar poucos slots; satisfazer elemento/classe não prova força ou sobrevivência. Sem candidato conhecido, retornar o requisito faltante; não invocar, melhorar ou equipar automaticamente.
4. **Preparar e conferir antes do início.** Registrar equipe anterior, aplicar apenas alterações autorizadas, reler slots/elementos/classes, custo e fase e então admitir uma entrada. Calibrar a seleção de equipe e o apoiador separadamente. O atual `check_start` verifica identidade/custo/repetição, mas ainda não valida esse plano de estrelas.
5. **Conferir cada objetivo depois da batalha.** Ler estrelas e condições no resultado e/ou preparação/mapa após o retorno. Três estrelas exigem prova vinculada à mesma fase; CLEAR isolado não basta. Registrar o resultado por objetivo e só marcar a fase como concluída no percurso de 3★ quando as três estrelas estiverem comprovadas.
6. **Tratar desvio antes de continuar.** Se uma próxima fase terminar com menos de 3★ ou resultado desconhecido, pausar o encadeamento e registrar a causa observada para decisão; não transformar vitória em sucesso de 3★ nem iniciar replay automático. Manter o diário de entradas, custo e limites. Não criar fila de reparo das fases anteriores. O orçamento da futura execução é de progressão planejada, sem reparo retroativo incluído.

Implementar como extensão da `ui_tree`, do catálogo e das primitivas/pipelines Maa existentes, com eventos de equipe e objetivos; sem segundo loop de captura ou modelo paralelo de progresso. Começar por testes offline de interpretação e seleção de candidatos, positivos/negativos de leitura e preparação sem combate; validar uma unidade ao vivo somente dentro do plano autorizado. Esta sessão fez análise offline e documentação, sem alterar equipe ou iniciar batalhas.

## Prólogo STOVE no roteiro do Caminho — 27/10/2026

`data/stages/adventurer-prequel.json` resolve 30 identidades estáticas por `mission_data` e preserva títulos/localizações e proveniência. Por exemplo, tar007 usa a localização A Rift in the Frustration e título One Last Strike; tar008 usa Fate's Crossroads e Failed to Protect. A preparação precisa provar os dois textos e o custo atual. Histórias gratuitas conhecidas têm um ramo próprio: capítulo, descrição atual, linha e View Story antes de uma entrada; Skip/hold e confirmação compartilhados, recibo identificado e retorno ao mapa. Custo desconhecido continua recusado.

`path campaign` compila um trecho contíguo do mesmo capítulo com orçamento total, um Start máximo por fase, Auto somente diante de HUD positivamente desligado e resultado 3★ antes do retorno. `path finish-stage` retoma somente uma entrada pendente, sem nós de início. A trava persistente recusa repetir uma fase registrada por um pedido novo. Não existe reparo retroativo ou replay automático.

O grafo de retomada remove também os nós de entrada que referenciavam seleção/preparação removidas. Suas arestas precisam permanecer fechadas; uma recusa Maa (`job_id=0`) falha imediatamente, sem consultar um job inexistente até o timeout. A entrada sem ação pode aguardar um combate já em Auto dentro do prazo finito do pedido. A preparação de ijp007 observada apenas com Genesis Ras convidado não iniciou; acrescentar um herói possuído resolveu aquele caso. Isso não estabelece uma exigência de quatro integrantes. O retry autorizado foi reconciliado individualmente no diário com prova da equipe corrigida, energia e identidade da janela; não é recuperação automática de Start incerto.

As unidades tar007/tar008 foram iniciadas uma vez cada, custo de 8 de energia por fase, com três condições cumpridas; o capítulo 3 alcançou 15/15 estrelas. A primeira entrada usou mouse64; tar008 usou mouse4, que também passou na seleção e no retorno à preparação. O fechamento encontrou Rank Up, histórias, desbloqueio de Abyss e recompensas. Pausas para calibração e retomadas têm zero Start. Esse percurso não comprova o encadeamento longo, o restante do prólogo ou a preparação automática de equipes para objetivos diferentes.

