# Cosmos2 — interações, instrumentos e conteúdo ampliado

Revisão 3.0, 12/10/2026. Especificação de produto solicitada pelo dono;
nenhum dos novos recursos abaixo deve ser apresentado como implementado.
Este documento complementa o plano diretor e define a entrega C2-11–20, complementada por QUATRO-FORCAS.md.
Sondas simples começam em C2-06; campos e relatividade entram antes de
concluir todo o catálogo. Quantidades são metas de aceite propostas nesta
revisão, sujeitas a avaliação técnica explícita, não inventário existente.

## 1. O que significa interagir fisicamente

Toda interação deve fechar o ciclo **alterar → calcular → observar → medir →
comparar → salvar**. Um vetor desenhado deve corresponder ao campo que o
modelo usa. Aumentar massa deve mudar forças e trajetórias; alterar carga
deve mudar a resposta eletromagnética. A imagem sozinha não valida o cálculo.

Cada cenário identifica três coisas separadas: procedência dos parâmetros,
equações adotadas e influência ativa. O usuário vê, por exemplo, “Campo
terrestre calculado — IGRF” e pode consultar época, unidade e cobertura.
Um campo prescrito atua nas partículas sem receber sua reação; a interface
informa essa hipótese. Dados ausentes não viram valores observados inventados.

As escalas têm modelos próprios. Não integrar simultaneamente todas as
estrelas catalogadas, partículas carregadas e raios de luz pelo mesmo solver.
Combinações precisam de contrato e validação; não basta somar efeitos visuais.

## 2. Instrumentos comuns

Complemento obrigatório de18/10: [CAMADAS-QUATRO-FORCAS.md](CAMADAS-QUATRO-FORCAS.md)
define malha relativística, camadas das quatro interações e campos associados
a corpos, com fontes, controles independentes e critérios de aceite próprios.

| Ferramenta | Ação e resultado visível | Introdução |
| --- | --- | --- |
| Sonda pontual | Fixar no espaço, seguir corpo ou lançar partícula de teste; medir grandezas no instante confirmado | C2-06; completa em C2-11 |
| Mapa de campo | Corte móvel, setas, linhas integrais e superfícies de igual valor; legenda com unidade e escala | C2-11/12 |
| Régua e comparação | Distância, velocidade relativa, aceleração, gradiente e comparação entre duas sondas | C2-11 |
| Gráficos ligados à cena | Tempo, energia, momento, órbita e leituras; clicar num ponto consulta o histórico disponível | C2-11/12 |
| Comparação de hipóteses | Duas ramificações com mesmos dados iniciais; eixos/unidades iguais e diferença quantitativa | C2-08/11 |
| Observador e relógios | Definir posição/movimento do observador, comparar tempo próprio e tempo de referência | C2-14 |
| Traçador de luz | Emitir feixe, acompanhar deflexão/captura e comparar trajetórias | C2-15 |
| Observatório | Curva de luz, espectro simplificado, diagrama luminosidade–temperatura e trânsito | C2-16 |

Sondas, cortes e gráficos são persistidos. Exportação inclui unidade,
referencial, amostragem, versão, parâmetros e fonte. Magnitude usa escala
linear/logarítmica selecionável; componentes com sinal usam escala própria.
Linhas de campo não são linhas de movimento. Densidade de linhas depende da
amostragem escolhida, não é uma medição automática da intensidade.

## 3. Gravidade e deformações por maré

Entregar em C2-06/11: inserir/remover corpos; editar posição, velocidade,
massa, raio e spin; lançar sondas; mostrar baricentro, órbitas e velocidade
de escape; prever trajetória com horizonte e erro identificados; comparar
sistemas binários, ressonâncias, encontros, capturas e ejeções.

Campo newtoniano e potencial vêm dos mesmos corpos ativos. Gradientes de
maré mostram aceleração diferencial em torno de uma sonda. Posições de
Lagrange usam o problema circular restrito de três corpos quando selecionado;
num sistema geral, indicar aproximação e referencial girante. Raio de Hill
e limite de Roche são estimativas com hipóteses, não detectores universais.

Adicionar achatamento J2 e marés de equilíbrio com parâmetros materiais,
spin e dissipação documentados. Comparar evolução orbital e aquecimento do
reservatório do modelo. Deformação geométrica ampliada é identificada; não
apresentar uma esfera esticada como cálculo de ruptura hidrodinâmica.

