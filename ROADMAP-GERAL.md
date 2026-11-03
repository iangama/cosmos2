# Cosmos2 — roteiro geral, etapas e ciclos

Atualização de22/10local/23UTC: o pedido de testes explicados e integração
geral dos corpos está detalhado em
[PLANO-INTEGRACAO-SISTEMA-SOLAR.md](PLANO-INTEGRACAO-SISTEMA-SOLAR.md).
As fatias IS-0–6 ligam Sol/Terra/Lua/Júpiter aos marcos existentes, sem
renumerá-los ou atribuir aceite conjunto às bancadas isoladas. IS-0 passou
14grupos científicos: [relatório](RELATORIO-TESTES-FORCAS-20261023.md).

Revisão científica4.0,12/10/2026; previsão de execução substituída pela4.1.
**PLANO-UM-MES.md governa prazo/capacidade:** meta12/11/2026, cerca de seis
cotas completas equivalentes por semana; orçamento-base30 após renovação13/10.
As horas e conversões em ciclos abaixo são HISTÓRICAS, retiradas da previsão
atual por falta de calibração; não usá-las para anunciar meses de duração.
Pedido: revisar profundamente o plano inteiro,
pesquisar além das ideias anteriores e apresentar etapas e ciclos como no
Revenant. Este documento governa sequência, previsão e estado; conserva os
IDs e aceites do PLANO-DIRETOR.md. Não apagar evidências ou renumerar entregas.

## 1. Resultado pretendido

Um explorador do universo e laboratório científico para Windows: viajar entre
escalas, selecionar objetos, investigar matéria/campos, alterar condições,
medir consequências, comparar hipóteses e retomar sessões. Quantidade de
objetos, aparência e física precisam melhorar juntas. Nenhum cenário fecha
apenas porque uma equação, botão ou teste foi acrescentado.

O roteiro tem **27 marcos**: 21 da v1 ampliada (C2-00–20) e seis de aprofundamento
(C2-21–26). **C2-00, C2-01, C2-02, C2-03, C2-06, C2-18 e C2-19 aprovados localmente;20marcos sem aceite completo**, sendo14da v1 e
seis posteriores. Parte substancial de alguns marcos já existe. Os doze palcos
atuais são modelos/casos executáveis; o aceite de cada marco tem decisão própria.

A implementação local existente continua autorizada. O pedido atual prioriza
devolver este plano antes de aplicar novas mudanças. C2-21–26 são propostas
detalhadas de expansão; não alegar que foram construídas ou que suas bibliotecas
já estão instaladas/validadas. Sem despesas, publicação ou pessoas externas.

## 2. O que a revisão acrescenta

- Um caminho entre Atlas e laboratório: selecionar corpos reais numa época,
  copiar estados coerentes, escolher influências, editar e comparar sem perder
  o registro de origem. Isso precede o editor geral e evita órbitas sem contexto.
- Instrumentos comuns em vez de painéis isolados: sonda espacial/temporal,
  cortes, vetores, equipotenciais, comparação de duas versões, incerteza,
  exportação e histórico. Preservar interfaces especializadas quando a escala
  não tem posição clássica ou tempo de evolução.
- Campos, trajetórias e sondas espaciais integrados à cena 3D navegável do
  renderer, com seleção/probes sincronizados. Gráficos e redes nucleares ficam
  como instrumentos adequados a esses modelos, sem inventar posições clássicas.
  Não aprovar a integração apenas por mostrar um painel científico separado.
- Observação física: distinguir posição geométrica, emissão e recepção da luz,
  observador, fase, eclipse, trânsito e desvio de frequência. A nova fatia JPL
  continua geométrica até o contrato observacional correspondente.
- Resposta estelar com escalas: energia nuclear, neutrinos, reservatório térmico,
  equação de estado e perdas; perfis/evoluções de referência acrescentam estrutura
  além da zona. Não transformar desligar fusão em apagar instantaneamente o Sol.
- Matéria quântica, espalhamento nuclear, espectros beta e oscilação de neutrinos,
  plasma coletivo, potenciais galácticos e expansão cosmológica em etapas próprias.
- Conteúdo com investigações: 12 mundos em destaque, 32 experiências na v1 e
  24 adicionais na expansão. Cada experiência altera algo, calcula, mede e compara;
  variantes de cores ou sementes não contam como experiências físicas distintas.

O universo usa modelos por regime. Gravidade Newton/GR, Lorentz/Coulomb,
processos nucleares, matéria quântica e cosmologia não cabem num solver universal.
As forças forte/fraca não são vetores clássicos inventados apontando de todo
objeto para todo objeto. A atuação física e a referência visual permanecem
independentes; efeitos mistos declaram dependências. Suprimir operadores
mantendo a matéria é uma hipótese do experimento, não uma teoria alternativa
validada. QUATRO-FORCAS.md continua o contrato desses controles.

## 3. Estado real reaproveitado

