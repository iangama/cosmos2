# Experiência e direção visual — Cosmos2

Especificação alvo, revista em 12/10/2026 para o plano 3.0. Já existe interface
de protótipo; os recursos abaixo só contam como entregues quando validados.
O critério central é o percurso que a pessoa consegue realizar e sua qualidade.

## 1. Primeira abertura

Abrir numa vista da Terra iluminada, com Lua visível quando a composição
permitir, escala compreensível e poucos controles. A tela oferece **Explorar**,
**Criar experimento** e **Continuar sessão**. O usuário entra diretamente
numa cena; não precisa escolher solver, dataset ou formato de arquivo.

Uma orientação curta apresenta selecionar, aproximar e voltar. Pode ser
dispensada e reaberta. Controles avançados e detalhes científicos ficam nos
painéis correspondentes, não ocupam a primeira vista inteira.

## 2. Organização da janela

| Área | Conteúdo e comportamento |
| --- | --- |
| Centro | Cena 3D como área principal, com seleção discreta e rótulos filtrados |
| Barra superior | Busca global, Atlas/Experimento, voltar e favoritos |
| Painel de objeto | Nome, classe, distância, propriedades essenciais; ações Visitar, Seguir, Comparar e Experimentar |
| Barra inferior | Data ou tempo do experimento, pausa, taxa solicitada/efetiva e histórico quando houver |
| Painel de ferramentas | Inserir corpo, massa, velocidade, raio e parâmetros do cenário |
| Painel de camadas | Órbitas, nomes, terrenos, catálogos e conteúdo procedural |
| Instrumentos | Sondas, cortes de campo, gráficos, relógios e observação de luz; disponíveis conforme o cenário |
| Detalhes expansíveis | Origem das propriedades, incertezas, modelo e diagnósticos |

Em 1080p com os painéis usuais abertos, preservar ao menos 65% da largura da
janela para a vista. Em telas pequenas ou zoom alto, usar um painel por vez,
sem sobrepor controles críticos. Texto base de pelo menos 16 px lógicos,
com escala 100–150%; atalhos não são a única forma de executar uma ação.

## 3. Linguagem visual

Fundo espacial escuro, tipografia legível e cores de acento usadas com
parcimônia. O corpo selecionado recebe contorno/indicador que respeita sua
projeção. Rótulos têm prioridade por seleção, proximidade e contexto; evitar
uma tela preenchida por milhares de nomes.

Os objetos precisam de volume e iluminação: terminador, relevo onde há fonte
ou geração, atmosfera com espessura coerente na imagem, sombras de anéis e
variação de materiais. Brilho e bloom não devem esconder detalhe. Exposição
automática é suave e pode ser travada; estrelas visíveis dependem do modo de
exposição. Um modo didático pode amplificar sua visibilidade com identificação.

Cada corpo tem limites de resolução. Ao aproximar além do conteúdo disponível,
informar o limite e manter uma vista consistente. Não esticar uma textura de
baixa resolução até apresentá-la como terreno detalhado. Nas superfícies
procedurais, o detalhe pode aumentar mantendo continuidade e seed.

