# IS-3 — nós removidos durante inicialização

Mapas0.7A encontraram um crash real ao limpar o corte joviano. Dados,
logs,trace,dump e hashes preservados em output/is3-native-maps-crash-20261024a.
O último bin0 iniciou CPU antes da remoção e não registrou conclusão;
depois da exclusão aparece inicializaçãoGL com identificador vazio. A
fonte guarda ponteiros crus nas filasCPU/GL e a remoçãoLua destruía o nó
sem coordenar essas filas. Isso identifica uma condição de uso após
liberação; a pilha no driver sozinha não prova todos os detalhes do crash.

M1 compilada e isolada em .runtime-node-lifecycle, sem teste/aceite nativo.
M2 em .runtime-node-lifecycle-v2 acrescenta drenagem da subárvore antes
de detach e encerramento por filhos antes de pais, usando a árvore real
para incluir nós ainda pendentes. Sete fontes são arquivadas com hashes;
as versões anteriores, instalado3.13 e sessão do dono foram preservados.
Nenhuma alteração nos modelosSI/coeficientes/solvers; nenhuma promoção.

cancelInitialization espera a CPU do nó e remove a referênciaGL pendente.
A trava inclui o último acesso ao LoadingScreen. Remoção simples e regex
passam por Scene.detachNode. deinitializeGL só executa se o estado chegou
a GLInitialized. O novo diagnóstico cosmos2SceneInitialization informa
somente trabalhoCPU: é necessário observar quadros posteriores para GL.

V2 compilou/linkou e o manifestoWindows teve a falha c101008d já observada
na máquina. finalize-engine-manifest.py incorporou normalmente ambos os
manifestos; o build completo repetido terminou0. Log direto preservado.
Staging exige hashes exatos das sete fontes e preservação dos runtimes
anteriores; receipt evidence/built-runtime-node-lifecycle-v2.json.
Compilação não representa aceite do motor ou dos mapas.

Verificações preparadas: remoção imediata folha/pai+filho/regex com CPU
pendente confirmada, seguida de quadros reais; replay dirigido corteJúpiter
com CPUociosa+quadrosGL antescaptura; shutdown normal solicitado com job
pesado pendente. Recibos nativos devem ser consultados; até passarem, estes
são testes preparados. Perfil próprio do motor+mapas continua obrigatório.

Oito capturas0.7A foram revistas no original100/150. PainelSI legível;
rótulos nativos do corteJúpiter se sobrepõem e corte parece pequeno. Não
houve garantiaCPUociosa nas capturasA. evidence/is3-body-maps-visual-review-
20261024a.json registra recusa de aceitevisual, sem alterar as imagens.

## Resultados nativos

node-lifecycle-v2-native-20261024a ACEITO: remoção imediata folha,pai/filho
por nome e por padrão; CPUpendente confirmada antes de todas, drenada após,
quadrosreais renderizados depois. Datasetbin0original10.206segmentos/nome,
tempos35,31/30,51/29,57s. Não são números de desempenho aceitável do produto.
node-lifecycle-v2-shutdown-20261024a ACEITO: shutdownnormal solicitado com
CPUfilhopesado pendente, engineexit0,servidor/launchercleanup,nenhumdumpnovo;
logs/hashes preservados. A fonte drena antes de destruir. O recibo não
alega CPU ainda pendente na entrada exata do destructor sem instrumentação.

Replay0.7V2A: Jupcutclear/loadoculto/CEF e célula passaram (1caso), duas
capturas apósCPUociosa+quadrosGL. Recibo geral INCOMPLETO: branch-load
posterior levou a timeoutCEF15s e WSapp5s durante restauração pesada;
app permaneceu vivo. Não é um novo crash observado nem aceitecompleto.
Batching0.7.1 mantém ciência e reduz objetos; contrato separado.
