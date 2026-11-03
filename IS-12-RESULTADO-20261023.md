# IS-1/2 — candidata isolada e propagação de quatro centros

Trabalho de23/10/2026. A candidata fica em `output/is12-solar-product`.
Os82arquivos instalados3.13 e o ponteiro `user/sessions/latest.json` foram
preservados; a base anterior foi arquivada antes das alterações. Candidata J
e seus aceites/recusas permanecem separados.

## Resultado numérico já auditado

Foi executado o modelo newtoniano reduzido Sol10/Terra399/Lua301/Júpiter599,
com o GM físico do planeta e apenas o subset599/5 previamente fixado.
Condições iniciais idênticas à fixtureSI de11/10/2026 12hUTC.
Referencial: baricentro inicial dos quatro centros, eixos J2000;
translação/velocidadeSSB preservadas para inversão.

O IAS15 de produção foi comparado com DOP853/SI independente durante30dias,
em121leituras comuns, a cada6h. Receita e limites de
`IS-2-VALIDACAO-PREVIA.md` foram congelados antes da captura. O refinamento
usa epsilon1e-12 e uma saída intermediária a cada3h, produzindo485passos
em vez dos246da produção; não é apenas repetir o mesmo caminho numérico.

| Medida | Resultado máximo | Limite prévio |
| --- | --- | --- |
| Posição, por componente | 0,000682122m | 10m |
| Velocidade, por componente | 1,555×10⁻⁹m/s | 10⁻⁵m/s |
| Refinamento de posição | 0,000113687m | 1m |
| Deriva relativa de energia, produção | ≤1,19×10⁻¹⁵ | 10⁻⁹ |
| Deriva normalizada de momento linear, produção | ≤1,62×10⁻¹⁶ | 10⁻¹⁰ |
| Deriva normalizada de momento angular, produção | ≤2,69×10⁻¹⁶ | 10⁻¹⁰ |

São erros de concordância numérica no mesmo modelo reduzido; não representam
precisão frente ao Sistema Solar observado ou às efemérides completas.
A normalização de momento usa escalas físicas não nulas, sem dividir pelo
momento total quase zero. O auditor recalculou os balanços por outro percurso.

Também passaram17recusas sem mutação,12contribuições de aceleração
recíproca, checkpoint/ramificação/reinício exatos e o verificador legado de
três corpos em cinco épocas, executado contra a candidata com saída própria.
O importador `atlas_sun_earth_moon` foi preservado byte a byte.

## Recibos e interrupção

`is12-solar-check-20261023a.json` terminou sem aceite por falta do guard de
revisão/instante no pedido de ramificação do harness. A propagação já havia
sido calculada; não houve falha demonstrada no solver.

`is12-solar-check-20261023b.json` conserva a receita corrigida e as séries
completas, mas ficou com `completed=false` por interrupção do servidor antes
da gravação final. Esse recibo não foi reescrito como se tivesse concluído.

O auditor separado `evidence/is12-solar-audit-20261023b.json` tem
`accepted=true`: verificou fontes/hashes e toda a série preservada,
recalculou os balanços e executou novamente checkpoint/ramificação/reinício.
Conferiu ainda o resultado legado e a preservação do instalado/ponteiro do dono.
As séries e as fontes executadas estão em
`output/is12-solar-check-20261023b`.

## Estado da integração do produto

Formato novo `solar_four_physical_centers/1.0.0`, despacho separado para o
legado, IDs físicos e procedência/GM/cadeias de cobertura implementados na
candidata. A interface/API dos quatro centros e a leitura de gravidade por
fonte estão em construção. Não há ainda aceite de jornada nativa, imagem
ou desempenho. Nenhuma promoção do instalado foi feita.

Próximo: verificar a API/cadastro e as leituras novas, abrir a candidata com
armazenamento próprio, conferir quatro traduções nativas/seleção/câmeras,
pausa/avanço/reinício e persistência. Preservar rótulos de quatro centros,
fontes e ausências de acoplamento EM/nuclear. Comparação com JPL é erro de
modelo separado. A lacuna de diagnóstico da recusa J permanece pendente.


