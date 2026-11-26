# C2-11 — campo e instrumentos gravitacionais

Contrato inicial, 14/10/2026. Continuação autorizada do editor C2-06.
A sonda básica já lê g e Φ em um ponto congelado; não fecha este marco.
A primeira fatia seguinte integra o mesmo avaliador a sondas persistidas e
amostras 3D de campo/maré. J2, marés materiais, ressonâncias e perfis ampliados
recebem seus ensaios próprios antes de qualquer aceite completo.

## Avaliador e domínio

Usar uma única função float64 de fontes ativas para leituras, vetores,
potencial e tensor de maré. Gravitação pontual sem softening:
`g = Σ GM d/r³`, `Φ = −Σ GM/r`,
`T_jk = ∂g_j/∂x_k = Σ GM(3 d_j d_k/r⁵ − δ_jk/r³)`.
O tensor mede aceleração diferencial por deslocamento, em s⁻²; não é força
ou deformação material. Fora das fontes seu traço é zero, salvo arredondamento.
Gradiente g = −grad Φ; eixo do autovetor não tem sinal único. Campo nulo tem
vetor zero e direção indefinida. Φ usa zero no infinito para o conjunto finito.
Manter limite singular mínimo de 1 mm e devolver motivo por amostra inválida;
jamais inventar zero ou NaN para permitir uma camada visual.

Amostras têm instante, revisão, IDs ativos, geração, referencial e unidade SI.
A exibição pode transformar e quantizar; dados físicos originais permanecem
float64. Setas normalizadas têm comprimento gráfico convencional e legenda.
Mapa de magnitude oferece linear/log, sem aplicar log a componentes com sinal.
Linhas integrais de campo não são trajetórias de partículas.

## Sondas e persistência

Definições separadas das massas: ID estável, nome, posição SI fixa OU corpo
seguido e deslocamento em eixos inerciais. Seguir não significa co-rotação;
a opção presa ao corpo exigirá transformação quaternion explícita.
Remoção da fonte seguida torna a sonda indisponível, com ID original mantido;
não passa a seguir o corpo que herdou um índice. Não produz massa ou reação.
Amostragem não zera referências de conservação e não reinicia IAS15.

Checkpoint sela definições e escolhas de campo. Cargas antigas recebem lista
vazia declarada; recusar definições inválidas antes de instalar qualquer estado.
A configuração tem revisão própria para evitar formulários antigos sem contar
como intervenção de energia/momento. Reiniciar o sistema segue política
explícita de descarte; salvar/retomar conserva definições e exibição.
Uma leitura guardada é marcada como antiga após edição/evolução. Leituras ao
vivo são confirmadas pelo worker, sem calcular silenciosamente no navegador.
Exportação inclui definições e amostras, não só os pixels de uma captura.

## Geometria 3D e experiência

Casca de direções distribuídas pela esfera e cortes móveis ortogonais/rotados;
setas calculadas em cada ponto, sem folha elástica. A legenda separa direção,
magnitude, escala gráfica e limites. Mostrar, esconder ou alterar densidade
não muda a evolução. Selecionar uma amostra consulta o mesmo avaliador.
Sondas fixas e seguindo corpos podem ser comparadas por distância, Δg e
aceleração diferencial. Curvas temporais indicam cadência, janela e lacunas;
não interpolar uma passagem singular como dado medido.

## Verificação e aceite

Conferir massa isolada, simetria e superposição, invariância de translação e
covariância sob rotação, −grad Φ e grad g por diferenças finitas, autovalores
radiais (2,−1,−1)GM/r³, traço fora das fontes e domínio singular. Comparar
aceleração de uma massa ativa (auto-termo excluído explicitamente) com a do
solver no mesmo instante. Amostras visuais/sondas devem coincidir numericamente.

Testar checkpoints antigos/novos, corrupção sem mutação, fonte removida,
formulário antigo e ausência de mudanças físicas por controles de exibição.
Jornada nativa: criar/fixar/seguir/medir/exportar/retomar uma sonda, mover corte,
orbitar a casca 3D e comparar duas leituras com tempo/legenda visíveis.
Medir custo por quantidade de fontes/amostras, fila/cadência efetiva, RAM/GPU e
responsividade; não adicionar trabalho científico ilimitado a cada quadro.

