# Atlas → experimento Sol/Terra/Lua — contrato prévio

FatiaC2-01,13/10/2026. Copiar os três estados geométricos simultâneos JPLDE442s
na época explícita UTC/TDB doAtlas. O comando pausa/confirma essa época e cria
uma ramificação nova, inicialmente pausada. Dados incompletos/inválidos são
recusados antes de alterar o motor/worker. Não editar a referênciaJPL.

Solver: massas pontuais newtonianas, REBOUND/IAS15, sem colisões. Sol10,
Terra399 eLua301 recebem IDs exp:<ramificação>:naif:<id>, preservando IDs
sol:naif:<id>, nomes, vetores originais, kernels/hash/fontes e cobertura.
Cada propriedade tem unidade/origem e desconhecido explícito. Fonte não
publica incerteza local para as posições/velocidades nem para o recorteGM:
guardar ausência, não zero ou número observado inventado.

GM usa os valores emkm³/s² publicados nos comentáriosDE442 fixados: GMSparaSol,
GM3paraTerra eGMMparaLua (GMB é Terra+Lua, não usar como massa daTerra).
Converter por10⁹paraSI; massacanônica=GMcorpo/GM0, ondeGM0é a unidade nominal
IAU já fixada. Não substituir o GM ajustado do Sol pelo nominal. MassaSI=GM/G
comGCODATA; a incerteza deG é só uma contribuição, não incerteza total de massa.

Referencial científico: eixosJ2000/ICRF, origem no baricentro inicial do
subconjunto de três corpos, com translação/velocidade de origem noSSB preservadas.
Transformação inversa inicial: rSSB=rCOM0+L0·r;vSSB=vCOM0+V0·v. A origem segue
movimento inercial uniforme no modelo reduzido. Tempo do experimento começa
emzero; épocaTDB inicial fica registrada, sem confundir duração comUTC.
Visualização continuaGALACTIC: aplicar matrizJ2000→GALACTIC na borda gráfica,
sem transformar vetores científicos ou alterar a fonte por movimento de câmera.
Marcadores ampliados e grade são auxílios de exibição, sem raio de colisão.

Excluir demais planetas/luas/asteroides, relatividade, J2/marés materiais,
radiação e evolução estelar. O modelo reduzido não reproduz a efemérideJPL
indefinidamente. Comparação inicial usa o mesmo estado; integração valida
equaçõesnewtonianas, não atribui divergência deJPL a erro numérico do integrador.
Estados/fontes/transformações/GM e controles sobrevivem a checkpoint com
hash de metadados, binário e escalaSI. Carregar geração diferente informa
diferença; corrupção/contrato incompatível recusa antes de substituir a sessão.

Critérios registrados antes da implementação:
- Cincoépocas1950/2000/2026/2030/2050: igualdade de época/IDs/fontes, inversa
  de posição≤1mm e de velocidade≤1e-8m/s; resíduoCOM ponderado proporcional ao
  arredondamento float64, GMcanônico coerente com unidadeSI.
- Força/aceleração inicial conferida por superposiçãoSI independente e
  evolução curta comSciPyDOP853 independente: diferença≤10m em24h, separando
  erro numérico de exclusão de fontes e da diferença paraJPL.
- Recusa de estado inválido/GM ausente/ID/referencial/época incompatíveis sem
  alterar sessão; checkpoint/retomada mantém estado/origem e transformações.
- FluxoHTTP/worker/renderer: comando retorna primeiroestado confirmado e
  pausado, IDs e datas visíveis, edição de massa atua na ramificação correta,
  retornoAtlas preserva os objetosJPL e a época congelada.
- UI nativa/câmera do sistema e regiãoTerra–Lua, imagens revistase medição
  de coordenadas do renderer contra a transformação declarada. Não substituirG0.

Estado13/10: fatia implementada e verificada, sem declarar aceite integralC2-01.
app/atlas_import.py prepara/valida, session.py guarda checkpoint esquema2,
worker/laboratory/API eUI entregam a cópia pausada. GMorigem permanece separado
da massa editada e os IDs da ramificação sobrevivem à retomada.

verify-atlas-import.py: cinco épocas, inversa máxima1,526e-5m e3,638e-12m/s;
superposiçãoSI com diferença2,56e-12m/s²; DOP853 independente24h com diferença
máxima0,0002442m e conservação de energia3,26e-16rel. Seis payloads inválidos
recusados sem mutação. Checkpoint exato, corrupção recusada e geração alterada
identificada. Regressões verify-session/verify-canonical-units passaram.

verify-native-atlas-import.py: CEFreal, coordenadas locais iguais à transformação
declarada, massa aplicada ao IDexp, reinício original, checkpoint/retomada,
retornoAtlas preservado eP32/P128 funcionando. ZeroerrosJS. Imagens system,
earth-moon eprovenance revisadas; rótulos e enquadramento corrigidos. Terra/Lua
compartilham um rótulo na escala solar e têm rótulos separados na vista próxima.
LabFrame e labels são auxiliares do renderer, sem alteração do estado físico.
Um falso negativo do teste de massa veio do preenchimento sem foco sendo
sobrescrito pelo polling; teste mantém o campo em foco como entrada do usuário.
Recibos: evidence/atlas-import-check.json, native-atlas-import-check.json e
atlas-import-visual-review.json. Último teste restaura ponteiro de checkpoint
do usuário e deixa Atlas/P32 pausado. Não é benchmark nem aceiteG0 novo.