| Área | Já existe | Ainda falta para fechar |
| --- | --- | --- |
| Base C2-00 | Build próprio Windows/OpenSpace, offline/CEF, worker e aceite G0 | Sem novo trabalho obrigatório; verificar regressões quando houver mudança relevante |
| Contratos C2-01 | Aprovado localmente: unidades, dez contratos, propriedades solares/fontes, dez pacotes verificáveis e cópia ramificada com checkpoint | Ampliações pertencem aos marcos de acervo/observação/edição/integração; ver C2-01-DECISAO.md |
| Gravidade C2-06/11 | Worker32/128, massa/pausa/checkpoint; campo radial e binário restrito3D | Editor livre, cópia de estados, comparação, J2/marés e perfis maiores |
| EM C2-12 | E/B uniformes, Lorentz, medições e dipolo com gravidade | Cargas/fontes editáveis, campos gerais, interação mútua e bancada unificada |
| Nuclear C2-18/19 | Ambos aprovados localmente: acervo/Q/limiares/seis misturas/sete taxas; dezpais/19ramos e cadeia Sr/Y, leptões/energia | Decisões próprias delimitam aceites; transporte/térmica e espectros aprofundados seguem C2-20/22 |
| Estrela C2-20 | pp-I e CNO-I com composição, energia/neutrinos e canais | Redes ampliadas e resposta térmica; T/rho hoje são prescritas |
| Planetário C2-13 | Dipolo e IGRF14 com globo/mapa/sonda | Trajetórias no campo real e ambientes externos com contrato próprio |
| GR C2-14/15 | Raios Schwarzschild, relógios e curvatura | Órbitas/precessão, observador, lente, Kerr e imagem relativística |
| Produto completo | Busca e câmeras iniciais, exportações, salvamento parcial | Navegação geral, superfícies, acervo, histórico integrado e pacote instalável |

O benchmark novo do Atlas JPL foi concluído: três trajetos de 10s, warmup 5s,
74,12–74,92FPS e p95máximo15,878ms. É regressão curta; o G0 formal tem outra
versão de cena e nove coletas3×60s. Não atribuir sua aprovação à expansão inteira.

## 4. Previsão histórica4.0 — substituída, sem validade de prazo

**Um ciclo = cinco horas de esforço focado equivalente.** A unidade segue o
acompanhamento usado no Revenant. Ela não mede quantas janelas de cotaCodex
serão consumidas, nem cinco horas corridas de autonomia. Cotas são observadas
pela telemetria real. Não há conversão conhecida entre esforço e allowance.

As faixas abaixo estimam **trabalho restante a partir deste estado**, incluindo
implementação, aquisição/curadoria, revisão visual, validação proporcional,
integração e documentação. Não somar horas já gastas nem recontar C2-00.
Limite inferior: arquitetura atual funciona. Superior: uma correção delimitada
de integração/modelo por frente. Troca total de motor, QCD de primeiros
princípios, hidrodinâmica completa e relatividade numérica não estão incluídas.

| Entrega | Horas restantes sem reserva | Ciclos de 5h | Figura central |
| --- | ---: | ---: | ---: |
| V1 ampliada, vinte marcos | 965–1.665h | 193–333 | 1.315h /263 ciclos |
| Aprofundamento, seis marcos | 490–880h | 98–176 | 685h /137 ciclos |
| Roteiro completo | 1.455–2.545h | 291–509 | 2.000h /400 ciclos |

Reserva de integração de 20% aplicada uma única vez: figura central da v1
**1.578h, cerca de 316 ciclos**; roteiro completo **2.400h, 480 ciclos**. A reserva
não é trabalho já aprovado nem deve ser somada novamente em cada etapa.
As faixas são previsões de engenharia, não probabilidades calibradas ou prazo.
Confiança média nas próximas etapas; baixa em terreno, Kerr, acervo e expansão.
Reestimar pelo trabalho realmente restante após cada prova importante. A faixa
histórica 432–768h descrevia outro escopo e não se aplica a esta revisão.

As horas são envelopes de baixo para cima por marco, não derivadas de um
registro medido de velocidade do agente. Toda etapa inclui cálculo/conteúdo,
interface, verificação pertinente e integração; dividir por5 só produz a
unidade de planejamento. Nas próximas provas registrar esforço real quando
disponível e revisar esses envelopes, sem inventar horas históricas.

## 5. Ordem da v1 e entregas por marco

Ordem conservada: **01→18→19→02→03→06→11→12→20→14→04→05→07→08→09→10→13→15→16→17**.
C2-00 está concluído. A numeração histórica não é a ordem de execução.
Salvamento, acessibilidade e validação acompanham cada entrega; os marcos de
integração consolidam compatibilidade, sem adiar esses requisitos para o final.

