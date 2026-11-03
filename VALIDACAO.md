# Validação e critérios de aceite — Cosmos2

Protocolo revisado em 12/10/2026 para o plano 3.0. Já existem provas do
protótipo em evidence/, descritas em LEIA-PRIMEIRO.md; elas não aprovam os
marcos completos. Os critérios abaixo são metas, não resultados. Congelar
entradas e tolerâncias antes de executar; justificar alterações posteriores.

## 1. Portas de decisão

| Porta | Marco | Evidência necessária |
| --- | --- | --- |
| G0 — base viável | C2-00 | Aplicativo Windows real na RX 7600, perfil offline, viagem Terra–Lua–Via Láctea, interface própria e worker atualizando 32 corpos |
| G1 — qualidade visual | C2-03 | Três cenas iniciais reproduzíveis, navegação utilizável e revisão visual sem defeitos impeditivos |
| G2 — exploração | C2-05 | Percursos J1/J2, origem dos dados e superfície procedural determinística |
| G3 — laboratório | C2-07 | J3/J4 e testes de integração, colisão, conservação e interrupção |
| G4 — entrega intermediária | C2-10 | J1–J5, instalação limpa, offline, desempenho, recuperação e documentação |
| G5 — campos e instrumentos | C2-11–13 | J6–J8, medições independentes, gravação de sondas e resposta física a alterações |
| G6 — relatividade | C2-14–15 | J9/J10, referências quantitativas, observador/domínio definidos e imagem correspondente aos raios |
| G7 — riqueza de conteúdo | C2-16 | Metas do acervo, 12 destaques, 32 experimentos e observatório J11 |
| GN — nuclear e acoplamento | C2-18–20 | J12–J15, taxas/decadência, operadores independentes e balanços de composição/energia |
| G8 — v1 ampliada | C2-17 | G0–G7 e GN, J1–J15, persistência dos modelos, offline e desempenho do pacote completo |

G0 exige mediana ≥30 FPS a 1080p no perfil pequeno, sem renderização por
software, sem travamento ao pausar o worker e sem artefato impeditivo.
A meta de 60 FPS do produto é avaliada nos marcos posteriores; G0 não a comprova.
Falha central em G0 encerra a tentativa daquela base conforme C2-00 e abre
o diagnóstico/alternativa, não a multiplicação de funcionalidades.

## 2. Física: testes proporcionais e independentes

| Caso | Comparação e critério inicial |
| --- | --- |
| Unidades e referenciais | Transformar ida/volta vetores conhecidos; resíduo ≤max(1 mm, 10⁻¹²×norma) para posição nos domínios locais testados |
| Dois corpos | Órbitas analíticas com excentricidades 0 e 0,6; 100 períodos; erro relativo de energia ≤10⁻⁸ e posição ≤10⁻⁵ do semieixo maior no modo de precisão |
| Encontro próximo | Fixture com solução de referência refinada; estudo de convergência numa janela anterior à divergência caótica relevante, considerando o piso de arredondamento; sem singularidade silenciosa |
| Momentos | Em sistema fechado sem colisão, resíduos normalizados de momento linear e angular ≤10⁻¹⁰ nos casos de referência |
| Colisão frontal | Massa e momento linear conservados a erro relativo ≤10⁻¹²; contato detectado mesmo quando atravessaria o raio em um passo |
| Colisão oblíqua | Momento angular contabilizado incluindo spin; balanço energético conforme reservatório do modelo |
| Calor didático | Soluções estacionárias conhecidas, unidades coerentes e limites válidos de albedo/emissividade; erro relativo ≤10⁻⁶ na avaliação escalar |
| Edição no tempo | Pausar, editar e reiniciar produz o mesmo estado que iniciar diretamente do checkpoint editado, dentro da tolerância do solver |
| Determinismo procedural | Mesmas seeds/versão produzem parâmetros idênticos nas ordens de visita testadas; imagens podem variar por driver |

Para momentos, usar escalas características não nulas, por exemplo M×V e
M×R×V; não dividir por um momento total que pode ser zero. Para energia de
casos não ligados, usar escala K+|U|, sem divisão por energia quase nula.
Após colisão, a energia mecânica isolada não precisa se conservar: validar o
balanço que inclui o destino da dissipação no modelo adotado.

O teste analítico de dois corpos mede o integrador. Uma comparação com
efemérides mede também o modelo físico. Não atribuir toda diferença ao solver
quando marés, relatividade ou perturbadores foram omitidos.

No teste de referenciais, ida/volta é apenas uma checagem adicional: um par
de transformações igualmente errado poderia cancelá-lo. Conferir também
vetores conhecidos e orientações de referência, incluindo uma rotação de
90 graus, troca de origem e conversão km→m, contra valores independentes.
Mudanças deliberadas de massa/velocidade são intervenções externas e reiniciam
a referência de conservação conforme o registro de eventos.

## 3. Efemérides e dados reais

Fixar pequenos vetores de referência com fonte, data de obtenção, kernel,
centro, eixos, escala temporal e correção de aberração. No teste geométrico,
usar a mesma convenção sem correção aparente de luz. Comparar posições/velocidades
do adaptador com valores independentes sob as mesmas definições.