## Continuação23/10 — API, jornada nativa e erro de modelo

A jornada `evidence/is12-native-20261023c.json` terminou `completed=true`,
`accepted=true` no CEF real. Foram verificados referência de quatro centros,
11 recusas de API/leitura sem mutação de fase, importação pausada, quatro
seleções/câmeras, leituras passivas com três fontes por corpo, pausa/evolução,
marcação de amostra obsoleta, save/load, ramo/reinício exatos, recarga do CEF,
retorno ao Atlas e compatibilidade com a importação legada de três corpos.
As três comparações de posições locais nativas tiveram diferença zero na
serialização consultada, dentro do limite prévio de1mm. Não é benchmark.

A execução A parou por campo ausente no próprio harness de captura. B
percorreu a jornada até a volta da cópia legada e parou porque tentou clicar
no botão solar ainda desabilitado enquanto a UI terminava de atualizar.
As duas evidências continuam sem aceite. C usou espera explícita de botão
habilitado; a candidata também passou a restaurar o botão no fim do comando.
Fontes de todas as execuções estão arquivadas nos diretórios respectivos.

A imagem inicial revelou enquadramento baseado só em Sol/Terra apesar do
baricentro visual incluir Júpiter. A câmera solar agora considera os quatro
centros e identifica Sol, Júpiter e Terra/Lua, agrupados apenas no rótulo da
visão geral. Seleção e evolução continuam individuais. Outra revisão do
quadro Terra/Lua está sendo verificada em geração nativa posterior; C não
é aceite antecipado dessas alterações posteriores. As esferas ainda são
marcadores didáticos ampliados, sem textura científica de Júpiter.

`evidence/is2-invariance-20261023a.json` passou: translação de até3e11m e
velocidade comum1234/−5678/910m/s durante30dias/121saídas. Erro máximo de
componente após inversão:0,455mm de posição e1,16e−9m/s; separações por par
≤0,512mm. Receita fixada em IS-2-INVARIANCIA-PREVIA.md; não é relatividade.

`evidence/is2-jpl-model-20261023b.json` completou a comparação separada da
série numérica B já auditada, sem refazer a propagação. Receitas e hashes
fixados em IS-2-COMPARACAO-JPL-PREVIA.md. Foram usados instantes TDB exatos,
SSB/J2000/NONE, centros10/399/301/599 e inversão com velocidade da origem.
A tentativa A foi recusada no harness por leitura JSON sem UTF-8 explícito;
seu recibo permanece incompleto. A execução B conserva as duas gerações de
código do catálogo e exige igualdade dos dados/modelos, exceto esse hash.

Máximos de módulo do resíduo de posição contra JPL nos30dias: Sol172,220km,
Terra574,671km, Lua573,740km e Júpiter2212,741km. Resíduo relativo Terra–Sol
738,661km; Lua–Terra3,473km no máximo e3,064km no final; Júpiter–Sol2372,210km.
Esses resíduos medem diferença do modelo reduzido para as efemérides; não
aplicar o limite de10m entre integradores, nem atribuir todo resíduo a uma
causa única. Séries completas e gráficos com procedência estão em
output/is2-jpl-model-20261023b e output/is2-jpl-figures-20261023.

Instalado3.13 e ponteiro do dono continuam preservados. A candidata usa seu
próprio armazenamento e nenhuma promoção foi feita. EM/nuclear não foram
acoplados. Faltam revisão visual final100/150%, perfil próprio, retomada
após encerramento completo e as fatiasIS-3–6.


## Fechamento funcionalD e reinício completo

A jornadaD `evidence/is12-native-20261023d.json` completou e passou com a
câmeraTerra/Lua ancorada no ponto médio do par e rótulos afastados dos
marcadores, sem mover os estados físicos. As posições do ponto médio seguem
o mesmo snapshot quando há evolução. CapturaD revista: nomesTerra/Lua
legíveis, ambos os centros enquadrados. Não é aceite de todas as imagens.