| Ordem / ID | Resultado para o usuário | Estado | Horas / ciclos restantes |
| --- | --- | --- | ---: |
| 1 / C2-01 | Contratos, propriedades com fonte, pacotes e transição Atlas→experimento | Aprovado localmente13/10; C2-01-DECISAO.md | — |
| 2 / C2-18 | Atlas nuclear, ligação, energia de reação e fusão manipulável | Aprovado localmente13/10; C2-18-DECISAO.md | Concluído no recorte do marco |
| 3 / C2-19 | Decaimentos/capturas, cadeias e produtos mensuráveis | Aprovado localmente13/10; C2-19-DECISAO.md | Concluído no recorte do marco |
| 4 / C2-02 | Navegação, busca geral, seleção, tempo e favoritos | Aprovado localmente13/10; C2-02-DECISAO.md | Concluído no recorte do marco |
| 5 / C2-03 | Terra, Lua e Saturno com qualidade visual aprovada | Aprovado localmente13/10; C2-03-DECISAO.md | Concluído no recorte do marco |
| 6 / C2-06 | Criar/editar sistemas gravitacionais a partir de dados ou do zero | Aprovado localmente14/10; C2-06-DECISAO.md | Concluído no recorte do marco |
| 7 / C2-11 | Instrumentos comuns e gravidade avançada | Parcial: instrumentos/ramos3.8 validados; J2 exterior3.9.1 validado ciência/worker/CEF/migração/perfis128 com1e4fontes; maré material3.10 instalada com ciência/persistência/CEF/migração/perfil2massas aprovados; ressonâncias3.11 aprovadas ciência/persistência/CEF/migração/perfil128;256massas3.12 aprovadas no perfilformal c211p256q3;10mil3.13 instalados18/10 comciência/worker/transporte/CEF/seleçãoSI/migrações eperfis c211cloud4+c211p256c2 aprovados;abertura padrão e quatro telasdeforças verificadas;novas camadas seguem nosmarcos definidos | 55–95h /11–19 |
| 8 / C2-12 | Bancada eletromagnética com fontes e cargas interagindo | Parcial: editor0.2, intervenções/persistência/migração e candidata18/10 com navegação, cena nativa E/B, linhas, sondas, exportação e retomada verificadas; perfis formais e aceite integrado pendentes | 45–75h /9–15 |
| 9 / C2-20 | Região estelar relacionando quatro forças e resposta energética | Parcial | 75–130h /15–26 |
| 10 / C2-14 | Comparar Newton/GR, precessão, relógios e lentes | Parcial | 45–80h /9–16 |
| 11 / C2-04 | Viajar entre sistemas, estrelas, Via Láctea e Andrômeda | Parcial | 65–110h /13–22 |
| 12 / C2-05 | Superfícies contínuas e mundos procedurais variados | Planejado | 85–145h /17–29 |
| 13 / C2-07 | Colisões, spin, calor e balanços no modelo declarado | Planejado | 40–70h /8–14 |
| 14 / C2-08 | Histórico integrado, ramificações e recuperação | Parcial | 35–60h /7–12 |
| 15 / C2-09 | Desempenho e instalação limpa do pacote base | Parcial | 30–50h /6–10 |
| 16 / C2-10 | Primeira versão intermediária demonstrável | Planejado | 10–20h /2–4 |
| 17 / C2-13 | Magnetismo terrestre/planetário e partículas no ambiente | Parcial | 45–80h /9–16 |
| 18 / C2-15 | Buracos negros com rotação e imagem calculada | Parcial | 100–175h /20–35 |
| 19 / C2-16 | Acervo curado, observatório e32 experiências completas | Parcial | 100–175h /20–35 |
| 20 / C2-17 | V1 ampliada integrada, offline e revisada | Planejado | 50–85h /10–17 |

### C2-01 — origem e contratos

Entregar manifestos verificáveis, unidade/referencial/época por propriedade,
incerteza e desconhecidos, IDs estáveis e cobertura por objeto. Resolver
observador/tempo de emissão/recepção onde aplicável. O usuário copia Sol/Terra/
Lua numa época para um experimento sem misturar SSB/J2000/GALACTIC nem massas
nominais com valores observados. Saída: estados/procedência sobrevivem à cópia,
consulta inválida não muda o motor e uma geração incompatível é informada.

### C2-18 — nuclear forte e ligação

Primeiro instrumento AME2020 de NUCLEOS.md: mapa N×Z, B/A×A, sonda, seleção,
incertezas, valores estimados e exportação. Acrescentar energias Q/limiares e
comparações entre fusão e canais avaliados adequados ao domínio. A ligação
total não mede isoladamente a força forte nem determina a meia-vida. Saída:
alterar condições muda taxas/composição/energia; todas as entradas preservam
flags/ausências. Espalhamento quântico mais profundo fica em C2-21.

### C2-19 — fraca e cadeias

Expandir o recorte avaliado para pelo menos oito casos distintos, incluindo
beta−/beta+/captura com ramificações quando os dados permitirem. Populações,
produtos, energia e neutrinos aparecem por tempo; ambiente da captura é declarado.
Saída: meias-vidas/ramificações e balanços verificados; desligar um canal
preserva a matéria inicial. Espectros completos/oscilações ficam em C2-22.

### C2-02 — navegar e selecionar

