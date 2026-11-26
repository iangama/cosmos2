# IS-3 — linhas internas de Terra e Júpiter

Candidata isolada output/is3-body-lines-product, geração0.5, armazenamento
próprio. Base dos vetores output/is3-body-vector-product preservada, assim
como IS3 anterior, instalado3.13 e sessões do dono. Sem promoção.

## Ciência e domínio

Contrato prévio IS-3-LINHAS-CONTRATO.md. Traçador próprio RK4 com duplicação
de passo para dx/ds=±B/|B|, nas mesmas sínteses fixadas IGRF14/JRM33.
Transformação e centro são os da leitura confirmada. Vértices e B em SI,
arcos, sementes, tolerâncias e motivos de término ficam no recibo da
geometria. Terra restringe alturaWGS84 de0 a1000km; Júpiter mantém1..20Rj.
Não extrapola B nos estágios externos e não fecha curvas truncadas.

PASSOU evidence/is3-lines-check-20261024a.json:30curvas modelo×época/grau×
posição×sentido contra DOP853 independente, refinamento, dipolo analítico,
campo uniforme, polos, covariância por rotação e inversão de sinal, nulo,
borda e17recusas. Maior erroODE por componente1,66109e−8R (limite2e−6R),
bound de refinamento1,70354e−8R. Invariante de dipolo≤1,352e−9 relativo;
linha uniforme≤6,218e−15R. Inversão geodética200pontos: altura≤9,314e−10m;
adaptador cartesianoIGRF45pontos≤1,695e−21T contra a consulta já adotada.
Precisão do integrador não é precisão observacional do campo.

Conjuntos padrão calculados na bancada:Terra5curvas/Júpiter4, com sementes
equatoriais e ponto selecionado; tempos locais0,295/0,609s. São tempos de
cálculo nessa execução, sem garantia de prazo para qualquer ponto/grau.
Alguns casos polares atingiram o limite de arco; essa interrupção está
registrada e não significa linha fechada ou ausência de campo.

## Jornada e imagem

PASSOU evidence/is3-native-body-lines-20261024a.json: seleção realCEF,
criação/substituição, cinco meshes confirmados no motor, máscara corporal,
recargaCEF, política atual de raios, amostra fixa na evolução, salvar/load
com limpeza da camada, Atlas e fontes preservados. Recusas de parâmetros,
fase, corpo e representação não mudaram fase ou camada aceita. Sol/Lua
informam modelo não adotado, distinguindo indisponível de B=0.

Linhas ciano e setas verdes derivam do mesmo B; tamanho das setas é gráfico.
Grade é elipsoideWGS84/esfera de referênciaJRM33. Painel mostra modelo,
época, domínio, número de curvas/vértices, congelamento e limites físicos.
Capturas100/150 revistas em resolução original: controle legível e curvas,
grade, ponto/setas e rótulo visíveis. Região central950×720RGBA idêntica
entre escalas; recibo is3-body-lines-controls-visual-review-20261024.json.
Não é aceite visual final de todo SistemaSolar, texturas ou magnetosfera.

## Perfil e próximas pendências

Perfil próprio20261024a iniciado; contrato IS-3-LINHAS-PERFIL-PREVIO.md,
runner benchmark-body-lines-native.py e auditor separado. Consultar
evidence/is3-lines-profile-20261024a.json antes de testes concorrentes.
Não herdar desempenho do vetor único nem declarar aceito antes da auditoria.

Persistência de seleção/configuração/visibilidade em checkpoints/ramos,
exportação, mapas/cortes, comparação sustentada ligado/desligado, múltiplas
camadas e partículas/Lorentz continuam pendentes. Ocultar atualmente remove
a camada e restaura a política dos corpos; ela é da sessão do renderizador.

## Auditoria do perfil B

B20261024b concluído e PASSOU auditor separado
evidence/is3-lines-profile-audit-20261024b.json. Terra4.499quadros,
Júpiter4.500; p95máx14,2618ms,p99máx14,6990ms,nenhum>100ms.
Ritmo normalizado mínimo1,000675;RAM1,02873GiB,WDDM2,95844GiB.
Todas as três vistas de cada modelo e66amostrasWDDM por janela passaram.
Hashes do reciboSI e meshes conferidos. Não cobre múltiplas camadas ou
amostragem contínua. A20261024a permanece incompleto: processo retornou143
sem recibo final/exceção; nenhum runner/coletor restou, motor ficou vivo.
Captura parcial recuperada em is3-lines-profile-20261024a-interruption.json;
causa do encerramento não estabelecida. B usou os mesmos fontes/limites e
foi iniciado por processoWindows separado; nenhuma correção do produto.