`evidence/is12-restart-20261023a.json` completou com aceite. Os processos
OpenSpace25712→22460 e servidor também mudaram no encerramento normal.
Checkpoint não mudou, fase/corpos/fontes/geração foram restaurados exatamente,
com posições locais nativas iguais na consulta. Controles em100/150% foram
executados, mas a captura150 ainda pede conferir o rótulo junto ao centro:
a imagem capturada mostravaLua comTerra selecionada. Registrar isso como
pendência visual, mesmo com contrato funcional de reinício aprovado.

O perfilA completou três janelas e foi RECUSADO pelo auditor. A primeira
soma61,033836s em vez dos60s ±0,5s; houve quatro pausas de aproximadamente
0,98s em cada janela,12ao todo. O runner abria/fechava conexãoLua em cada
consulta; as pausas coincidem com esses pontos. RunnerB usa conexão
persistente, mantendo produto/fontes/limites. A comparação está em execução
neste registro; não é aceite antecipado. Recibos/sourcearchives deA intactos.

IS-3 teve uma primeira função passiva emoutput/is3-solar-staging/solar_tides.py,
sem tocar a candidata ativa durante o perfil. Contrato próprio anterior
IS-3-MARES-VALIDACAO-PREVIA.md.72casos contraDecimal70dígitos passaram em
`evidence/is3-tides-staging-20261023a.json`, junto de deslocamento0 exato,
limite linear/refinamento e cinco recusas de vetores inválidos. Sem alteração
da fixture. Falta ampliar recusas/guard e ligarAPI/UI: isso não aceitaIS-3
nemIGRF/JRM33, nem resposta de deformação ou maré oceânica.

Os guards do instrumento de maré staging também passaram25recusas em
evidence/is3-tide-guards-20261023a.json, sem mutação. A função científica
permanece com AST idêntica à dos72casosDecimal arquivados. API/UI ainda
não integradas. A validação de guard usa snapshot confirmado; não aceita
revisão/instante/frame/token obsoletos nem booleanos usados como números.


## PerfilB concluído e auditado — sem promoção

`evidence/is2-native-profile-20261023b.json` completou as três execuções de
30s de aquecimento e60s de captura. Auditor separado
`evidence/is2-native-profile-audit-20261023b.json` accepted=true.
As94fontes comuns e o executável são idênticos aA; a diferença controlada é
o transporte persistente do runner. B não apresentou as pausas de fechamento.

Medianas13,3745/13,3766/13,3859ms;p95máximo14,4681ms;p99máximo15,0181ms;
nenhum intervalo>100ms nas três janelas. Ritmo mínimo1,00023unidade/s.
Cada janela teve4499intervalos válidos e durou60,0066–60,0077s na somaSGCT.
RAMsomada máxima1,02519GiB e GPUdedicada somada2,97577GiB;66amostrasGPU por
janela cobriram toda captura, sem erro de contador e abaixo do orçamento
DXGI. Somatórios preservam a limitação de páginas/alocações compartilhadas.
Esse aceite cobre essa cena de quatro monopolos com leituras fixas eCEF,
semEM/nuclear/mapas3D e sem substituirG0 ou perfisJ.

A seleção foi investigada após a captura150 suspeita. Em100/150%, a consulta
nativa confirmou âncoraTerra, textoTerra e somente seu rótulo habilitado no
recibo is12-selection-label-diagnostic-20261023.json. Ainda conferir uma
captura após confirmação de renderização antes de encerrar a revisão visual;
o estado nativo correto sozinho não reinterpreta a imagem antiga.

Nova consulta de cota nesta retomada:97%5h/52%semanal,observed
2026-10-23T16:18:02.779Z. O0%antigo era de janela encerrada às15:59:09UTC;
nenhum valor antigo deve ser tratado como saldo atual. Construção continua.