Busca por nome/tipo/proximidade e filtros; árvore de sistema; seleção por
clique; câmera livre/orbital/seguimento; favoritos e retorno; linha do tempo
com cobertura e modos Atlas/Experimento claros. Controles por teclado,
escala e contraste acessíveis. Saída: Terra→Lua→Saturno→favorito por interface,
sem terminal, perda de foco ou salto de câmera decorrente de uma edição.

### C2-03 — qualidade visual inicial

Terra, Lua e Saturno: iluminação, exposição, atmosfera/anéis/sombras, escala
e aproximação. Datas e posições consistentes, efeitos visuais de aumento
de tamanho indicados. Ficha e captura por mundo, revisadas no renderer real.
Saída: três percursos legíveis e atraentes em 1080p com desempenho medido.

### C2-06 — gravidade editável

Criar corpos e editar massa, raio, posição, velocidade e spin; prévia orbital,
baricentro e escape; 128 massivos com taxa efetiva/precisão visíveis. Copiar
sistemas reais, simular encontros/capturas/ejeções e comparar antes/depois.
Saída: órbitas e conservação, edição/pausa/checkpoint e uma viagem de edição
real; o Atlas não escreve por cima do estado integrado.

### C2-11 — campo e instrumentos

Sondas fixas/seguindo corpos, cortes móveis, vetores omnidirecionais,
equipotenciais, gradientes de maré, gráficos e comparação entre ramos.
Adicionar ressonâncias, J2 e marés de equilíbrio com parâmetros materiais.
Medir 256 massivos e até10 mil partículas sem gravidade mútua num perfil próprio.
Saída: mesmo avaliador fornece números/campo/força; leitura tem instante e
revisão confirmados, integrado à cena 3D navegável. Deformação material e
curvatura espaço-temporal são distintas.

### C2-12 — fontes EM e interação mútua

Incluir painel e camadas E/B com controles independentes, fonte/corpo
selecionável, linhas/cortes/sondas e persistência, conforme
[pedido de18/10](CAMADAS-QUATRO-FORCAS.md). Preparar a associação ao catálogo
em C2-13; não tratar falta de modelo como campo nulo.

Editor de cargas e fontes, E/B vetoriais, superposição, hélice, deriva E×B,
dipolo e pequeno sistema Coulomb autoconsistente. Raio de exclusão ou
regularização, regime de velocidade e influência de reação explícitos.
Saída: cinco experiências com força/trabalho/energia, fonte/atuação/camada
independentes e convergência. Cargas clássicas não ganham órbitas atômicas reais.