REBOUNDx é candidato para efeitos adicionais, condicionado à compatibilidade
com REBOUND fixado e a testes no Windows. Ele documenta efeitos gravitacionais,
marés e pressão de radiação; isso não comprova a integração Cosmos2.
[Efeitos REBOUNDx](https://reboundx.readthedocs.io/en/latest/effects.html).

Carga: manter 128 corpos massivos como perfil inicial; provar 256 em perfil
ampliado e 10 mil partículas de teste para anéis/discos. Estas últimas não
exercem gravidade mútua nesse perfil. Limites são medidos separadamente e a
taxa física efetiva continua visível. Aceleração/GPU só após identificar custo.

## 4. Campos elétricos, magnéticos e ambientes planetários

C2-12 entrega campos uniformes E/B, cargas pontuais fora de um raio de
exclusão, dipolo magnético ideal e superposição. O usuário altera intensidade,
direção, carga, massa, posição e velocidade; mede E em V/m, B em T e força
em N; observa órbitas helicoidais, aceleração elétrica e deriva E×B.
Campo singular exige exclusão ou regularização declarada e convergência.

Partículas de teste obedecem à força de Lorentz no regime adotado. Começar
com Boris não relativístico e comparação analítica. A documentação PlasmaPy
explicita esse regime e os argumentos SI. Definir limite de velocidade no
preset; regimes fora dele exigem integrador relativístico validado.
[Boris no PlasmaPy](https://docs.plasmapy.org/en/stable/api/plasmapy.simulation.particle_integrators.BorisIntegrator.html).

Além do modo prescrito, incluir um laboratório eletrostático pequeno com
interação de Coulomb entre até 128 cargas, calculada consistentemente a cada
passo e com balanço energético. Esse modo não resolve ondas eletromagnéticas
nem campos magnéticos gerados dinamicamente pelas partículas. Separar os
perfis e não chamá-lo de plasma completo. Alvo de partículas de teste: 10 mil,
sujeito a medição; não equivale a 10 mil cargas com interação mútua.

C2-13 integra o campo principal terrestre IGRF, com coeficientes fixados,
época, altitude e convenções de componentes. A NOAA fornece coeficientes,
implementações e calculadoras para referência independente.
[IGRF — NOAA/IAGA](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field).
Esse modelo não é o campo total durante tempestades. Não confundir o campo
interno terrestre com uma magnetosfera dinâmica completa.

Comparar Terra e um dipolo planetário ideal; visitar regiões de espelhamento
de partículas e produzir gráficos de trajetória. Para vento solar e forma
da magnetosfera, usar um modelo externo validado ou pacote de simulação com
parâmetros conhecidos. Controles só recalculam o que o modelo suporta;
interpolar snapshots não cria nova simulação MHD. Aurora pode ter camada
ilustrativa identificada; emissividade física exige modelo próprio.

## 5. Relatividade e distorções gravitacionais

“Distorção gravitacional” abrange marés, desvio da luz, diferença no ritmo
de relógios e efeitos da geometria do espaço-tempo. Cada um terá sua medição.

| Entrega | Interação | Modelo e limite |
| --- | --- | --- |
| Precessão orbital | Comparar mesmos dados com Newton e correção relativística | C2-14: aproximação pós-newtoniana de campo fraco, domínio quantificado |
| Relógios e desvio de frequência | Posicionar observadores, comparar tempo próprio e frequência | C2-14: velocidades e potenciais definidos; cenário estático Schwarzschild separado |
| Lente gravitacional | Mover fonte/lente/observador e medir separação, deflexão e amplificação | C2-14: lente pontual no regime fraco; hipóteses de distâncias declaradas |
| Buraco negro sem rotação | Lançar luz e partículas de teste, alterar massa e câmera | C2-15: geodésicas em Schwarzschild, horizonte e órbitas de referência |
| Buraco negro em rotação | Alterar spin e inclinação; comparar sombra e arrasto de referenciais | C2-15: Kerr estacionário; domínio de spin e observadores permitido |
| Disco e aparência | Examinar imagem deformada e desvio de frequência | C2-15: emissividade prescrita identificada, sem alegar GRMHD do disco |

Não aplicar correções de campo fraco arbitrariamente perto do horizonte.
Desenhos de “malha deformada” são auxiliares didáticos: não equivalem a uma
superfície material do espaço. Definir observador e coordenadas para evitar
interpretar singularidade de coordenada como barreira física medida.

Usar integração CPU de referência para validar raios; avaliar renderização
progressiva/GPU apenas depois. EinsteinPy é candidato para comparação e
protótipos de geodésicas em métricas fixas, não motor de imagem em tempo real
já aprovado. [Artigo dos autores](https://arxiv.org/abs/2005.11288).
Fusão de buracos negros com métrica evoluindo, ondas gravitacionais calculadas
por relatividade numérica e acoplamento completo à matéria ficam fora da v1.

## 6. Mais conteúdo com qualidade verificável

| Conjunto | Meta da v1 ampliada | Qualidade exigida |
| --- | --- | --- |
| Sistema Solar | Sol, 8 planetas, 30 luas e 50 corpos menores selecionados | IDs/fontes, orientação, dimensões, movimento e cobertura; detalhes visuais compatíveis com dados |
| Mundos em destaque | 12: Terra, Lua, Marte, Vênus, Mercúrio, Júpiter, Saturno, Io, Europa, Ganimedes, Titã e Encélado | Ficha individual de luz/material/escala; pelo menos um fenômeno ou investigação disponível |
| Superfícies | Relevo de Lua e Marte; 4 famílias procedurais rochosas com 20 sementes de referência | Continuidade, variedade e origem; planetas gasosos não ganham chão sólido fictício |
| Estrelas | 100 mil registros no recorte básico; meta de 1 milhão com pacote progressivo medido | Seleção e busca; incertezas/distâncias verificadas; sem velocidade ou planetas inventados |
| Sistemas exoplanetários | 30 sistemas curados | Dados versionados, lacunas preservadas, visual hipotético rotulado; presets físicos quando estado suficiente |
| Céu profundo | Via Láctea, Andrômeda e 30 objetos adicionais entre nebulosas, galáxias e aglomerados | Tipo da representação e distância/estrutura conhecida; imagem não vira volume observado |
| Estrelas e objetos compactos | Exemplos de sequência principal, gigantes, anãs brancas, estrelas de nêutrons/pulsares e buracos negros | Modelos de luminosidade/rotação/fontes; superfícies e feixes não inferidos como fotografias |
| Experimentos prontos | 32 cenários reproduzíveis distribuídos abaixo | Alteração significativa, medição, comparação e salvamento por interface |

As 12 cenas de destaque são subconjunto do Solar, não objetos adicionais.
Os números não significam texturas observadas completas ou 3D real de todos.
Curadoria pode substituir um candidato inadequado por outro equivalente,
com justificativa; não aprovar a meta só por contar IDs vazios.
As quatro famílias procedurais iniciais são craterada, vulcânica, desértica
e rochosa coberta de gelo; isso classifica relevo/material, sem alegar clima
ou evolução geológica simulados. Cada família deve diferir em formas e
parâmetros, não apenas na cor.

Os primeiros 24 cenários: 6 de gravidade (órbita, binária, Lagrange, ressonância, encontro,
maré); 5 EM (E uniforme, hélice, E×B, dipolo, Coulomb); 3 magnetismo planetário
(mapa terrestre, comparação com dipolo, espelhamento); 4 relatividade
(precessão, relógios, lente, Schwarzschild/Kerr comparados); 3 colisão/energia
(frontal, oblíqua, equilíbrio radiativo); 3 observação estelar (diagrama de
estrelas, binária eclipsante, trânsito exoplanetário).

C2-16 adiciona espectro de corpo negro didático, fluxo e curva de luz com
geometria explícita. Um espectro calculado não é espectroscopia observada.
Fontes exoplanetárias já previstas continuam candidatas; fixar consulta,
tabelas e referências antes de importar. [Consultas do NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/docs/API_queries.html).

## 7. Desempenho, integração e fronteira do escopo

As metas de 1080p/RAM/VRAM do plano continuam para o perfil padrão. Conteúdo
extra usa pacotes e níveis de detalhe; o alvo básico de 6 GiB não inclui
automaticamente todo conteúdo de alta resolução. Publicar tamanhos reais
por pacote. Não baixar catálogos enormes como consequência desta revisão.

Campos: começar por cortes 128×128, linhas limitadas por orçamento e quatro
sondas ativas. Valores medidos usam solver/precisão declarados, mesmo se a
imagem tiver menos amostras. Amostragem de campo pode ser 5–10 Hz enquanto
a câmera mantém sua cadência; exibir idade da leitura e nunca reutilizar
campo de outra revisão como resultado atual.

Raios relativísticos: alvo de navegação ≥30 FPS em perfil interativo a medir,
com resolução interna declarada, e captura científica progressiva separada.
Se necessário reduzir amostras da imagem, manter a referência numérica.
As metas são propostas; uma imagem acumulada lentamente não comprova FPS.

Antes de cada módulo novo, congelar caso pequeno, entrada, referência,
tolerâncias e orçamento; provar cálculo e controle de pausa; então integrar
à interface e medir. Falha exige ajuste explícito do modelo/escopo, sem
substituir o fenômeno solicitado por uma animação e chamá-lo de concluído.

Forte/fraca, redes nucleares e os controles independentes das quatro forças
passam à prioridade inicial, conforme QUATRO-FORCAS.md. Acrescentar oito casos
nucleares/estelares: D+T, ligação nuclear, captura radiativa, decaimento beta,
captura eletrônica, cadeia pp, ciclo CNO e resposta energética de uma região
estelar. As 32 experiências não equivalem a 32 equações fundamentais distintas.
Hidrodinâmica completa de impactos, QCD de primeiros princípios, PIC/MHD
completo e cosmologia dinâmica permanecem expansões específicas.

## 8. Entrega e aceite

A execução segue as dependências do plano diretor, priorizando a fatia das quatro forças em C2-01/11/12/18/19.
C2-10 torna-se entrega intermediária; C2-17 encerra a candidata v1 ampliada.
Cada marco novo exige percurso funcional, referência física independente,
qualidade de imagem e persistência. Critérios numéricos ficam na seção 9 de
VALIDACAO.md. A revisão não aprova G0 nem resolve a compilação pendente.

Fontes externas desta revisão foram consultadas em 12/10/2026. Bibliotecas
citadas são candidatas; versões, licenças e compatibilidade serão fixadas na
prova correspondente, sem atualizar o ambiente atual só para seguir “latest”.