Primeiro validar transporte e conversões numericamente; depois comparar a
fonte adotada com Horizons. Uma diferença entre versões de efemérides não
deve ser “corrigida” alterando um corpo visualmente. Registrar tolerância por
corpo/intervalo antes do teste externo, em função da precisão e modelo das
fontes. A v1 não promete precisão universal de navegação espacial.
[Manual Horizons](https://ssd.jpl.nasa.gov/horizons/manual.html).

Para Gaia/exoplanetas: amostra de IDs e valores conferida com o recorte original;
campos ausentes continuam ausentes; procedência por propriedade; teste de IDs
acima de 2⁵³. Para efemérides, rejeitar consulta fora da cobertura ou marcar
claramente o modelo alternativo selecionado.

## 4. Medição gráfica no hardware real

Usar Windows nativo, RX 7600, 1920×1080 e preset fixo. Registrar build, driver,
resolução interna/saída, escalonamento, conteúdo, cache quente/frio e VSync.
Benchmarks antigos em WSL/Xvfb não servem como evidência desta entrega.

Guardar identificação de vendor/renderer/versão OpenGL e confirmar que o
processo usa a Radeon física. Registrar monitor, limite de FPS e VSync;
uma limitação de apresentação não deve ser confundida com custo do renderer.
Não atualizar driver como parte implícita da medição: registrar a versão
antes e depois se uma mudança se tornar necessária na implementação.

Por cena: aquecer por 30 s e medir três percursos de 60 s, guardando tempos
de frame. Não multiplicar repetições sem causa. Relatar mediana, p95, p99,
quadros acima de 100 ms, RAM total dos processos e uso/orçamento de VRAM.

Metas de cenas usuais: mediana ≤16,7 ms, p95 ≤25 ms, p99 ≤50 ms. Superfície
pesada: mediana ≤33,3 ms, p95 ≤40 ms, p99 ≤80 ms. O roteiro quente não deve
ter pausas recorrentes acima de 100 ms. Abertura fria tem relatório separado,
com meta de primeiro quadro útil ≤15 s no disco local e progresso visível.

Medir Atlas e Atlas+worker para separar gargalos. Pausa/cancelamento do worker
deve confirmar em ≤250 ms no perfil de 128 corpos; controle da câmera não
espera essa confirmação. Busca local: p95 ≤100 ms após índice pronto.

Metas de memória: soma residente do produto ≤8 GiB no perfil padrão e VRAM
alvo ≤5,5 GiB, sempre abaixo do orçamento realmente disponível. Contagem
exata e método ficam no relatório; memória compartilhada pode ser contada
duas vezes por ferramentas e precisa ser identificada.

### Cenários congelados da integração física

O número de corpos sozinho não define a dificuldade. Usar os seguintes
descritores propostos, convertidos em arquivos de entrada antes dos testes:

| Cenário | Estado e finalidade |
| --- | --- |
| P32 | 1 corpo central e 31 orbitantes; prova C2-00 e latência de comandos |
| P128 | 1 corpo central e 127 orbitantes; carga padrão C2-06 e orçamento de pausa |
| P-ENCONTRO | Fixture separada de encontro próximo; precisão, redução da taxa efetiva e resposta da interface |

P32/P128 usam unidades canônicas G=1, massa central=1, massa de cada orbitante
=10⁻⁸. Para N orbitantes, i de 0 até N−1: raio
`r_i = 0,5 × 60^(i/(N−1))`, ângulo `2πi/N`, plano z=0 e velocidade tangencial
inicial `sqrt((1+10⁻⁸)/r_i)`. Transformar o conjunto para seu baricentro.
São condições iniciais sintéticas de teste; não são efemérides nem uma
afirmação de estabilidade física de longo prazo. Estes perfis medem gravitação
e transporte de estado, sem colisões. Os três modelos controlados C2-06 também
usam massas pontuais sem contato e pausam no limite singular de 1 mm; o modelo
de contato, fusão e energia interna permanece em C2-07. A ausência de contato
não foi validada como física de corpos extensos.

Usar inicialmente IAS15 com tolerância configurada de 10⁻⁹ e registrar todos
os parâmetros efetivos. Uma unidade de tempo canônica é definida pela escolha
G=M=1; o período circular em r=1 é 2π unidades. Pedir 1 unidade de tempo
simulado por segundo de execução e medir a taxa realmente atingida. Não
converter esse resultado para “dias por segundo” sem declarar a escala física.

Emitir estados de visualização com alvo de 30 atualizações por segundo, sem
forçar passos físicos de 1/30 da unidade simulada. O critério de C2-00 é
interface/renderer responsivos e comando confirmado em ≤250 ms em P32.
C2-06 mede a mesma latência em P128. Throughput físico abaixo do pedido exige
mostrar a taxa efetiva; nunca relaxar a tolerância para encobrir o custo.

Salvar os vetores gerados e seus hashes para que futuras medições usem os
mesmos números. Benchmark não usa uma cena diferente a cada execução. Em
P-ENCONTRO, conservar a precisão tem precedência sobre atingir a taxa pedida;
para essa classe não existe promessa de aceleração constante.

## 5. Precisão e estabilidade da imagem

Congelar câmera e tempo em cenas próximas e distantes. Ao mudar âncora e
retornar, testar desvio de pontos projetados ≤0,5 pixel nas fixtures definidas.
Usar coordenadas projetadas além de olhar capturas; cintilação de shader é
outro problema e precisa de revisão de vídeo.

Observar: costuras de terreno, troca de nível, transparência dos anéis,
terminador, sombras, exposição, rótulos e seleção. A diferença de imagens
entre drivers tem tolerância perceptual, nunca igualdade binária obrigatória.
Uma captura bonita não comprova fluidez; um gráfico de FPS não comprova imagem
boa. Registrar imagem e percurso curto nas seis cenas de referência.

## 6. Persistência, instalação e falhas

Uma rodada focada deve cobrir:

- Abrir pacote numa pasta com espaços/acentos, sem ambiente de desenvolvimento.
- Executar J1–J5 com rede indisponível e conteúdo básico local.
- Encerrar worker e recuperar checkpoint sem travar o Atlas.
- Interromper gravação/obtenção e manter última sessão/pacote íntegro.
- Recusar corrupção ou esquema desconhecido sem sobrescrever os originais.
- Mover sessão para outra pasta e resolver conteúdo por IDs/hashes.
- Cancelar download e remover cache sem apagar experimentos.
- Redimensionar, alternar tela cheia, minimizar e voltar sem perder cena/foco.

Falhas são introduzidas apenas em cópias e pastas de teste. O pacote final
tem inventário de código, dados e termos; seu guia declara funcionalidades
adiadas e hardware em que foi medido.

## 7. Aceite de experiência

Executar J1–J5 na entrega intermediária e J1–J15 na v1 ampliada, com controles
de produto. Registrar passos que
exigem conhecimento interno ou console como defeitos de uso. Conferir foco,
contraste, zoom da interface, seleção sem depender só de cor e redução de
movimento. C2-03, C2-10 e C2-17 têm revisão visual do agente; a opinião do dono é
registrada quando fornecida, sem inventar um aceite.

## 8. Registro mínimo por marco

Um relatório curto identifica build, cenário, valores medidos, resultado,
limitações e próximos ajustes. Anexar somente fixtures, logs e capturas que
sustentem a decisão. Reusar resultados aceitos enquanto código, ambiente e
risco relevante permanecerem iguais. Não escrever testes que apenas repetem
a implementação ou transformar cada documento em nova bateria de testes.

## 9. Critérios científicos da ampliação

As tolerâncias são propostas iniciais, a congelar com fixtures antes do módulo.
Erro de implementação não é incerteza física do modelo. Convergência exige
refinamento de passo/amostragem, não só comparação de duas funções que usam
o mesmo código. Comparar diagnósticos no mesmo instante/referencial.

| Fenômeno | Referência e condição de aceite proposta |
| --- | --- |
| Campo gravitacional | Massa pontual fora da exclusão: g=GM/r² e potencial −GM/r; erro relativo ≤10⁻¹⁰; superposição e direção em posições não simétricas |
| Gradiente de maré | Autovalores radial 2GM/r³ e transversais −GM/r³ para massa pontual; erro normalizado ≤10⁻⁶ e comparação por diferença finita refinada |
| Lagrange | Caso circular restrito fixado; resíduos no referencial girante ≤10⁻⁸ da aceleração característica; L4/L5 conferidos por geometria independente |
| J2 e marés | Precessão secular contra solução no regime de pequena perturbação, alvo ≤1%; balanço orbital+spin+calor e convergência; fixar parâmetros e tolerância de maré antes da prova |
| Campo elétrico | Coulomb e superposição fora da exclusão; erro relativo ≤10⁻¹⁰; próximo de zero usar escala absoluta baseada nas fontes |
| E uniforme | Posição e velocidade contra aceleração qE/m, erro normalizado ≤10⁻⁶; considerar o escalonamento temporal das velocidades do integrador |
| B uniforme | Hélice, raio de Larmor e frequência ciclotrônica: 10 períodos, passo inicial T/2000, erro de trajetória normalizado ≤10⁻³ e deriva relativa de energia ≤10⁻¹⁰; confirmar convergência |
| E×B | Deriva média contra solução em campos cruzados uniformes, regime não relativístico; erro relativo ≤10⁻³ e janela com períodos completos |
| Coulomb mútuo | Dois corpos carregados no regime eletrostático, órbita/espalhamento de referência e refinamento; energia ≤10⁻⁶ da escala K+abs(U), momento normalizado ≤10⁻¹⁰ |
| IGRF | Pelo menos 20 posições/épocas/altitudes, incluindo polos e fronteiras de cobertura, contra implementação de referência com mesmos coeficientes; diferença de componentes ≤1 nT; isso não declara acurácia do campo terrestre real |
| Precessão relativística | Comparar avanço por órbita com 6πGM/[a(1−e²)c²] em fixture de campo fraco, erro ≤1%; subtrair erro do controle newtoniano e documentar domínio |
| Relógios | Observadores estáticos em Schwarzschild fora do horizonte: razão de ritmos pela expressão analítica, erro relativo ≤10⁻⁸; teste separado de dilatação cinemática |
| Lente em campo fraco | Deflexão 4GM/(bc²), com GM/(bc²)≤10⁻⁵, erro relativo ≤10⁻³; lente pontual alinhada contra raio de Einstein analítico |
| Schwarzschild | M→0 recupera raios retos; horizonte, esfera de fótons e ISCO nas coordenadas declaradas; parâmetro crítico de captura 3√3 GM/c² com erro ≤10⁻³, refinando perto da separatriz |
| Kerr | Spin→0 recupera Schwarzschild; referência independente para raios e invariantes de movimento; congelar normalização/tolerância antes de integrar à imagem, incluindo casos fora do plano equatorial |
| Instrumentos estelares | Integral do espectro de corpo negro contra Stefan–Boltzmann (≤10⁻⁴ no intervalo/refinamento declarado); trânsito central sem escurecimento de bordo contra (Rp/Rstar)² (≤10⁻³ relativo), em Rp<Rstar |

Para conservação com campo prescrito ou fonte externa, contabilizar trabalho
externo e esclarecer quais reservatórios estão fora do sistema. Campo
magnético uniforme sozinho não deve produzir aquecimento espúrio. Com marés
ou colisões, energia mecânica pode decair; o balanço total do modelo é o teste.

Geodésicas preservam sua normalização nula/temporal e os invariantes aplicáveis
com erro e convergência registrados. Horizonte/sombra não são o mesmo raio
aparente. A imagem precisa concordar com um conjunto de raios CPU de referência
e com a câmera/observador; diminuir erro de imagem não substitui testar o solver.

Em18/10, o recorte experimentalC2-12 avançou para editorEM0.2 e candidata
isolada, sem alterar o produto3.13. em-editor-check.json registra17intervenções
com deltas mecânicos independentes,26recusas e futuro777passos exato nos dois
regimes; migração0.1 confere o futuro com processo do código congelado.
em-native-scene-check.json registra cinco presets, posições nativas exatas
conferidas porWS independente, malhas E/B reconstruídasSI e seis ciclos limpos.
em-trace-check.json confere direção, exclusões e convergência das linhas;
em-lines-native-ui-check.json mede erro máximo1.434e-6 no invariante analítico
do dipolo,16trechos/498vértices nativos, exportação comhash e instantes/fontes
próprios. em-native-resilience-check.json e em-restart-check.json verificam
pose/foco e retomada exata do modelo/histórico/seleção após reinício normal.
O perfil128 da nova candidata EM0.4 passou emnative-em128-c212em04a-review.json:
3×60s/30s,1920×1080,128cargas/dt.001/rate1,97amostras congeladas,
taxa mínima0.999384s/s,p95máximo23.254ms,p99máximo24.658ms,zero>100ms.
Cada rota recomeça do mesmo checkpoint.20pausas≤65.254ms;66amostrasWDDM por rota
cobrem toda captura. RAMsomada1.177GiB/WDDMsomado2.968GiB<DXGI7.190GiB;
somas podem repetir compartilhamentos. A revisão confere fontes/DLL/rawframes,
conservação e recursos. Órbita longa e migração têm provas separadas emem-v04-*.
O perfil0.3 permaneceu reprovado na taxa0.788–0.813s/s, com dados preservados.
em-potential-check.json verifica equipotenciais lineares e Coulomb com refinamento,
exclusões conservadoras, degenerações e orçamento. em-potential-worker-check.json
verifica289amostras em lotes128+128+33 sob identidade/tempo/geração únicos,
com recusas de respostas divergentes, sem mudar ciência/editor.
Em19/10, em-potential-native-ui-check.json passou a integração própria de
potencial:1089amostras,uniforme544arestas/553vértices eCoulomb868/877;
erro SM/float32/SI≤8.808e-8m,resíduoVuniforme2.776e-17V,
amostrasCoulomb conferidas por soma independente (erro0 nas amostras válidas).
Quatro combinações atuaçãoE/visibilidade, sonda de fontes congeladas, exporte
com tempos por camada,viewaux2/legacy1/recusas ezeroJS passaram.
em-potential-restart-check.json verifica retomada normal; em-potential-lost-ack-check.json
verifica publicação real seguida de ACK perdido e limpeza confirmada sem órfãos.
em-potential-paths-check.json confere caminhos abertos/ciclos/junções/pontas
quaseiguais; só pontas exatamente iguais de grau2 são unidas. Perfil potencialA
reprovado emnative-em128-c212pot128a-review.json porp95rota3=25.33406ms>25;
rates~1 passaram. PerfilB após otimização também reprovou(p95rota3=26.72623ms); nenhuma promoção.
em-cloud-v02-core-check.json:64pontos vs escalar/agrupamento longdouble,
erro normalizado5.068e-16;1024passos Boris escalar erro2.776e-17;
10períodosB com refinamento1000/2000/4000 e energia6.723e-15;
E/trabalho~1e-14 eE×B4.194e-6, exclusões/imutabilidade/recusas.
10mil/500passos dt.002:1.1728s/s isolados (v1congelada0.6847s/s),
sem aceite de desempenho nativo10milEM. Em19/10, checkpointEMschema1 eworker
próprio passaram futuros777/777/64 para1/128/10000 emais33passos emsegundo processo,
fase/trabalho/tempo exatos,23pausas≤8.337ms comtransporte. C2CLD002EMv2/SI1/1
passou37recusas ebufferF64exato;decodegravidadelegadorecusaEM. Runtime experimental
.runtime-em-cloud preservaexecutáveisaprovados. Prova inicialHTTP/child/GPU passou
1/128/10000, seleção e18recusasnativas; fonteparentfinal/CEF/restart/perfil pendentes.
Em20/10, native-emcloud-c212em10kc-review.json aprovou o recorte nativo
10milq=m=1/Buniforme1T/Ezero/dt.002/rate1/97vetoresB congelados:3×60s,
30saquecimento/rota,1080p; cadarota parte da mesma fase. P95máximo18.43488ms,
p99máximo20.65366ms,zero>100ms,taxamínima.9446987s/s.20pausas≤121.1317ms;
66amostrasWDDM/rota cobrem toda a captura. RAMsomada1.078GiB/WDDMsomado2.964GiB
<DXGI7.190GiB. Auditorstdlib verifica cada fonte/DLL/rawframe/subrota, os buffers
F64 e órbitaB analítica de todas10milpartículas: erro≤3.400e-5raiosLarmor,
deriva de energia somada0 nas três saídas. Candidata congelada sem promoção.
PerfilB ficou incompleto por timeout final do coletorGPU na rota3; raw e fonte
preservados emnative-emcloud-c212em10kb-interrupted-source.tar.gz. PerfilC usa
diário poramostra e prazo de finalização de90s, sem alterar limites científicos.
O primeiro auditorC teveKeyError porseparadorWindows no recibo; tentativa efonte
preservadas, normalização corrigida antes da auditoria aprovada.
DiagnósticoCPU separado de20passos/10mil com128fontes estáticas de carga+dipolo
mediu.0114626s/s; não aprova esse regime. Núcleo compilado próprio em construção.
HelperE próprio em20/10:camposSIMD vsescalar erro≤2.231e-16,200bboxes contra
referência(120recusas),16exclusões/subnormais/0.01c;futuros iguais em1/4/6/8threads.
16futuros NumPy/C++ emprocessos separados cobrem777/777/64/8passos,1/16/128/10000
partículas,0/2/128fontes e4combos;erro≤5.552e-17,tempos exatos. Worker7processos
passoufuturos exatos e23pausas≤7.817ms;checkpointv2real recusado semmigração.
CEF/reinício/64futuros/13recusasaux/ACKperdido passaram na candidata própria.
Perfil native-emcloud-c212src128a-review.json PASSOU no recorte fraco explícito:
10milq=m1;128fontes estáticasq±1e-12C emcasca8m,momentos(1e4,-2e4,3e4)A.m²,
Buniforme1T;dt.002/rate1;97vetoresE+97B;3×60s/30s1080p e3vistas porrota.
Taxamínima1.000023s/s,p95máximo18.79838/p99máximo19.76913ms,zero>100ms;
20pausas≤113.4061ms,RAMsoma1.1854GiB/WDDMsoma2.9648GiB<DXGI7.1901GiB.
F64/checkpoints/fontes/DLL/raw/subrotas foram conferidos. ReferênciaDOP853 de
fórmula vetorial independente para3partículas/rota até~104s:erro≤3.4923e-5,
refinamentodaref≤1.311e-14;energiaestática total de10mil deriva≤1.087e-11.
Núcleo/candidata/perfil/reprovações congelados sem promoção. O caso intenso
q±1e-10C falhou trajetórias longas:erro.9051/.2527/.06611 nos passosT/20000,
T/40000,T/80000 em62.83s. Não usar aceitefraco para esse regime; ajustar passo/
estratégia econferirconvergência. A referênciaDOP inicial1e-10/1e-12 também
nãoera fina o bastante; refinada a1e-12/2.5e-14 semafrouxar limiteBoris.
Esses resultados não aprovam10milEM comfontesintensas/arbitrárias, catálogo planetário,
malha relativística ouC2-12 completo. Baseline0.4congelada em
output/c212-em-v04-product/LEIA-CANDIDATA.md; potencial em candidata separada.

Em 20/10, a regressão de 128 cargas mútuas no motor EMcloud
`native-em128-c212mutnewa-review.json` reprovou quadros: p95 de
37,376/39,485/41,117 ms e p99 de uma subrota 50,816 ms, mantendo taxa e
conservações aprovadas. O diagnóstico isolou acumulação de tópicos Lua já
respondidos na conexão nativa: 5.000 respostas concluídas em conexão extra
elevaram p95 de 32,446 para 47,540 ms; fechar essa conexão recuperou
35,278 ms. O controle registra o envelhecimento entre condições e não é
aceite de desempenho. Dados em `native-topic-retention-original1.json`.
Motor separado `.runtime-topic-cleanup` retira tópicos concluídos no preSync
seguinte, preservando os pendentes e assinaturas. O teste nativo real passou
4.096 callbacks distintos, 128 reutilizações sequenciais, 128 callbacks com
o mesmo ID em voo, assinatura viva/cancelada/recriada e 12 desconexões antes
da resposta. Recibo `topic-cleanup-native-lifecycle-check.json`. Física e
motores existentes foram preservados. O controle corrigido ficou em p95
16,978–17,164 ms nas quatro condições, incluindo 5.000 respostas concluídas.
Perfil formal `native-em128-c212mutfixa-review.json` APROVADO: mesmas três
rotas de 60 s/30 s/1080p, p95 máximo 17,081 ms, p99 18,581 ms, taxa mínima
0,998090 s/s e zero quadros acima de 100 ms. Vinte pausas ≤53,945 ms;
RAM somada 1,17995 GiB e WDDM 2,96085 GiB < DXGI 7,19014 GiB.
Auditor independente validou fontes/patch/receipts, dados brutos, subrotas,
recursos e conservações: energia ≤7,515e-15, momento ≤2,167e-15 e momento
angular ≤1,738e-15. A reprovação anterior continua preservada. Regressões
de interface/persistência, potencial e perfil de 10 mil no motor corrigido
ainda precisam passar antes de promoção; não é aceite completo de C2-12.
Atualização posterior: regressões nativa/CEF da nuvem, CEF do potencial,
restart normal de ambos e perda real de ACK passaram no motor corrigido.
Capturas foram inspecionadas, sem aceite geral de acabamento. Perfil
`native-emcloud-c212src128fixa-review.json` APROVADO: três rotas de 60 s/30 s,
10 mil partículas e 128 fontes fracas, p95 máximo 18,293 ms, p99 19,822 ms,
taxa mínima 0,999589 s/s; vinte pausas ≤115,653 ms. RAM 1,27044 GiB e
WDDM 2,96698 GiB < DXGI 7,19014 GiB. Fonte, F64, quadros e recursos foram
auditados; referência DOP853 independente deu erro ≤3,478e-5 e energia total
≤1,187e-11. O perfil formal de potencial c212potfixa segue em execução;
regime intenso e integração/acabamento permanecem pendentes. Sem promoção.
Atualização seguinte: c212potfixa foi aprovado com p95 máximo 17,084 ms,
p99 18,299 ms e vinte pausas ≤61,475 ms. Os três perfis, motor e regressões
foram congelados sem promoção. O regime intenso q±1e-10 C passou no ensaio
fine1 com 1,28/2,56/5,12 milhões de passos em 20π s: erro
2,617e-4/6,544e-5/1,636e-5 e energia ≤1,223e-9; razões de convergência
3,99909/3,99864. Auditor stdlib conferiu endpoints, energias e integridade;
referência DOP853 usa fórmula independente. Archive e recibos separados
preservam a rejeição dos passos anteriores. Não é desempenho nativo intenso.
A cópia F de controles numéricos mantém o núcleo 0.4 idêntico e declara uma
geração separada do harness. Worker e CEF verificaram passo, ritmo, guardas,
histórico limitado e preferências seladas; reinício normal reproduziu 777
passos contra processo legado. Falhas reais de gravação de preferências
retornam save parcial e preservam a fase válida. O perfil de 128 dessa cópia,
com 64 registros numéricos, passou em `native-em128-c212time128a-review.json`:
três rotas de 60 s/30 s/1080p, p95 máximo 17,595 ms, p99 19,886 ms,
taxa mínima 0,999426 s/s e zero quadros acima de 100 ms. Vinte pausas
≤60,640 ms; RAM 1,16099 GiB e WDDM 2,96475 GiB < DXGI 7,19014 GiB.
O auditor confere a geração separada do harness e as 64 entradas nos estados,
além do núcleo/quadros/recursos/conservações. Perfil de potencial dessa cópia
estava em execução. Em21/10, o potencial F passou: p95máximo17,469789ms,
p9919,330896ms, taxa mínima0,999448534,20pausas≤52,743ms.
A nuvem F teve tentativa A interrompida antes dos quadros por bloqueio do
sinal do coletor e B reprovada por taxa0,843525526 na rota2, com ciência e
quadros aprovados. Ambas foram preservadas. Após diagnóstico sem alteração
dos núcleos/limites, C passou com p9518,114220ms/minrate0,999177437 e D,
no mesmo processo, com p9518,044091ms/minrate0,998182482. Referências DOP853
e recursos passaram em ambas. A causa exata da falha B continua indeterminada;
as capturas aceitas não são garantia contra pausas de escalonamento.
F congelada emc212-em-time-candidate-20261021.tar.gz,192files, sem promoção.
Instalado3.13 restaurado/ready e82arquivos+owner conferidos antes de G.
G é cópia separada para integração: núcleos/workers byteiguais, interface
nova e instrumentos somente de leitura. em-integration-measurements-check.json
passou20casos contra fórmulas escalares de campos/força/energia/potência e
trabalho por diferença do potencial estático. Não é soma do trabalho de todos
os passos nem inclui reservatórios externos/energia do campo. G ainda exige
CEF, reinício, revisão visual e perfis próprios. Atualização posterior:
em-integration-native-ui-release2-check.json passou17verificações/zeroJS,
incluindo partícula definida,referênciasq/m,cinco presets,8combosE/B,
exportação,save/restore eárea≥65%/pausa acessível em100/150%.
em-integration-navigation-release1-check.json passou16combosdasquatroforças,
preservando efeitos internos e limpando/pausando laboratórios ao alternar.
em-integration-restart-check.json conferiu restauração e777passos exatos
emlotes≤32,sem mudar o limite do worker. Falhas iniciais dos harnesses foram
preservadas: boundssemzoom,comparação de dict semeffects,pedido777>32.
Não são falhas de física nem reclassificações de aceites anteriores.
Revisão visual cobre só layout pequeno pausado; perfis G e fechamento
integrado continuam pendentes.

## 10. Aceite de conteúdo e integração científica

Auditar os números do ESCOPO-CIENTIFICO.md por IDs distintos; os 12 destaques
são subconjunto do Solar. Conferir amostras e todos os objetos destacados
contra fontes. Cada destaque precisa de ficha visual, origem e investigação
utilizável; cada um dos 32 cenários precisa de edição, leitura, comparação,
pausa, salvar/reabrir e explicação do domínio, sem console.

Adicionar às seis cenas visuais originais: mapa gravitacional com duas sondas,
hélice carregada com campo legível, magnetismo terrestre, lente e buraco negro,
e observatório com trânsito. Congelar câmeras/parâmetros e inspecionar vídeo,
legendas, seleção e contraste. Intensidade de efeito não deve esconder o objeto.

Medir separadamente Atlas, gravidade avançada, EM e raios relativísticos com
o protocolo de frames da seção 4. Registrar resolução interna, amostras e idade
dos campos. Revalidar pausa ≤250 ms nos perfis aprovados e degradar apenas
detalhe visual quando preciso, sem relaxar precisão científica silenciosamente.
Metas de 256 massivos/10 mil partículas e 1 milhão de estrelas são perfis
diferentes; nenhum resultado aprova automaticamente sua execução simultânea.

Em C2-17, introduzir falha de cada worker em cópias de teste: Atlas permanece
responsivo, diagnóstico identifica o modelo, checkpoint retoma pausado com
sondas/campos/observador compatíveis. Troca de modelo invalida previsões antigas.
Testar versão desconhecida, pacote ausente e exportação; repetir ciência só
quando integração alterar solver, unidade, tempo, coordenadas ou entrada.

## 11. Quatro forças e controles independentes

Obrigatório: QUATRO-FORCAS.md. Primeiro relatório em evidence/forces-check.json
valida os quatro casos iniciais e 16 combinações de controles. Não aprova GN
ou toda a interação forte/fraca. Nuclear usa dados REACLIB/AME2020/NUBASE2020
fixados em data/science, com hashes e fonte; não supor incerteza nula.

Para cada modelo, testar atuação ligada/desligada × visualização ligada/desligada.
Ocultar não altera resultado físico; referência independe da atuação. Gravidade
sem atuação mantém fontes e produz movimento balístico. Canais nucleares
suprimidos preservam estado inicial sem inventar desintegração do núcleo.
Composições conservam número bariônico e carga incluindo produtos leptônicos.
Redes completas precisam comparar energia liberada, depositada e perdida por
neutrinos; não usar energia Q inteira como calor sem hipótese de deposição.

A bancada atual D+T usa temperatura/volume prescritos e taxa com barreira
eletrostática fixa; não aceita essa taxa como previsão de um universo sem EM.
Neutrinos no decaimento são contados; seu espectro energético ainda é pendência.
Referência de meia-vida é distinguida de vida média. Mudança de atuação é
intervenção explícita e não erro de conservação espontâneo.

Ampliação de12/10: controles de efeitos por cenário, incluindo componentes
E/B independentes; comparei as4 combinações com uma ODE de Lorentz separada
(erro máximo2.47e-11 em unidades de Larmor). Lei beta agora inclui nêutrons,
trítio e carbono-14; conserva A/carga incluindo elétron e conta antineutrinos.
Edge confirmou os controles/seleção de espécies; schema2 carrega schema1
após validar hash original, sem invalidar silenciosamente arquivos anteriores.
Evidências nos mesmos relatórios forces-check e forces-ui-check atualizados.

### Evidência nativa coletada12/10: estado parcial G0

Build próprio abre naRX7600/OpenGL4.6; nove rotas1080p (3×60s por perfil,
30s de aquecimento) mediram74–75FPS, p95 máximo15.74ms, p99 máximo18.48ms e
zero frames>100ms. Arquivo bruto:native-benchmark.json, com hash da versão
medida; VSync emmonitor75Hz. Soma residente máxima.956GiB pode repetir páginas
compartilhadas; DXGI do processo-motor2.901GiB, não VRAM agregada de todo produto.

Perfil offline: externalHTTP negado emHttpRequest/DownloadManager e proxyCEF,
com provas de negação e conexão local preservada emnative-cef-check.json.
Cache de aplicativo novo; cache de disco doSO não foi esvaziado. Cena27.543s,
CEF conectado34.612s, captura útil concluída36.222s. Meta≤15s não atingida.
Correção do lançador reenvia aURL local só na inicialização para evitarabout:blank.

Smoke da sessão no build próprio passou32/128corpos, massa, pausa,checkpoint
e retornoAtlas. Primeira alteração de massa teve timeout apesar de aplicada;
repetição quente passou. Registrar e diagnosticar ACK/recuperação fria; não
atribuir essa falha ao modelo físico sem evidência. C2-00/G0 continuam abertos,
com pontos fortes medidos e pendências específicas; não repetir nove rotas
sem mudança gráfica ou nova falha que justifique.

Relatividade exterior passou quadratura independente (7.45e-10rad máximo),
limite fraco,8combinações e CEF nativo. Isso não aprova todoGR/GUI final.

### CNO-I e redes:12/10

evidence/cno-check.json: erro relativo de taxa1.24e-14; derivadas comparadas
ao pynucastro com diferença1.05e-9 mantida por normalização rho/m_u vs mol/g.
Seis canais individuais e oito gatesforte/fraca/EM; visibilidade independente;
betaN13/O15 por meia-vida analítica, conservação de carga com pósitrons,
bárions1.78e-15/catalisadores1.06e-15, cantos do domínio e refinamento.
Erro de composição refinada5.99e-15/energia1.89e-15rel nesta configuração;
isso não mede incerteza experimental das taxas nem valida hotCNO.

cno-ui-check e networks-ui-check passaram emEdge: oito curvas, avaliação
beta explícita, canais separados, taxa por instante, probes de densidade,
vistas sem alteração física,720px sem overflow e zero errosJS.
native-networks-check passou as duas redes noCEF já existente e gerou
cosmos2-native-{cno,stellar}-network.png. Diagramas não são cenas de posições
nucleares; T/rho prescritas, sem transporte/feedback/luminosidade superficial.

### Diagnóstico do primeiro ACK e gravidade binária:12/10

FalhaACK reproduzida em worker novo sem renderer. Dump de threads localizou
importNumPy emREBOUND Particle.__getitem__; não era fila de respostasLua.
evidence/worker-intervention-before-fix.json preserva o stack. Sessão agora
seleciona a partícula viva por iteração pública, sem mudar solver/coordenadas.
Worker novo confirmou primeira massa em.526ms; checkpoint/restauração exatos,
sem stderr. Smoke em abertura fresca passou32/128/massa/Atlas/checkpoint;
trace28168:ACK2.338ms/HTTP5.411ms na massa. As taxas científicas não dependem
dessa otimização. Origem de eventual lentidão geral de importDLL não foi
diagnosticada; o caminho desnecessário foi removido. G0 ainda tem abertura/VRAM.

Binary: comparação de trajetória com REBOUND inercial3.81e-14a, Jacobi1.87e-15,
potencial e tensor de maré por diferenças finitas~6e-11, traço do vácuo~1e-16,
cinco equilíbrios, L4, quatro gates e escala de massa. Referência não muda
ao suprimir atração; sem forças, trajetória inercial é balística. Limite0,02a
testado sem classificação falsa de colisão. UI/CEF passaram seleção de fonte,
campo mantido, potencial/maré por clique e vistas sem alterar física.
Evidências binary-gravity-check,binary-ui-check,native-binary-check e PNGs.

Contratos/unidades:science-contracts-check verifica oito modelos, hashes de
código/dados, unidades, parâmetroafim sem confusão de relógios, JSON e
identidadecientífica invariável ao esconder referências. canonical-units-check
verificaGcan=1,T0/M0/L0, período2corpos, checkpoint explícito/legado e recusa
binding incompatível sem mutação. verify-session e worker-intervention passaram
após a adiçãoSI, sem reintroduzir importNumPy no worker. Smoke nativo atual
passou32/128/massa/checkpoint/Atlas; CEF mostrah/hporsegundo.

EM: em-readings-check verifica8combinações de carga/E/B, qE+qv×B, F·v,
potênciaBsemtrabalho e balançoK−K0−trabalho1.32e-15rel. UI Edge e CEF real
conferemE/B/ambos, unidadesV/m, probe temporal e referências com atuaçãooff.
Evidências em-readings-{check,ui-check},native-em-readings-check e PNGs.

### Memória de GPU por processo:12/10, nova janela de cota

collect-gpu-memory.ps1 confere cenário/worker pela API Windows em cada amostra,
identifica filhos do motor/servidor e registra contadores GPU Process Memory.
Atlas e P32 em movimento tiveram60amostras a1s: soma dedicada máxima2.957703 e
2.958679GiB, respectivamente. Inclui OpenSpace_Helper/CEF, além do motor.
Os contadores por processo incluem recursos compartilhados entre processos;
a soma pode superestimar a alocação única. Não chamar isso deVRAM exclusiva.
GPU Adapter Memory registra o adaptador inteiro, inclusive outros aplicativos.
DXGI consultado separadamente continua medindo uso/orçamento do motor apenas.

Evidências gpu-memory-{atlas-validated,laboratory-p32-running}.json; conferência
final do coletor emgpu-memory-atlas-guarded.json (3amostras, cenário e hash
do script estáveis). O coletor foi editado durante a primeira coletaAtlas;
seu JSON declara que o hash tomado ao final não congela o código executado.
Versão atual captura o hash antes e recusa alteração durante execução.
gpu-memory-laboratory.json antigo foi marcado REJECTED por rótulo incorreto;
não usar como laboratório. Cenário incompatível foi recusado antes da coleta.

São diagnósticos estáticos, sem os três percursos da medição gráfica formal.
Não aprovam G0 nem substituem o benchmark de frames anterior. Considerar o
defeito de contadores documentado pela Microsoft para Windows10; não afirmar
que ele foi reproduzido ou descartado nesta instalação Windows11.

### Leitores e diagnóstico de abertura:12/10

cold-start-diagnostic-20261012.json, mesmo motor02c36582…, cache de aplicativo
novo: API30.595s, CEF36.688s, PNG38.470s. Servidorlocal2.321s. Mantido o
resultado anterior; não alegar melhora antes de medir o build alterado.
Log preservado emoutput/startup-diagnostic-20261012: inicialização da galáxia
concentrou14s; tela de carregamento emitiu1.778avisos de glifos inválidos.

native-readers-check.json compara todos os3.269.410pontos COFF com o parser
std::istringstream upstream noMSVC:22.885.870floats, zero diferenças de bits.
Tempo acumulado dos parsers7.385s/1.591s; não é tempo de abertura nem FPS.
63.486escalaresBMP comparados à conversãoUnicodeWindows; UTF8malformado,
surrogates/limites e fallback fora doBMP testados. Leitor rejeita campos
faltantes, extras, não finitos e números malformados. Não confundir os pontos
do modeloNAOJ com catálogo observado ou converter sua escala silenciosamente.
O build finala37f248e… passou. O helper por blocos1MiB também foi conferido
contra todos os22.885.870floats, com zero diferenças, inclusive fronteiras
entre blocos/CRLF/EOF. native-readers-check.json registra hashes e tempos:
referência7.56638s, parser1.60206s, leitura+comparação por blocos1.6204s.

cold-start-bulk-20261012.json, cache do aplicativo novo e cacheSO desconhecido:
API12.20045s, CEF13.29948s, PNG útil concluído14.87788s. Meta15s passou nesta
coleta; a captura é limite superior do momento de exibição, não timestamp de
apresentação GPU. Zero avisos de glifo. Capturas loading/ready nativas revistas:
acentos e travessão corretos; Terra, atmosfera, catálogo e interface mantidos.
Não generalizar esse resultado como partida com cache de disco frio.

verify-laboratory.py no build atual passou32/128corpos, massa, pausa, retomada
exata e ida/voltaAtlas. native-cef-check.json associa o recibo atual e passou
controles científicos/offline/loopback, sem errosJS. O benchmark formal novo
native-benchmark-g0bulk.json está em coleta, incluindo GPU por processo; não
substitui silenciosamente o arquivo histórico native-benchmark.json.

### DecisãoC2-00/G0:12/10/2026, builda37f248e…

Aceite local concluído; G0-DECISAO.md substitui o estado parcial histórico.
native-benchmark-g0bulk-review.json auditou9coletas e66amostrasGPU por coleta,
cobertura integral e hashes: mediana mínima74.424FPS, p95 máximo15.661ms,
p99 máximo16.540ms, zero>100ms; residente1.00232GiB, soma dedicada por processo
2.99185GiB, orçamento mínimoDXGI do motor7.19014GiB. Método conservador com
compartilhamento declarado; contadores não significam VRAM exclusiva.

UI nativa passou busca/cliques/câmeras, pausa128corpos9.249ms e zeroerrosJS;
imagensTerra/Lua/ViaLáctea revistas sem artefato impeditivo. Metaabertura15s
passou em uma coleta com cacheSO desconhecido. Build/oficial/offline/worker
estão rastreados nos recibos citados na decisão. Não atribuir esse aceite aos
marcosC2-01–20, qualidade visual final ou desempenho do pacote completo.

### Dipolo3D prescrito:12/10

Especificação anteriorDIPOLO.md e resultado dipole-check.json: campo contra
fórmula esférica4.15e-16rel; divergência/rotacional1.95e-8normalizado; escala
r^-3/inclinação/linhas analíticas tangentes conferidas. Quatro combinações
Newton/Lorentz, gatesmaster/efeito e visibilidade independentes, reta sem
forças, potência magnética nula até arredondamento, limitesinterno/externo e
recusa de orçamento explícita. EnergiaK+Uaplicado1.05e-8rel no preset; RK45
independente3.46e-11R em5s; refinamentoDOP8531.88e-8R em40s. Latitudeespelho
difere0.1386° da previsãoadiabática, não precisãoobservacional.

UIEdge/CEF passou camposB/g, potencial, sondagemtemporal,5curvas selecionáveis,
visualização sem alterar identidadefísica, fonte/referência preservadasBoff,
720px e zeroerrosJS. Capturas nativas finais revistas; legendas ocultadas
quando inaplicáveis e inversãov_parallel comBoff explicada. Regressões redes
pp/CNO/EMuniforme e9contratos passaram. Nenhum aceiteIGRF/plasma/colisão.

### IGRF14: 13/10

Contrato prévio IGRF.md, verify-igrf.py/igrf-check.json: 58casos contra BGS
Fortran original compilado por GNU13.3, incluindo1900/1995/2025/2030, polos,
interpolação, altitude1000km, campo geocêntrico e variação secular. Máximo por
componente0,0145434nT (<1nT), geocêntrico0,00435173nT. Diferenças de constantes
arredondadas preservadas. Grau1 cartesiano3,98e-16rel, polosECEF/periodicidade/
conversões conhecidas, oito combinações de carga/gates, qv×B e potência nula,
identidade sob visibilidade e recusa fora do domínio passaram. Fixture58casos
reproduzido pelo script collect-igrf-reference.py com SHA7837fdb5… idêntico.

Dez contratos passaram, IGRF spatial_snapshot704pontos sem evolução temporal;
UI Edge mapa/globo/sonda/componentes/grau1/época/polos/720px/zeroerrosJS passou.
Painel de sonda separado após revisão visual; rotação do globo conferida.
Comparação de código não mede a precisão observacional do campo terrestre.
verify-native-igrf.py/native-igrf-check.json passou no CEF nativo, com globo,
mapa, sondas, componentes, comparação e controles independentes. Capturas
nativas globo/mapa revistas; grade é a superfície geográfica, não espaço-tempo.

### Persistência da geração científica:13/10

Configuração esquema3 guarda modelo, hashes de código/dados e versõesPython/
NumPy/SciPy. Hash do envelope inclui condições e geração; esquema1/2 migram
com geração desconhecida explícita. verify-force-persistence.py passou dez
modelos, cinco corrupções, diferenças de código/dados/runtime, condições
preservadas e recusa de entrada inválida sem sobrescrever o arquivo anterior.
Isto é procedência de condições, não checkpoint de solver ou garantia bit a
bit entre máquinas. UI Edge/CEF são verificações separadas, em andamento.
UI Edge e CEF nativo passaram retomada mesma/mudada/antiga e recusa de corrupção
sem recalcular. Arquivo original do usuário restaurado; imagem de aviso nativa
revista, destacando a causa da mudança sem prometer checkpoint dinâmico.

### Atlas solar JPL:13/10

atlas-check/native-atlas-check:5épocas1950–2050, IDs/unidades/centro0/ICRF/NONE,
SPKcov porcorpo, km↔m/velocidade por diferença temporal, Lua−Terra porconsulta
relativa e rotação ortogonal. Leap2016 preservado, seis datas inválidas recusadas.
FourfixturesHorizonsDE441 vsDE442s:160.15–180.47m, limiteprévio1km. Pipeline,
não incerteza observacional. RendererGALACTIC composiçãoJ2000, maiorresíduo
posição0.00003052m/rotação1.11e-16; época inválida preserva estado nativo.

native-atlas-ui-check:epochconfirmado/pausado, distânciamuda, ida/voltaLab
preservaepoch, mudançaAtlasnoLabrecusada, originalrestaurado e zeroJS. Câmera
iluminada medida cos30°0.8660254, chaveReferenceFramevalidada. Terra/Lua finais
revistas. RecorteinicialRootJ2000 passou coordenadas mas FALHOUrevisãovisual;
diagnóstico preservado, substituído pelo resultado final sem ocultar falha.
### Acervo nuclear AME2020:13/10

verify-nuclei.py passou3.558IDs/N+Z=A,14.232campos contra tokenização independente,
incertezas/estimativas e295ausênciasbeta. Noveâncoras por valores fixos, ligação
por massas com resíduo≤4,494e-5keV/núcleon e coerência com excesso de massa emtodos
osregistros pelos arredondamentos. Comparação3.558IDs doNUBASE/pynucastro mostra
diferenças até5keV e exceçãoO16=7e-5keV, menor que sigma3e-4keV; registrada, não
eliminada. Corrupção de linha/duplicata/save recusadas e geração alterada avisada.
Edge/CEF passaram mapa, clique, curva, comparação,filtro/sonda,ausências,JSON
local e salvar/retomar; Edge720px semoverflow e zeroerrosJS. Imagens nativas
revistas; corrigidos rótulos sobrepostos. É instrumento de referência, sem
meia-vida porB/A, trajetória ou decomposição da ligação emforças. Não é aceiteC2-18.

### Contratos/pacotes/cópiaC2-01 —13/10

Aceite local emC2-01-DECISAO.md. verify-atlas-import: cincoépocas, inversa
1,526e-5m/3,638e-12m/s, superposiçãoSI2,56e-12m/s², DOP85324h0,0002442m;
nove entradas inválidas sem mutação, retomada exata egeração diferente indicada.
verify-packages-properties: dezpacotes/34arquivos/894541883bytes iguais aos
recibos/extrações, todos os dados científicos atuais registrados, corrupção de
mesmotamanho/tamanho/ausência/path/duplicata recusados emfixtures. Symlink
externo conferido porPythonLinux; não confundir com teste de criaçãoWindows.
21propriedades coerentes, quatro metadados inválidos sem mutação echeckpoint
movido entre pastas com espaços. Incertezas ausentes e contribuiçãoG separadas.

CEFreal: cópia pausada/coordenadas locais0diferença, massa no IDexp, histórico,
checkpoint/reinício/retornoAtlas/P32/P128; abrir dados pausa e preserva cópia.
Campo editado conserva entrada mesmo apósblur/polling. UIde propriedades e
pacotes passou filtros/fontes/termos/verificação/JSONlocal e retorno; Edge720
semoverflow, zeroJS. Imagens revistas após corrigir rótulos/câmera/eixos/busca/
tamanhos pequenos. Relatórios atlas-import-check/packages-properties-check/
native-atlas-import-check/content-ui-check/native-content-check e reviews.
Não repetirG0 nem atribuir esse aceite à versão completa.

### Reexecução das quatro forças e integração solar —23/10 UTC

`evidence/four-forces-recheck-20261023.json` registra14grupos aprovados,
fontes arquivadas, recibos antigos preservados e ponteiro do dono idêntico.
`RELATORIO-TESTES-FORCAS-20261023.md` explica resultados e exemplos; o plano
`PLANO-INTEGRACAO-SISTEMA-SOLAR.md` exige validação conjunta posterior.
Essa rodada não é jornada nativa, benchmarkJ ou aceite do Sistema Solar.

### Aceite local C2-18 e misturas de fusão —13/10

C2-18-DECISAO.md delimita acervo/Q/limiares/fusão; não é aceite da v1.
Contratos anteriores NUCLEOS/ENERGIAS-NUCLEARES/FUSAO-CANAIS. verify-fusion
passou sete taxas (7,07e-14rel), composição/extensões contra ODE independente
(1,06e-12/5,30e-13n0), balanços A/Z4,45e-16rel,66gates/48limites, exposição
mínima e esgotamento. Pares idênticos1/2, ramos D+D concorrentes e alteração
de queima com T/densidade a duração fixa; sem inventar reação dos produtos.

verify-fusion-ui Edge/--native passaram seis misturas, taxas/composição/energia
por tempo, gatesDD/EM, referência e identidade física preservadas, save/load da
geração e JSON local igual à saída backend. JS Number não é autoridade para
representação decimal de números grandes. Erro de dtypeobject com JSONinteiro
grande corrigido parafloat64 e coberto. Imagens finais reais revistas após
corrigir rótulo final e rodapé do eixo (fusion-visual-review.json),720semoverflow
/zeroJS. Contratos de11modelos e persistência passaram. Onze pacotes/42arquivos
agora registrados; o aceiteC2-01 histórico continua correspondente à sua geração.

### Aceite local C2-19 —13/10

Decisão C2-19-DECISAO.md após DECAIMENTOS.md:10pais/19ramosbeta−/beta+/EC,
alimentaçãoSr90→Y90→Zr90, larguras parciais independentes e fontesfixadas.
verify-decays passou102gates/40limites: meia-vida1,12e-16N0, Radau1,43e-12N0,
Bateman6,67e-16N0, balanços2,99e-14rel. ENSDF/NUBASE e médias e/ν/Q divergentes
conservadas, normalização impressa explícita. Sem calor/spectro inventado.

Edge720 eCEFnativo percorreram dezcasos, F18ECsempositrões, Sr/Ytransiente e
alimentação comYsuprimido, consulta das fontes/incertezas, save/loadgeração e
JSONreal igual ao backend. Cena/worker preservados,zeroJS/semoverflow; imagens
representativas revistas emdecays-visual-review.json. Dozecontratos e
persistência/pacotes passaram,12pacotes/64arquivos/895410499bytes. Regressões
iniciais e fusão passaram; nenhum novo build oubenchmarkG0 atribuído.

C2-02 aprovado localmente13/10: NAVEGACAO.md/decisão própria. JornadaCEF
Terra→Lua→Saturno→favorito, seleção/filtro sem mutação, modos com pose/época
preservadas, voo livre/tecladoWindows/foco, viagens/cancelar, relógio nos dois
limites, arquivos inválidos recusados, UI150% e regressõesAtlas/cópia/checkpoints.
SAT441699+DE442s em cincoépocas, máximo0,000244m; subset201épocas idênticas.
13pacotes66arquivos903760474bytes. atlas-route-c202b: três15s1080p,
74,997–75,061FPS, p99máx15,256ms, zero>100ms. Captura inicialc202 preservada
como método inválido (fechamentoWS por janela); corrigida para conexão contínua.
C2-03 mantém aceite visual separado; anéis/qualidade ainda não aprovados.

C2-03 aprovado localmente13/10: QUALIDADE-VISUAL/decisão própria.13capturas
revistas comhashes emvisual-review.json; detalheEarth inicial rejeitado e
limitado, fonteativaSaturnoOpenSpace identificada, oclusãoelipsoidal de rótulos.
verify-visuals e regressãonavegaçãopassaram, fontesEdge720passaram.
atlas-route-c203b:3×15s1080p,74,943–75,019FPS,p99máx15,381ms,zero>100ms.
GPUproduto3amostrasmáx2,97GiB(somacompartilhamentodeclarado), RAMsnapshot
1,0544GiBresidente/4,2963GiBcommitprivadosomados. Modelo semterreno/fotometria
observada/dinâmicadeanéis; não substitui G0 ou candidata v1.

C2-06 primeira fatia, SEMaceiteinteiro: set_bodySI transacional,frame/ID/
revisão/limites,22inválidossemmutação,E0relativodesconhecido/absolutodisponível,
balanços/checkpoint. DOP853 pósedição difere<=2,85e-5m. CEFP32/P128/cópiaAtlas
passou3jornadas,massa/fase/renderlocal<=1,53e-5m, fonte/pointerpreservados,
semJS. body-editor-check/body-editor-ui-check; não inclui criação/raio/spin.

### Editor C2-06: validação final em andamento — 14/10

Geração editável 3.4.0: cadastro/criação/remoção, atributos, cônicas,
conservação, três experiências controladas e sonda básica. Contratos próprios
EDITOR-GRAVITACIONAL.md, RAIO-SPIN.md, ORBITAS-EDITOR.md, ENCONTROS.md e
SONDAS-BASICAS.md. Os ensaios de estado/checkpoint recusam entradas antigas e
metadados incoerentes antes da instalação; fonte Atlas e IDs preservados.

Duas órbitas inclinadas com e=0/e=0,6 e massas comparáveis foram propagadas
por 100 períodos: diferença para CSPICE conics <=3,681 mm na escala L=1e9 m,
Erel<=2,65e-15, Pnormalizado<=1,28e-15, Lnormalizado<=7,37e-16. Refinamento
IAS151e-12 difere<=2,74e-12 do semieixo; checkpoints finais exatos. Isso mede
o integrador no modelo pontual, sem comprovar observação ou estabilidade geral.
Sonda pontual: solução analítica/superposição e −grad Φ por diferenças finitas
<=1,88e-10 relativo, fixtures2/32/128/Atlas,48 entradas recusadas sem mutação,
binário e ponteiro de checkpoint idênticos.

CEF nativo passou criar/remover/editar nos quatro modelos, raio/spin,
propostas elíptica/hiperbólica/radial, referências/Atlas e sonda. Uma falha
transitória de resposta CDP ao clique não foi ignorada: sequência interrompida,
worker respondendo, motor recuperado, nova jornada edge concluída. Nenhum
percurso de desempenho começou nessa tentativa. Recibos/capturas preservados.

A revisão visual rejeitou o primeiro conjunto com letras sobrepostas:
RenderableLabel upstream usava coordenadas absolutas float32 em1e14 m.
Novo camera-relative-label.patch conserva posições científicas e monta glifos
próximos da câmera. Reprodutor de precisão:20 posições horizontais distintas
viravam1; novo caminho conserva20. Compilação incremental/manifesto SDK e
estágio passaram; EXE c308114c…27f4d0, runtime oficial intacto. Capturas de
sonda/hipérbole revistas com letras completas. Afastamento dos rótulos da
grade e tamanho por enquadramento são adaptações de exibição.

Ainda falta o recibo formal P128 e regressão proporcional do novo build.
Os nove percursos G0 a37f248e… continuam históricos; não atribuí-los ao novo
EXE. O primeiro c206p128 incompleto é diagnóstico de timeout ao criar512nós,
resolvido por lotes de8corpos (~8,6–9,4s para criar a cena). Não é frame time
nem abertura inicial do aplicativo. C2-06 continua sem aceite enquanto os
critérios finais não forem conferidos. C2-11 possui apenas contrato/protótipo
matemático separado em output/c211-staging, sem instalação no produto.

P128 c206p128b concluído/auditado: três60s/30s/1080p,128massas ativas,
taxa>=0,9999759u/s para1; Erel<=7,75e-15, Pnorm<=6,88e-17, Lnorm0 nos
estados registrados. Mediana máxima12,828ms, p95máx23,985ms/p99máx25,828ms,
zero>100ms;20pausasAPI com máximo36,944ms e câmera33,706ms. Soma RAM1,13057GiB,
GPU dedicadaWDDM2,99091GiB com compartilhamento, orçamentoDXGI mínimo7,19014GiB.
Hashes, geração atual,66amostrasGPU/UTC/cenário/cobertura por percurso conferidos
por review-native-benchmark.py. Esse perfil passou; g0labels ainda em execução
para a regressão do EXE novo. Não converter o inverso da mediana de intervalos
em taxa média de apresentação (pacing variável nesta sessão75Hz).

### C2-06 aprovado localmente —14/10/2026

C2-06-DECISAO.md substitui as pendências históricas acima: ciência/jornadas/
dezimagens/P128c passaram noEXEcfcd. G0g0async4 completo/auditado:9rotas,
p95<=18,003ms/p99<=19,210ms,zero>100ms. P128c re-auditado com fonte congelada:
128massasativas,taxa>=0,9995616u/s,p99<=24,600ms,20pausas<=36,282ms.
Recibos físicos/visuais congelados em evidence/c206-final. Falhas anteriores
preservadas; não substituir por zeros nem misturar tentativas. Ver decisão
para limites e suspeita de cleanupWS fora das rotas quentes. PróximoC2-11.

### C2-11 parcial — sondas e campo3D instalados14/10/2026

Sondas3.5 passaram P32/Atlas no CEF nativo; erro de consulta do roteiro Lua
corrigido. Checkpoint/binário/referências/fontes/IDs preservados; export/stale/
câmera/exclusão própria/fonte removida passaram. Backup da fatia validada em
output/c211-probes-validated/manifest.json, sem alterar evidence/c206-final.

Mapas3.6: verify-field-layers passou quatro modelos,68comandos recusados e
24corrupções seladas recusadas antes da instalação. g/Φ/T por amostra exatamente
iguais ao avaliador de sonda; configure/sample não mudaram binário/pointer/fase.
Geração3.5 migra mapa vazio;3.6 sem bloco de mapa/sondas é recusada. Fonte central
removida mantém ID e torna medição indisponível. P128/569pontos~691ms no ensaio.
Regressões registry/atributos/órbitas/sonda passaram após a instalação3.6.

Tensor e cortes com --installed passaram: gradg<=1,268e-10rel, rotação<=8,343e-16,
traço<=1,172e-16normalizado. Massa isolada/contorno: erro de raio2,431%em17×17,
1,481%em21×21; plano<=5,514e-7m; potencial linear<=6,662e-16. Singularidade abre
quatro células com lacunas; platô não cria curva única. Curva é interpolada,
leituras físicas float64 separadas.

verify-gravity-fields-ui passou massa isolada/P32/Atlas: consulta de amostra
igual à sonda, todos os vértices das linhas confrontados com transformação
nativa/quantizaçãofloat32, mover/girar/linear/esconder/limpar/export/salvar/
restaurar/stale/âncora sobrevivendo à troca. Diferença gráfica máxima7257,492m
em mapas~3e10m, dentro do recibo; não erro da leitura física. Poll8,5–9KiB,
sem enviar385amostras completas por atualização. Três capturas revistas.
Perfilc211fields1 recusado por partep95 25,0158ms>25; fields2 também recusado.
Dados/fontes próprios preservados. A/B não culpou campo; tracing128/semcampo
apósreinício p95 20,553ms semhitches. Novo perfilfresco será separado.
Sem atribuir P128/G0 históricos ao produto3.6.
Séries/comparação/ramos/J2/marés/ressonâncias/256/10mil ainda impedem aceiteC2-11.

Perfil fresco c211fields3 aprovado/auditado:128massasativas+569amostrascongeladas,
p95<=22,264ms/p99<=27,325ms/zero>100ms/20pausas<=51,786ms. RAMsoma1,55343GiB/
GPUWDDMsoma2,45255GiB/DXGI7,19014GiB. Releituras sob pedido<=1662,380ms fora
das janelas formais. Recibo/sourcearchive próprios e backup3.6validado.
C2-11 parcial; candidatos de comparação/histórico3.7 ainda fora do produto.