Avanço em18/10: candidata separada EM0.4, com editor transacional, intervenções,
checkpoint/migração explícita, posições nativas conferidas, mapas e linhas com
fontes/instantes próprios e retomada após reiniciar. O perfil128 passou em
native-em128-c212em04a-review.json:3×60s/30s,1080p,dt.001/rate1,
taxa mínima0.999384s/s,p95máximo23.254ms,p99máximo24.658ms,zero>100ms,
20pausas≤65.254ms, recursos dentro dos limites. Fonte/DLL/testes/recibos
congelados emc212-em-v04-candidate-20261018.tar.gz. A0.3 foi reprovada na taxa;
sua medição e fonte continuam preservadas. A instalação3.13 não foi alterada.
Em19/10, equipotenciais foram integradas em candidata própria à cena nativa,
canvas, sonda de fontes congeladas, exportação e preferências visuais schema2,
com núcleo científico0.4 intacto. CEF/SM/SI, quatro combinações de atuação/
visibilidade, reinício e perda de ACK passaram; zero errosJS e instalado preservado.
O perfil potencialA falhou p95=25.334ms>25; dados e fontes preservados.
Malhas0.2 unem somente pontas exatas de grau2, sem alterar arestas científicas;
544/868arestas passam a553/877vértices. PerfilB também reprovou: p95rota3=26.72623ms; nenhuma promoção.
Núcleo isolado EMcloudv2 passou campos/Boris escalar/10períodos/refinamento,
E analítico/trabalho e E×B.10mil/500passos dt.002 mediram1.1728s/s isolados,
contra0.6847v1; não é desempenho nativo nem desempenho com128fontes.
Worker10milEM e checkpoint próprio passaram processos reais com futuros exatos;
transporteC2CLD002 declara Borisv2/SI1/1 e runtime experimental separado. A prova
nativa funcional inicial passou1/128/10000, seleção SI e18recusas de pacotes;
CEF/retomada passaram em19/10; em20/10 o perfilEMcloudC passou3×60s em1080p,
10milq=m=1/Buniforme1T/dt.002/rate1/97vetores congelados. Auditoria independente:
p95máximo18.435ms,p99máximo20.654ms,taxamínima.944699s/s,20pausas≤121.132ms,
RAMsomada1.078GiB/WDDMsomado2.964GiB. Candidata isolada congelada em
c212-em-cloud-v02-candidate-20261020.tar.gz; A/B interrompidos preservados.
Diagnóstico isolado de10mil+128fontes estáticas carregadas/dipolares mediu
apenas.01146s/s no núcleoNumPyv2. Núcleo compilado separado em desenvolvimento;
nenhuma promoção. Em20/10, helperE próprio (MSVC/AVX2/OpenMP, geração selada)
passou referências escalares/analíticas,16futuros NumPy vsC++ emprocessos separados,
worker/checkpoint/GPU/CEF/reinício/ACKperdido. Perfil de10mil+128fontes estáticas
fracas q±1e-12C/momentosnãonulos emcasca8m passou3×60s/30s,dt.002/rate1,
1080p e97E+97B:taxamínima1.000023,p95máximo18.79838ms,20pausas≤113.407ms.
Auditor independente verificouenergiaestática total eDOP853 para3partículas/rota,
erro≤3.493e-5. Congelado emc212-em-cloud-native-candidate-20261020.tar.gz,
sem promoção. Caso intenso q±1e-10C REPROVADO na trajetória longa nos passos
ensaiados; permanece com fonte/dados, exige passo/convergência próprios.
Em 20/10, a regressão EM128 no motor novo reprovou p95 em
37,376/39,485/41,117 ms. Foi reproduzida acumulação de tópicos Lua concluídos
na conexão do motor, elevando o custo de cada publicação de propriedade.
Uma conexão extra com 5.000 respostas concluídas levou p95 a 47,540 ms;
fechá-la recuperou 35,278 ms. Correção em motor separado, sem mudar a física
ou o instalado: limpeza de concluídos no preSync seguinte. Testes nativos de
callbacks pendentes, IDs reutilizados e assinaturas passaram. O controle
corrigido ficou em p95 16,978–17,164 ms, mesmo com 5.000 respostas concluídas.
Formal EM128 c212mutfixa e auditor independente passaram: três rotas de
60 s/30 s/1080p, p95 máximo 17,081 ms, taxa mínima 0,998090 s/s e vinte
pausas ≤53,945 ms, com recursos e conservações dentro dos limites originais.
Reprovação anterior preservada; sem promoção do candidato parcial.
Os perfis corrigidos de 10 mil/128 fontes fracas e de potencial também
passaram, com p95 máximo 18,293 e 17,084 ms, respectivamente. Recibos e
interface/restart foram congelados em c212-topic-cleanup-candidate-20261020.tar.gz.
O regime intenso passou em quatro partículas com passos explicitamente
menores: 49,087/24,544/12,272 µs, erros 2,617e-4/6,544e-5/1,636e-5 e
ordem dois contra DOP853. Não aprova o passo antigo nem desempenho de 10 mil
nesse regime; rejeição anterior preservada.
Uma nova cópia F acrescenta controles de passo/ritmo ao laboratório pequeno,
mantendo o núcleo 0.4 byte a byte. Worker, CEF, retomada e relato de saves
parciais passaram; perfil 128 com histórico numérico no limite está em execução.
Em21/10, os perfis F128/potencial e duas rodadas da nuvem passaram; uma
rodada anterior da nuvem ficou reprovada por taxa0,8435 e foi preservada.
O diagnóstico não estabeleceu sua causa. F foi congelada sem promoção e o
instalado3.13 foi restaurado e conferido. Cópia G de integração separada
acrescenta editor da partícula de teste, instrumentos de força/potência/
energia/trabalho e painéis alternáveis com escala100–150%. Vinte casos dos
instrumentos passaram contra fórmulas escalares independentes. O percurso
CEF,16combosdasquatroforças e reinício com777passos exatos passaram em G;
seus perfis próprios estão em medição. Nuvem, alternância de vistas e revisão
visual das cinco experiências continuam em C2-12-INTEGRACAO.md.
Faltam integração, acabamento e aceite de experiência. Não é
aceite completo deC2-12, do catálogoC2-13 ou da malha relativística.

### C2-20 — estrela e escalas das quatro forças

Ampliar pp-II/III e rede adequada ao ciclo CNO no domínio escolhido, considerar
screening só com formulação fixada. Acrescentar zona com temperatura/composição
e reservatório evoluídos, equação de estado e perdas consistentes. A densidade
prescrita ou dinâmica e qualquer fonte de trabalho ficam explícitas. Comparar
com perfis/trilhas de evolução estelar de referência; transporte/hidrostática
completos não são inferidos da zona. Saída: balanços e resposta temporal ao
suprimir canais, sem confundir energia produzida com luminosidade superficial.

### C2-14 — relatividade de campo fraco

Entrega obrigatória acrescentada em18/10: malha espaço-temporal de referência
com botão próprio, corte espacial/observador/coordenadas definidos e leituras
conferidas com a métrica. Primeira fatia exterior esférica; ampliação em C2-15.
Critérios e distinção da malha para o campo3D em CAMADAS-QUATRO-FORCAS.md.

Precessão orbital, tempo próprio de observadores, desvio de frequência e lente
pontual com fonte/lente/observador editáveis. Comparar o mesmo estado inicial
em Newton e aproximação relativística, com mapa3D das grandezas e resíduos.
Saída: previsões quantitativas e domínio respeitado; não usar aproximação fraca
perto de um horizonte, nem folha elástica como representação principal.