Referências oficiais para comparação de linguagem visual:
[SpaceEngine](https://spaceengine.org/),
[OpenSpace — superfícies](https://www.openspaceproject.com/features/globe-browsing.html).
Essas referências orientam composição e funcionalidades; não fornecem assets
licenciados automaticamente para o Cosmos2.

## 4. Navegação

Três controles coerentes: **orbitar** um alvo, **voar livremente** e
**seguir** um corpo. Busca e botão Visitar sempre oferecem alternativa ao voo.
Velocidade varia suavemente com a escala e aparece em unidade adequada.

Proposta inicial: arrastar com botão direito orbita/olha, roda aproxima ou
ajusta velocidade conforme modo; WASD e Q/E movem no voo livre; G visita;
F segue; Espaço pausa; Esc cancela viagem ou fecha o painel ativo. O foco de
texto tem prioridade: digitar numa busca não pode mover a câmera.

Viagem automática usa trajetória suave e pode ser interrompida imediatamente.
Evitar cruzar o interior de um corpo sem intenção do usuário. Próximo ao solo,
modo de navegação por superfície evita atravessamento; isso é restrição da
câmera, não força aplicada ao sistema físico.

Distância real permanece acessível. Um mapa com ícones ampliados é identificado
como representação; voltar à cena física não carrega a ampliação dos ícones.
Não comprimir silenciosamente distâncias para fazer todos os planetas caberem.

## 5. Percursos de aceite

### J1 — viagem entre escalas

Terra → Lua → Saturno → estrelas próximas → Via Láctea → Andrômeda → favorito
Terra. Executar por busca e visita, e repetir trechos em voo livre. Cada etapa
deve conservar orientação utilizável, seleção, escala e feedback de dados
carregando. O retorno não pode apresentar tremor ou outro objeto no mesmo ID.

### J2 — explorar uma superfície

Selecionar a Lua, aproximar do relevo e observar o horizonte sob luz rasante.
Depois visitar um planeta rochoso procedural, percorrer terreno e voltar à
órbita. A Lua identifica a fonte e resolução; o planeta identifica a geração.
Nenhuma troca de nível de detalhe deve abrir fendas ou expor geometria faltante.

### J3 — alterar o Sistema Solar

Selecionar o Sol, escolher Experimentar, conferir o conjunto de corpos e
alterar a massa. A primeira alteração significativa pausa e mostra o novo
cenário. Executar, observar órbitas, comparar com a referência e restaurar por
checkpoint/ramificação. A ação não exige saber o nome do integrador.

### J4 — construir e colidir

Criar sistema vazio ou usar preset, inserir estrela/planeta, informar massa,
raio e velocidade com unidades, observar prévia e executar colisão. A interface
mostra qual modelo foi aplicado e oferece gráfico simples de massa/energia.
Partículas luminosas de efeito não entram na contagem de corpos massivos.

### J5 — salvar e continuar

Salvar experimento e localização, sair, reabrir e continuar no mesmo estado.
Mover uma cópia da sessão para outra pasta com os mesmos pacotes disponíveis.
Se faltar um pacote ou checkpoint, informar exatamente o que falta e manter
a sessão preservada. Exportar uma imagem e CSV com dados identificáveis.

### J6 — medir e alterar a gravidade

Abrir Terra–Lua ou binária, colocar duas sondas e um corte de campo. Ler
aceleração, potencial e gradiente, editar a massa numa cópia e comparar os
resultados. Seguir uma sonda e exportar leituras. Alternar setas, linhas e
superfícies sem alterar a simulação. Explorar um caso de Lagrange e marés
com o modelo e amplificação visual identificados.

### J7 — experimentar eletricidade e magnetismo

Abrir laboratório, escolher elétron/próton ou partícula definida, lançar num
campo uniforme e observar trajetória. Alterar B, E, carga e direção; medir
raio, força e energia, comparar com o caso inicial. Em outro preset, mover
duas cargas com interação eletrostática e observar sua resposta. O modo
prescrito e o modo de interação mútua ficam visíveis na escolha do cenário.

### J8 — explorar o campo planetário

Visitar a Terra, ativar o campo principal, escolher época válida e medir em
superfície/altitude. Comparar o modelo terrestre com um dipolo ideal e seguir
uma partícula de teste. A interface distingue intensidade de campo, densidade
de linhas desenhadas e trilha da partícula. Vento solar e aurora explicam
qual camada é calculada, importada ou ilustrativa.

### J9 — comparar gravidade clássica e relatividade

Abrir cenário de precessão, duplicar estado inicial e comparar Newton/campo
fraco no mesmo intervalo. Consultar avanço orbital; posicionar relógios no
cenário apropriado e observar diferença acumulada. Mover fonte/lente/observador
no laboratório de lente pontual e medir desvio. Controles apresentam limites
físicos do preset sem exigir escolher um algoritmo numérico.

### J10 — acompanhar luz perto de um buraco negro

Abrir Schwarzschild, emitir feixe e identificar raios desviados/capturados.
Variar massa e câmera; comparar com Kerr variando spin e inclinação. Mostrar
horizonte, região de fótons e referência orbital quando aplicáveis, distintos
da sombra observada. Imagem e feixes respondem aos mesmos parâmetros.
Salvar observador e preset para repetir a comparação.

### J11 — observar estrelas e exoplanetas

Buscar um sistema curado, consultar dados e aparência calculada. Comparar
luminosidade/temperatura, simular um trânsito e medir a curva de luz. Variar
raio/inclinação numa cópia e sobrepor as curvas. Um espectro de corpo negro
vem rotulado como modelo; dados observacionais mantêm suas fontes/erros.

### J12 — observar processos da interação forte

Escolher reação/cenário de ligação, alterar condições, medir taxa e produtos,
comparar energia disponível e referências. Suprimir processo mantendo sua
visualização e identificar o experimento hipotético. Não desenhar quarks
clássicos orbitando como evidência de QCD resolvida.

### J13 — observar processos da interação fraca

Escolher decaimento/captura, medir população/meia-vida e produtos. Alterar
atuação preservando curva de referência; consultar neutrinos onde modelados.

### J14 — controlar as quatro interações

Em cada palco, testar as quatro combinações Atuação/Referência. Ocultar mantém
resultado. Desligar mantém fontes e referência, alterando somente operadores
suportados. Salvar, reabrir e exportar condições/resultado. Outros efeitos
só aparecem como operáveis quando o cenário possui modelo implementado.

### J15 — relacionar processos numa estrela

Investigar rede pp/CNO e balanço térmico no modelo declarado. Comparar efeitos
nucleares, gravidade e transporte; distinguir energia produzida no núcleo de
luminosidade da superfície. Não apagar a estrela instantaneamente ao suprimir
uma reação. Consultar tempos e limites do modelo.

## 6. Cenas de referência visual

| Cena | O que avaliar |
| --- | --- |
| Terra no terminador | Atmosfera, oceano, nuvens, iluminação e exposição equilibradas |
| Lua em luz rasante | Relevo, textura, sombras e horizonte sem degraus de detalhe |
| Saturno | Transparência e sombras dos anéis, escalas e legibilidade da seleção |
| Sistema binário gerado | Fontes de luz identificáveis, órbitas e procedência |
| Via Láctea vista de fora | Volume/distribuição legíveis e estrelas sem excesso de cintilação |
| Planeta procedural próximo ao solo | Continuidade, variedade de relevo e fluidez ao retornar à órbita |

As seis cenas iniciais continuam. A ampliação acrescenta as 12 fichas de
mundos e cenas de instrumentos, campos e relatividade definidas em
ESCOPO-CIENTIFICO.md e VALIDACAO.md. Não exigir todos os fenômenos em todo
objeto; cada ficha especifica o que seu conteúdo realmente suporta.

Guardar câmera, época, iluminação e preset das cenas para comparar versões.
Imagens precisam ser do programa executado; arte conceitual, se criada depois,
será identificada e não contará como entrega do renderer.

## 7. Compreensão e acessibilidade

Seleção por cor também usa texto/ícone. Contraste de texto normal com alvo
de 4,5:1; foco visível; navegação dos painéis por teclado. Permitir reduzir
movimento de câmera, brilho intenso, trilhas e efeitos. Preservar pausa como
ação acessível durante processos demorados.

Rótulos essenciais: **Dados de catálogo**, **Modelo calculado**, **Gerado**,
**Hipótese do experimento** e **Sem informação**, usados quando ajudam a
interpretar uma propriedade. Exibir detalhes de fonte sob demanda. Evitar
siglas de infraestrutura e caminhos internos no fluxo principal.

## 8. Como julgar se ficou bom

Em C2-03, comparar as três cenas iniciais por luz, materiais, câmera, clareza
e continuidade. Se uma dessas áreas estiver fraca, corrigi-la antes de aumentar
o número de objetos. Em C2-10, demonstrar J1–J5; em C2-17, demonstrar J1–J15
e os destaques científicos com a build real. Registrar separadamente aceite técnico e opinião do dono;
funcionalidade implementada não presume satisfação com a experiência.

Para tornar a revisão reproduzível, cada cena de referência tem uma ficha
com câmera, época, resolução, preset, origem dos mapas e seis verificações:

| Aspecto | Condição observável de aceite |
| --- | --- |
| Luz | Fonte e lado iluminado coerentes; detalhe não desaparece por exposição ou bloom excessivos |
| Material/relevo | Recursos previstos para o corpo aparecem sem textura ausente, esticamento impeditivo ou fenda |
| Câmera | Orbitar, aproximar e voltar mantêm controle; a viagem automática pode ser interrompida |
| Escala | Distância/unidade acessíveis e amplificações didáticas identificadas |
| Leitura | Seleção e texto permanecem legíveis nos tamanhos de interface testados |
| Origem | É possível distinguir a fonte observada, o modelo e os detalhes procedurais daquele objeto |

G1 exige as três cenas iniciais sem falha impeditiva nesses aspectos.
O conjunto completo de seis cenas entra nos marcos em que seu conteúdo existe.
Problemas pequenos podem ser registrados; um corpo sem o material ou relevo
exigido, uma câmera que perde o alvo ou uma fonte de dados apresentada como
outra não contam como cena aprovada. Mais objetos no catálogo não compensam
uma dessas falhas.