J2 deverá usar R de referência, eixo/spin, coeficiente e origem identificados,
com potencial e aceleração derivados coerentemente e precessão analítica de
referência. Marés de equilíbrio exigem modelo material/dissipação e energia
interna contabilizada. A referência Lagrange usa o problema circular restrito;
em estados gerais declara aproximação e referencial girante. Perfil256 e
10 mil partículas sem gravidade mútua são separados do P128, sem trocar massas
ativas por marcadores ou chamar partículas de teste de corpos autogravitantes.

## Candidato para efeitos adicionais: pesquisa pontual

Consulta primária em14/10/2026: [REBOUNDx, efeitos](https://reboundx.readthedocs.io/en/latest/effects.html#gravitational-harmonics).
A documentação consultada se identifica como5.1.0. gravitational_harmonics
aceita J2/J4, raio equatorial e eixo arbitrário; o spin fica prescrito e a
reação de torque sobre ele não é contabilizada. Portanto, esse operador
isolado não comprova conservação do momento angular total órbita+spin.

[tides_spin](https://reboundx.readthedocs.io/en/latest/effects.html#tides-spin)
usa maré com atraso temporal constante e pode evoluir spin quando há momento
de inércia dimensional. Raio, Love k2, eixo e atraso são parâmetros do modelo.
Nenhum desses operadores foi instalado ou incorporado ao worker nesta etapa.
A compatibilidade com REBOUND5.2.2/Windows e a persistência devem ser testadas
em ambiente separado; não atualizar a dependência científica fixada por
conveniência. A relação entre Q e atraso exige conferir a convenção no artigo
antes de usá-la, pois o texto online consultado contém uma expressão ambígua.

## Preparação anterior dos candidatos

Em14/10, output/c211-staging contém avaliador/tensor, definições de até16sondas,
Session/worker/ponte/interface candidatos e geometria de setas/cortes.
Configuração separa revisão física e revisão dos instrumentos; replay de
eventos valida IDs emitidos e removidos. Seguir conserva o ID mesmo após
remover a fonte. Exclusão da própria massa é explícita, inclusive no export.

O ensaio da Session candidata passou fixture32, cópiaAtlas e sistema do usuário,
21guards antigos e21corrupções sem instalar estado inválido; fase/binário/
ponteiro/referências físicos ficaram idênticos nas operações de instrumentos.
Leituras carregam um único snapshot global de fontes SI, sem repetir todas as
contribuições por sonda em cada atualização da interface. Ainda faltam promoção,
geração3.5, reinício e jornada CEF nativa; o produto continua3.4 por enquanto.

Cortes candidatos usam17×17 ou21×21amostras e contornos de interpolante linear
triangulado. Contra uma massa isolada, diferenças de raio de2,431% e1,481%;
a leitura física nos pontos permanece separada da aproximação da curva.
Uma malha11×11 deu5,62% e foi retirada desses perfis. Células singulares ficam
com lacunas; potencial constante no nível solicitado não inventa um contorno
único. Nenhuma dessas curvas ainda aparece na interface do produto.

## Integração local 3.5/3.6 — 14/10/2026

A preparação acima foi promovida: sondas3.5 passaram pela jornada CEF nativa
P32/Atlas; campo3D/cortes3.6 também estão instalados. Até128direções na casca,
cortes17×17/21×21 rotados/deslocados, setas normalizadas e equipotenciais
trianguladas aparecem na cena. Cor de |g| oferece linear/log; a legenda informa
unidade, níveis de Φ, comprimento gráfico e lacunas. O cálculo ocorre sob pedido
no worker, com limite569pontos somando os dois lotes; nunca em cada quadro.

Configuração do mapa tem revisão/histórico próprios e é selada no checkpoint.
3.5 migra com mapa vazio;3.6 sem definições é recusado antes de instalar estado.
Centro pode seguir ID com offset inercial; fonte removida não é reatribuída.
Leitura antiga fica marcada. Mostrar/esconder/consultar/limpar preserva evolução.
Poll envia resumo8,5–9KiB; fontes SI e amostras completas permanecem disponíveis
para consulta/export, sem repetição por quadro da interface.

verify-field-layers passou massa isolada/P32/Atlas/P128,68comandos rejeitados e
24corrupções seladas sem mutação; binário e ponteiro exatos. Valores de g/Φ/T
coincidiram exatamente com sonda pontual. P128/569pontos levou~691ms nesse ensaio.
As provas matemáticas instaladas mantiveram erros do tensor/contornos registrados
acima. A jornada CEF passou massa isolada/P32/Atlas: mover/girar/esconder,
selecionar leitura, exportar, salvar/restaurar, stale e âncora segura na troca.
Imagens evidence/cosmos2-fields-{single,fixture,atlas}.png revistas localmente.
Erro da geometria float32<=7257,492m nesses mapas de extensão~3e10m, dentro do
recibo gráfico; leituras SI float64 permanecem separadas dessa aproximação.

Perfil c211fields1 foi medido, mas recusado em uma parte p95=25,0158ms>25:3×60s/30s/1080p,128massas ativas com569amostras
congeladas visíveis, RAM/GPU e20pausas. Cinco releituras são temporizadas fora
das janelas formais. Não substituir P128/G0 congelados do C2-06 nem concluir
perfil256/10mil por esta coleta. Faltam séries/comparação/ramos/J2/marés/
ressonâncias e perfis ampliados para o aceite completo de C2-11.

Continuação: fields2 também recusado; falhas/fontes preservadas. A/B pausado
e evoluindo não isolou custo culpado do mapa. Tracing após reinício128/semcampo
p95 20,553ms semhitches; perfil fresco c211fields3 aprovado/auditado:
128massasativas+569amostrascongeladas, p95<=22,264ms/p99<=27,325ms/zero>100ms/
20pausas<=51,786ms. RAMsoma1,55343GiB/GPUWDDMsoma2,45255GiB/DXGI7,19014GiB.
Releituras sob pedido<=1662,380ms fora das janelas formais. Recibo/sourcearchive
próprios e backup3.6validado; não atribuir esses tempos à geração3.7.

## Comparação e séries temporais — produto3.7

Duas sondas do mesmo instante confirmado mostram distância, Δg, ΔΦ e
os autovalores do tensor na primeira. T·Δx é uma aproximação local de primeira
ordem, disponível só com as mesmas fontes incluídas. Autovetores degenerados
não definem eixos materiais únicos; não há deformação material nesta fatia.

Gravação durante a evolução, em snapshots confirmados: cadência real solicitada
0,25–5s, janela de128registros, descarte explícito do mais antigo. Cada leitura
guarda instante físico, revisão, definições, fontes/faseSI, g/Φ/T e balançosE/P/L.
Cadência não cria passos do integrador. UI pede curvas compactas até1Hz só
com painel aberto; não replica o histórico completo no poll de estado.
Traços interrompem lacunas/configurações distintas/leituras indisponíveis.
Escala log usa só positivos. Eixos com variação pequena mostram diferença
contra uma referência numérica explicitada na legenda.

Clicar consulta a amostra original e cria marcas antigas na cena; não restaura
a evolução. A marca informa leitura congelada. Checkpoint mantém janela e
definições; export completo preserva fontesSI. Limpar janela preserva física.
Ciência instalada passou8corrupções; Sessionfixture/Atlas/single passou24guards/
21corrupções, igualdadeREBOUND comcontrole e binário doMESMOintegrador exato
antes/depois das leituras. IAS15 sem avisos no domínio1corpo; política numérica
em GRAVIDADE-NUMERICO.md. Worker e regressões existentes passaram.
CEF P32/Atlas passou comparação/gravação/clique/export/save/load/clear,
sem erros, marca nativa exata e pointer latest.json preservado.
Stress isolado128massas/16sondas/128registros: rate0,99927u/s,
20pausas<=36,326ms, leitura<=49,689ms, curvas511462bytes/export5112639bytes.
Perfilhistory1 foi aprovado na fonte3.7 congelada:3x60s/30s/1080p,
p95<=19,901ms/p99<=22,061ms/zero>100ms/20pausas<=49,808ms.
RAMsoma1,05063GiB/GPUWDDMsoma2,99723GiB/DXGI7,19014GiB.
C2-11 permanece parcial: ramos3.8 em validação; J2/marés/ressonâncias/
perfis256/10mil pendentes.

## Ramos3.8 — núcleo e perfil validados

Até32arquivos independentes em user/sessions/branches, sem substituir o ponteiro
da sessão principal. Cada arquivo guarda o integrador, fase, origem, definições
e janela completa, com pai/hash selados. Restaurar gera novo edit_token e pausa.
Comparação de arquivos exige mesma origem/referencial/geração salva; gráficos
conservam instantes originais, lacunas e definições diferentes explícitas.
Estados finais em tempos diferentes não são subtraídos. Export comparação é
compacto; integrador e fontes completas permanecem nos arquivos originais.

Núcleo4modelos/24rejeições e worker passaram; CEF P32/Atlas passou jornadas
básicas, fase/referências/history/pointer exatos. Erro de posição gráfica
0P32/3,052e-5mAtlas. Capturas revisadas. Os arquivos do teste são retidos em
output/c211-branches-native-fixtures e backend é reiniciado para recache.
Stress128massas/16sondas/128registros e catálogo32 passou: salvar5,44–5,52s,
comparar10,871s/restaurar9,764s, resumo11374B, estado~3,116ms. Limite33
rejeitado sem modificar arquivos/fase. Não equivale a benchmark de quadros.
Prazo da ponte save/load ampliado para30s; prova máxima nativa passou com
128massas/16sondas/128registros, salvar6187,448ms, zeroerrosCEF, fase/histórico/
referências/pointer preservados. Selects recalculam habilitação imediatamente.
Regressão de histórico3.8 também passou P32/Atlas, incluindo clique original,
marcas nativas, salvar/restaurar e igualdade física.

Perfilc211history2 fonte3.8 aprovado/auditado comarquivo de fontes próprio:
3x60s/30s/1080p,p95<=20,507ms/p99<=22,290ms/zero>100ms,
rate>=0,99566,20pausas<=108,688ms. RAMsoma1,04469GiB/GPUWDDMsoma2,99088GiB/
DXGIbudget7,19014GiB. Recibo evidence/c211-branches-validated.json e backup
output/c211-branches-validated. C2-06 e perfis3.6/3.7 preservados separadamente.
Apóscoleta,UI corrige tracejado reiniciado acada intervalo e espaça marcadores
emjanelas densas; revalidaçãoCEF própria emcurso, sem atribuir aessa mudança
os tempos dafonte congelada. C2-11 continua parcial.

## J2 exterior — produto3.9 em validação de desempenho

Em15/10, a correção de quadrupolo exterior foi instalada, após provas isoladas
e regressões. Até4fontes com J2, Req, eixo inercial e procedência explícitos.
Nenhum planeta recebe parâmetros J2 por padrão; o raio geométrico e o spin
cinemático permanecem separados dos parâmetros gravitacionais. O eixo do
quadrupolo é prescrito, sem evolução/reação do torque no spin. O modelo não
representa interior, material ou deformação. Exige r≥Req para os demais centros
e sondas; tentativa de entrar no interior pausa sem publicar fase inválida.

Um kernelSI fornece Φ, g e T e a força quadrupolar. Pares incluem reação linear
e energia de interação. Sondas são pontos passivos sem quadrupolo; uma fonte
J2 também recebe a reação de seu próprio quadrupolo contra as outras massas.
Energia mecânica e P são auditados. L orbital vetorial pode variar fisicamente;
não é rotulado como erro de conservação. A componente num eixo comum é
auditada quando os eixos configurados são paralelos. Não alegar conservação
de L total órbita+spin nem aquecimento nesta aproximação.

Isolado60órbitas: erroE1,735e-15/P4,556e-16/Laxial7,065e-16.
Precessão nodal/pericentro difere0,0336%/0,0205% da primeiraordem secular.
IAS15 contraDOP853 difere~1,55e-13; refinar o passo do oráculo difere1,295e-13,
no piso float64/oráculo. Campo passa gradiente/tensor/rotação/traço.
Leituras mantêm binário domesmo integrador exato. Retomada religa callback e
mantém toda fase e camposIAS15 exatos; entre instâncias sówalltime medido e
ponteiros _sim são excluídos da comparação de serialização.

Sessioninstalada passou4cenários/39guards/24corrupções, histórico guardaJ2SI/
procedência. Configurar J2 é intervenção física comΔE, replay e invalidação
dos derivadosIAS15; salvar/ler não os reinicia. Worker passou6leituras/.25s,
20pausas<=4,728ms, fronteiraexterior e ramos, stderrvazio. Regressões pontuais
anteriores passaram em cópias com importação do candidato e arquivos próprios.
CEF P32/Atlas passou ativar/desativar, formulário antigo, mapas337pontos,
histórico, salvar/carregar e ramos J2vsmonopolo; zeroerros, fase/referências/
pointer/épocaAtlas exatos. Capturas cosmos2-j2-{fixture,atlas}.png revisadas.
Provas j2-{session-installed,worker-installed,ui}-check.json. Backup pré-J2 em
output/c211-pre-j2/app; promoção evidence/c211-j2-promotion.json.
Perfilhistory3 fonte3.9 passou auditoria numérica, mas foi recusado por possível
interferência de um ensaio científico no fim da terceira janela. Fontes e falha
preservadas. Repetição limpa history4 concluída/auditada:3×60s/30s/1080p,
p95<=19,839ms/p99<=22,429ms/zero>100ms/rate>=0,99888/20pausas<=77,760ms.
RAMsoma1,05650GiB/GPUWDDM2,98893GiB/DXGIbudget7,19014GiB. Fonte atual coincide
com os hashes desse arquivo congelado. Este perfil tem J2 desligado;
performance comJ2 ativo requer perfil próprio. Marés/ressonâncias/256/10mil pendentes.

## Correção de desempenho J2 — 3.9.1

O perfil ativo c211j2c da3.9.0 foi recusado:128massas/1fonte J2 e histórico
atingiram só0,05903u/s com pedido1u/s. Imagem fluida não prova evolução rápida;
os frames ficaram p95=16,894ms/p99=18,589ms e zero>100ms nessa janela recusada.
Rawframes e fonte anterior permanecem no recibo/arquivo failed-source.
Tentativas a/b anteriores têm falhas de roteiro separadas e não são aceites.

Profiling isolou avaliações escalares Python por corpo e estágioIAS15.3.9.1
agora avalia pares num lote NumPy, usando o mesmo kernel para g/Φ/T e força.
O callback acessa uma view limitada à chamada, com tamanho/offsets obtidos do
ABI da versão REBOUND fixada; não guarda ponteiros após clone/carga. Quantidade
e massas são verificadas. Reação linear continua aplicada. A versão/NumPy são
registrados na geração científica, pois muda a ordem de arredondamento float64.

2560pontos contra derivação escalar preservada: diferenças de g≤7,592e-15 e
T≤5,395e-14 na escala do modelo; gradientes numéricos≤4,325e-10. Reação com
128massas/4fontes normalizada8,255e-17. Session/worker/órbita independente
passaram novamente, incluindo39guards/24corrupções e fronteira exterior segura.
Quatro checkpoints reais3.9.0 migraram com histórico exato e arquivos intactos.
CEF P32/Atlas passou e capturas foram revistas. promotion/backup pré-otimização
em evidence/c211-j2-vector-promotion.json e output/c211-pre-vector.
Perfil formal ativo3.9.1 ainda em coleta; não atribuir o aceitehistory4 histórico
à fonte nova. C2-11 continua parcial; marés materiais ainda fora do produto.

Perfis J2ativos3.9.1 concluídos e auditados separadamente:1fonte
p95≤18,892/p99≤21,071ms/rate≥0,99461/20pausas≤50,137ms;4fontes
p95≤19,129/p99≤21,383ms/rate≥0,96444/20pausas≤105,776ms. Ambos semframes>100ms,
128massas/16sondas/.25s/128registros/2curvas. RAMsoma≤1,04759GiB,
WDDMsoma≤2,98893GiB/DXGIbudget7,19014GiB. Fontes e backup validados em
output/c211-j2-validated e evidence/c211-j2-validated.json. Motor encerrado.
Marés avançaram para kernel isolado com médias Kepler/energia/torque/calor
verificados; continuam fora do produto. Próximo é integração conjunta e
persistência, com contrato numérico material próprio explicitado.

## Maré material3.10 — ciência e jornada nativa validadas

MARES-EQUILIBRIO.md define o contrato instalado: duas massas ativas, uma esfera
com k2 potencial/τ/I/R/spinSI explícitos, órbita relativa+spin+calor em UMA ODE
BS5.2.2(epsabs/rel1e-13), COManalítico e partículas somente como espelho confirmado.
Sem J2 prescrito/superfície/h2/térmica. Sondas usam oQ congelado do mesmo kernel,
sem induzir outra resposta. Eauditada inclui calor; L inclui spin material.

Provas instaladas tides-{bs,session,worker}-installed-check, tides-ui-check e
migração de10arquivos. E+calor/Ltotal20órbitas≤1,963e-13/7,760e-14; confronto com
DOP853deRHSindependente3,008e-11. Save/load e ramos conservam fase/spin/calor/
solver/histórico, com futuro exato; domínio inválido não é publicado.
CEF passou par sintético/formulárioSI/mapas337pontos/gravação/ramos e captura
foi revista após enquadramento próprio. Arquivo do dono permanece byte-exato.
Perfil formal material2 de3.10 está em coleta:16sondas/.25s/128registros,
2curvas+569amostras congeladas,3×60s/30s/1080p; aguardar recibo de auditoria.
Ressonâncias em preparação isolada, sem operador instalado.256/10mil pendentes.

Perfil próprio3.10 c211tides1 concluído/auditado:2massas materiais/16sondas/
.25s/128registros/gráfico2sondas+569amostrascongeladas,3×60s/30s/1080p.
p95≤13,963ms/p99≤14,424ms/zero>100ms/rate≥0,98492/20pausas≤47,664ms.
RAMsoma1,05463GiB/WDDMsoma2,96940GiB/DXGIbudget7,19014GiB. Fontes exatas e
backup emoutput/c211-tides-validated e evidence/c211-tides-validated.json.
Isso não é perfil128/256/10mil. C2-11 continua parcial. Próximo: ressonâncias.


## Ressonâncias3.11 e expansão256 em16/10

RESSONANCIAS-ORBITAIS.md registra o instrumento passivo, as convenções e os
limites de inferência. Ciência/Session/worker/CEF/migração reais passaram.
Perfilc211orbital1 aprovado:128massas+16sondas+janelaorbital,.25s/128registros,
3×60s/30s/1080p,p95≤18.910/p99≤21.111ms,zero>100ms,rate≥.9980478,
20pausas≤52.733ms. Backupoutput/c211-resonances-validated/app; recibo próprio.
A3.12 amplia o limite a256massas ativas; oráculoDOP853 curto concorda7.106e-15,
históricos256fontes/save/load/3futuros exatos,257ªmassa recusadaatomicamente.
Worker eCEF passaram; abertura/reabertura256 exige32.4s de inicializaçãoGL.
Comandos de montagem agora esperam60s; controles curtos mantêm prazo15s.
Perfilformal256c211p256q3 APROVADO17/10:3×60s/30s/1080p,p95≤22.428ms,
p99≤24.969ms,zero>100ms,rate≥.99964045,20pausas≤62.999ms. Runtimequery
eponteemlote;reciboc211-p256-validated.json,backupoutput/c211-p256-validated/app. Dezmil
partículas semmassa passaram ciência e pacote binário isolados; ainda sem
integraçãoSession/cena dinâmica/seleção/perfilpróprio. C2-11 permaneceparcial.

## Integração candidata de10mil —17/10

output/c211-cloud-product/app agora liga Session/worker/Laboratory/CEF à nuvem
nativa agregada. Jornada completa passou: criação10000, evolução, seleção9999
SIexata, foco e marcador móvel, leitura antiga explícita, save/reset/load,
limpeza ao Atlas e restauração ao reentrar; zeroerrosJS e sessão do dono intacta.
Reciboevidence/cloud-product-candidate-check.json. A ponte valida pacote em
Python e mantém uma publicação em voo até confirmação nativa do mesmo
instante, sequência, identidades e bufferGPU. Ciênciafloat64; desenho quantizado
float32. Uma fonte e partículas sem massa, sem gravidade entre testes/reação.
Leitura de energia específica é congelada; marcador acompanha posições novas.
Armazenamento candidato separado:output/c211-cloud-candidate/sessions.
Perfilformal c211cloud1 em andamento; sem promoção ou aceite completo deC2-11.

Pedido17/10: atração acima/abaixo do corpo foi conferida no instalado e na
candidata.1030direções emdoiscentros,2060leituras porvariante; atração central,
módulo igual emraiosiguais e queda1/r². Session7corpos confirma movimento
paraocentro nos6semieixos, incluindo±z; erro4.167e-12 contra somaindependente.
Recibosgravity-spherical-installed-check.json egravity-spherical-candidate-check.json.
O anel sintético é plano por suascondiçõesiniciais; gravidade não estárestrita
aoplano. A conclusãoesférica valeparaomonopolo exterior; J2/maré acrescentam
componentes nãoradiais. Não comprova estrutura material interna.

## Instalação3.13 —18/10

Os registros de candidatura acima são históricos.3.13 está instalada: ciência,
worker, transporte, migrações, jornada completa e perfis de10000 e256 no mesmo
motor foram aprovados. c211cloud4: p95max18.327741/p99max19.515841ms;
c211p256c2: p95max21.460199/p99max23.259919ms. Ambos3×60s/30s/1080p,
zero>100ms. Aprovação ebackup em evidence/c211-cloud-validated.json.
Bootpadrão eUIinstalada10mil/quatroforças passaram, sem salvar sobre o dono.
Seis limpezasdecampo+duas trocas256↔10000↔Atlas passaram; crash anterior
de limpeza estápreservado semcausa atribuída. Não declarar C2-11 inteiro ou
malha implementados: CAMADAS-QUATRO-FORCAS.md fixa pendências18/10.