### C2-04 — Atlas entre escalas

Hierarquia e carregamento progressivo; Sol, oito planetas,30 luas e50 corpos
menores; índice de100 mil estrelas selecionáveis e meta opcional de1milhão.
Via Láctea/Andrômeda e objetos profundos com tipo de representação. Índices,
catálogos e terreno não podem invalidar IDs ou tremular ao trocar de âncora.
Saída: percurso multiescala e retorno com referências/épocas preservadas.

### C2-05 — superfícies e geração

Lua/Marte com relevo identificado; quatro famílias rochosas (craterada,
vulcânica, desértica, gelo) e20 sementes de referência. Procedural também cria
sistemas com composição/órbitas/condições coerentes dentro dos modelos.
Saída: órbita→superfície contínua, bordas sem rachaduras, visita determinística
independente da ordem e famílias com geometria distinta. Não alegar simular
geologia/clima apenas pela geração; gigantes gasosos não têm chão fictício.

### C2-07 — colisões e energia

Contato contínuo, fusão de esferas, momento angular/spin, reservatório de calor,
resfriamento e equilíbrio radiativo simples. Três experiências: frontal,
oblíqua e térmica. Efeitos são derivados/identificados; brilho e fragmentos
visuais não criam massa nem substituem um solver. Saída: nenhum atravessamento
nos casos congelados e balanços compatíveis com a dissipação adotada.

### C2-08 — histórico e recuperação

Sessão guarda localização, câmera, tempo, modelos, sondas, dados/fontes,
checkpoint e eventos. Retornar a um instante disponível, ramificar, sobrepor
duas hipóteses e exportar JSON/CSV com unidades; informar mudanças de geração.
Saída: fechar/reabrir restaura estado compatível, interrupção conserva último
arquivo válido e liberar cache preserva sessões. Não retrointegrar dissipação.

### C2-09 — pacote e orçamento

Instalador/pacote sem Python/compilador do usuário; dados offline básicos,
gerente de pacotes/cache, recuperação e manifestos de terceiros. Metas já
propostas:6GiB instalação básica,10GiB cache,8GiB RAM e5,5GiB orçamentoVRAM,
reavaliadas por medição. Saída: instalação limpa, reabertura offline e roteiros
reais. Conteúdo de alta resolução fica em pacote com tamanho medido.

### C2-10 — intermediária

Consolidar J1–J5, guia de uso e exemplos demonstráveis, corrigir falhas impeditivas
da exploração/editor/saves. Não exigir retrabalho de módulos já aprovados e
não chamar esse corte de conclusão do pedido das quatro forças.

### C2-13 — ambiente planetário

Vincular campos E/B suportados aos corpos do catálogo e auditar capacidades
dos12 destaques e Sol. Separar campos intrínsecos/crostais/induzidos/externos,
origem e época; disponibilizar camadas e sondas no corpo selecionado.

Ligar trajetórias de partículas ao IGRF dentro de seu domínio, comparar dipolo,
campo interno e modelos externos/snapshots. Observação por posição/época,
espelhamento e três experiências integradas. Saída: transporte é calculado,
limites e origem externa aparecem; interpolação de simulação não é nova MHD.
Aurora física exige emissividade/colisões; camada ilustrativa é identificada.

### C2-15 — buracos negros

Schwarzschild e Kerr estacionários: luz/partículas, spin, observador,
arrasto de referenciais, sombra e disco de emissividade prescrita. Referência
CPU antes de imagem progressiva/GPU. Saída: imagem corresponde a raios
validados, captura/fuga/fronteira têm destinos corretos e ≥30FPS é medido no
perfil interativo com resolução interna declarada. Não alegar GRMHD do disco.

### C2-16 — observatório e conteúdo

Completar12 destaques (Terra/Lua/Marte/Vênus/Mercúrio/Júpiter/Saturno/Io/Europa/
Ganimedes/Titã/Encélado),30 sistemas exoplanetários e30 objetos profundos adicionais.
Diagrama estelar, trânsito/binária eclipsante, fluxo, corpo negro e curva de
luz; fases/eclipses e correções de observação com geometria/observador definidos.
As32 experiências são6 gravidade,5 EM,3 magnetismo,4 GR,3 colisão/energia,
3 observação e8 nucleares/estelares. Saída: uma investigação por destaque,
metadados sem lacunas inventadas e percursos completos por interface.

### C2-17 — fechar a v1 ampliada

Aceite adicional de18/10: malha e camadas das quatro forças de
CAMADAS-QUATRO-FORCAS.md integram a conclusão da v1. Controles semelhantes
usam representações adequadas às escalas gravitacional, EM e nuclear.

Integrar J1–J15, modelos/sondas/saves, perfis de recursos e pacote offline.
Revisão científica e visual, acessibilidade, cancelamento/orçamentos de solver,
falhas/recuperação e jornada de demonstração. Saída: nenhuma dependência
obrigatória incompleta, experiência coerente e limitações acessíveis no produto.
O corte mantém expansão posterior identificada, sem promessa de física unificada.

## 6. Expansão além da v1

Esta frente enriquece a matéria e as escalas cósmicas após uma versão integrada.
Não bloqueia a v1 nem fica disfarçada em seus custos. Cada prova começa pequena,
fixa regime/referência/limites antes da implementação e pode exigir reestimativa.

| Ordem / ID | Entrega e saída | Dependência | Horas / ciclos |
| --- | --- | --- | ---: |
| 21 / C2-21 — matéria quântica | Hidrogênio com níveis/densidade de probabilidade/espectro; barreira Coulomb e tunelamento; modelo efetivo reduzido de dois núcleons com ligação/espalhamento. Comparar soluções e dados avaliados nos canais/energias escolhidos; nenhuma trajetória eletrônica clássica ou alegação de QCD completa. Quatro experiências. | C2-17/18/12 | 100–180h /20–36 |
| 22 / C2-22 — neutrinos e fraca avançada | Espectros beta permitidos em casos fixados, partilha de energia e oscilação de três sabores no vácuo/densidade constante com parâmetros avaliados. Probabilidades/normalização/balanços e casos conhecidos; não equacionar oscilação com nova força de decaimento. Quatro experiências. | C2-17/19/20 | 50–90h /10–18 |
| 23 / C2-23 — plasma coletivo | PIC eletrostático1D limitado: oscilação de plasma, blindagem de Debye e instabilidade de dois feixes, com estudo de convergência; magnetosfera/vento em snapshots MHD identificados. Sem prometer PIC3D/MHD interativo completo. Quatro experiências. | C2-17/12/13 | 120–220h /24–44 |
| 24 / C2-24 — dinâmica galáctica | Órbitas em potenciais de disco/bojo/halo, curva de rotação e comparação de hipóteses de matéria escura. Campo/sondas3D e população de teste; massa do modelo não é detecção da natureza da matéria escura. Quatro experiências. | C2-17/04/11 | 70–130h /14–26 |
| 25 / C2-25 — cosmologia e universo observado | FLRW: expansão, redshift, idade/lookback e distâncias próprias/comóveis/angular/luminosidade; variar parâmetros dentro do domínio. MapaCMB e teia cósmica de produtos fixados e identificados. Curvas e distâncias independentes; não transformar variar Ω em recalcular um snapshot. Quatro experiências. | C2-17/04/14/16 | 90–160h /18–32 |
| 26 / C2-26 — integração científica ampliada | Mais24 experiências (20 acima+4 comparações entre módulos),56no total; novas sessões/pacotes, recursos/acessibilidade, percursos da matéria quântica ao universo observado. Fechar somente os modelos e acervos validados. | C2-21–25 | 60–100h /12–20 |

Supernovas, ondas gravitacionais e grandes simulações podem aparecer como
produtos calculados externamente com procedência. Solvers próprios de explosão,
fusão de buracos negros, impactos SPH3D, formação cosmológica e QCD de primeiros
princípios exigem outro recorte e não estão escondidos nessas horas.

As quatro comparações finais investigam limites clássico/quântico,
partículas de teste/plasma coletivo, produção estelar/propagação de neutrinos
e observação geométrica/aparente/cosmológica em seus respectivos regimes.
Comparar módulos não significa acoplar solvers sem contrato ou combinar todas
as escalas numa única cena física. A gerência global limita filas, memória,
amostras e custo; tarefas obsoletas podem ser canceladas e leituras antigas
são identificadas. Domínio/velocidade efetiva são visíveis sem bloquear câmera.

## 7. Decomposição histórica4.0 — ver orçamento atual emPLANO-UM-MES.md

Cada ciclo registra um resultado utilizável, o que foi verificado e o próximo
passo. Distribuição típica flexível de 5h: cerca de0,5h para escopo/caso de
referência;3h de implementação/conteúdo;1h de ciência/UI/imagem pertinente;
0,5h de integração/registro. Não é cota, obrigação de produzir documento ou
cronômetro de parada. Se um resultado precisa de vários ciclos, mantê-lo
coerente e informar o trecho que permanece em trabalho.

Sequência inicial proposta, metas sem garantia de horas exatas:

| Ciclos | Resultado esperado |
| --- | --- |
| 1 | Adquirir AME2020, preservar flags/incertezas/ausências e catálogo/IDs verificáveis |
| 2 | Mapa N×Z, seleção/sonda e curvaB/A×A úteis por interface |
| 3 | Comparar núcleos, exportar dados/fontes e verificar UI nativa/720px |
| 4–7 | Fechar lacunasC2-01: propriedades/pacotes e cópia Sol/Terra/Lua para experimento |
| 8–10 | Completar a primeira trancheC2-18: energiaQ e experiências nucleares manipuláveis |
| 11–15 | Expandir decaimentos/ramificações e instrumentos C2-19 |

Essa janela permite alternar uma fatiaC2-18 antes do fechamentoC2-01 porque
o contrato nuclear depende da parteC2-01 já implementada. O aceite completo
continua01→18→19. Os15 ciclos de 75h não prometem fechar os três marcos em todos
os casos; o envelope acumulado é75–130h,15–26 ciclos.

## 8. Como uma etapa fica concluída

1. O usuário altera uma condição e obtém consequência calculada e legível.
2. Fonte, modelo, domínio, unidade, época/referencial e incerteza são consultáveis.
3. Um caso independente/analítico e verificações de conservação/convergência
   pertinentes sustentam o cálculo. Tolerâncias se fixam antes do resultado;
   erro numérico não vira acurácia observacional.
4. Atuação, efeitos e visualização preservam a semântica das quatro forças.
5. Um percurso real da interface/renderer é revisado, com desempenho da classe
   de cena e recurso medidos onde a mudança exigir.
6. Persistência/exportação funcionam no estado compatível; limitações e trabalho
   restante ficam registrados. Usar o mínimo de testes que estabeleça o resultado.

Não repetir suites antigas ou benchmark longo por edição de texto/aparência.
Não abrir um novo pacote administrativo por ciclo. Reutilizar evidência válida;
ampliar checks só por mudança, falha ou dúvida concreta. Atualizar previsão,
progresso e LEIA-PRIMEIRO após avanços materiais. Telemetria≤8% manda salvar
passagem e continuar; só parar em esgotamento real, bloqueio, fim do escopo ou
pedido do dono. Nunca substituir allowance por tempo decorrido ou tokens.

## 9. Fontes primárias e implicações desta pesquisa

Consultadas nesta revisão em12/10/2026; versões/termos de candidatos serão
fixados na prova específica, sem atualizar bibliotecas já instaladas.

| Referência | Como orienta o roteiro |
| --- | --- |
| [SpaceEngine](https://spaceengine.org/) | Navegação entre escalas, superfícies e procedural; inspiração de experiência, não código/dados a copiar |
| [Universe Sandbox](https://universesandbox.com/) | Editar/criar sistemas e ver consequências; material/clima/impactos exigem modelos além de gravidade |
| [OpenSpace](https://docs.openspaceproject.com/latest/) e [globe browsing](https://www.openspaceproject.com/features/globe-browsing.html) | Base atual, acervo multiescala e terreno de missões; última documentação não substitui release0.22 fixada |
| [Celestia](https://github.com/CelestiaProject/Celestia) | Organização/extensibilidade/navegação; repositório oficial consultado quando site bloqueou acesso |
| [JPL/NAIF: aberração](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/req/abcorr.html) | Separar estado geométrico de observação com tempo de luz e aberração |
| [AME2020 original](https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt), [NUBASE2020](https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf), [ENDF/IAEA](https://www-nds.iaea.org/exfor/endf.htm) | Catálogo/ligação, propriedades de decaimento e dados de reações; preservar avaliação/incerteza/domínio |
| [NIST/espectros atômicos](https://physics.nist.gov/PhysRefData/ASD/levels_form.html) e [forças nucleares efetivas](https://arxiv.org/abs/1105.2919) | Referências para níveis atômicos e limites de modelos nucleares de baixa energia; comparar aproximação reduzida, sem prometer implementar toda EFT |
| [ESA/Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3) e [NASA/colunas exoplanetárias](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html) | Qualidade/ausências/incertezas por propriedade, identidade por release e curadoria de sistemas |
| [MESA](https://mesastar.org/) e [equação de estado](https://docs.mesastar.org/en/stable/eos/overview.html) | Evolução estelar exige rede, EOS, energia/transporte/estrutura; candidato a referência/perfis, não solver instalado em Cosmos2 |
| [CERN: Modelo Padrão](https://home.cern/science/physics/standard-model/) | Distinguir as três interações quânticas de gravidade e evitar alegação de teoria unificada |
| [PDG: neutrinos](https://pdg.lbl.gov/2022/reviews/rpp2022-rev-neutrino-mixing.pdf) | Formulação/parâmetros de oscilação; avaliação escolhida será fixada antes C2-22 |
| [Smilei/PIC](https://smileipic.github.io/Smilei/Understand/algorithms.html) e [módulos físicos](https://smileipic.github.io/Smilei/Understand/physics_modules.html) | Plasma coletivo exige campo/partículas autoconsistentes; colisão/ionização não surgem automaticamente do PIC |
| [galpy/potenciais](https://docs.galpy.org/en/v1.11.2/potential.html) | Órbitas e curvas de rotação em potenciais modelados; candidato a comparação independente |
| [Astropy/cosmologia](https://docs.astropy.org/en/stable/cosmology/index.html) | Referência candidata para cosmologiasFLRW e diferentes distâncias/tempos |

As novas entregas e horas são síntese/proposta de engenharia desta revisão.
As páginas acima não certificam compatibilidade no Windows, desempenho na RX7600
ou conclusão das funcionalidadesCosmos2. Esses resultados precisam das provas
locais da etapa correspondente.
