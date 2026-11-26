# IS-3 — vetor magnético de uma amostra na cena nativa

Preparação da próxima fatia visual, com ligação ao produto condicionada à
resolução dos perfisJ pendentes deC2-12. As consultasIGRF/JRM33 já possuem
evidência numérica, de orientação, worker e interface. Essa evidência não
aprova geometria ou desempenho com novas camadas.

## Conteúdo e escala

Mostrar uma única amostra confirmada, sua posição e direçãoB. O comprimento
da seta é gráfico, fixo em0,3vezes o raio de referência; não representa
intensidade ou força. Módulo e componentes continuam no painel emSI.
A geometria será derivada no servidor da leitura validada, sem aceitar
vetoresB fornecidos pelo navegador. Mostrar/ocultar não muda a solução.

Terra: grade no elipsoideWGS84 adotado pela consulta, com semieixo maior
6.378.137m e achatamento1/298,257223563. Não é relevo nem transformação de
uma estação medida. Júpiter: esfera de referênciaRj=71.492.000m, sem
representar superfície sólida ou achatamento. Eixos e grade usam o mesmo
frame corporalITRF93/SistemaIII e época da leitura, não o giro cosmético.

Cor verde identifica vetorB; ponto amarelo marca a posição. Grade de
referência em tom discreto, sem mapa de intensidade inferido da cor.
Ausência deB é indisponibilidade ou norma nula com direção indefinida,
identificada; nunca substituir falha por vetorzero. Não traçar linhas de
campo a partir de uma única seta. Correntes externas eLorentz continuam
fora desta fatia.

## Identidade e tempo

Cada camada guarda sistema,corpo,token,revisão,tempo,época,modelo,grau e
hash da leituraSI. O pedido exige o mesmo guard da consulta e cena pausada.
O servidor calcula a leitura na fase atual confirmada e confirma os nós
no motor. Não usar a orientação/posição de outro instante ou da referência
JPL para reposicionar o centro evoluído.

A camada é uma amostraFIXA no frame inercial. Evoluir não a arrasta para
outro centro/época. UI marca a fase obsoleta e permite ocultar/refazer.
Carregar/restaurar/importar ou trocar de sistema limpa a camada. Uma mudança
nos campos do formulário identifica que a camada é da amostra anterior.
Parâmetros e derivadas não são persistidos no checkpoint nesta fatia.

Ao ver a camada em escala física, ocultar somente o marcador ampliado do
corpo amostrado, mantendo essa política enquanto a camada estiver ativa.
Ocultar/limpar restaura a política normal de marcadores/raios definidos.
Não reescrever atributos físicos do corpo para conseguir desenhá-la.

## Transporte e geometria gráfica

Gerar vértices em coordenadas locais do modelo, normalizadas pelo raio de
referência, com translaçãofloat64 do centro atual. A transformação corporal
paraGALACTIC é a composição das matrizes já calculadas na própria leitura.
Aplicar rotação somente a posições relativas e vetores. Não somar centroB.

O recibo preserva ponto/vetorSIfloat64 e registra quantização dos vértices
float32 e limite conservador de erro gráfico. Comparar posição do frame
no motor em≤1mm; isso não promete vértices gráficos com precisão milimétrica.
Limite gráfico prévio: erro por componente de vértice≤1e−6×raio adotado.
Seta e orientação têm teste separado, com erro relativo de comprimento e
direção≤1e−12 antes da conversão gráfica.

## Critérios prévios

Arquivar fontes/contrato e leituras usadas. Testar comprimento/direção por
vetores analíticos, sinal, rotações, norma nula e entradas não finitas.
Usar leituras reaisIGRF eJRM33 já validadas para conferir ponto, centro,
matriz de transformação e identidade temporal; arquivos de malha precisam
conter somente as arestas declaradas e hashes no recibo.

Worker/API recusa guard obsoleto, corpo/modelo incompatível e pedidos extras
sem alterar órbitas. Falha ao montar a cena precisa remover nós parciais e
preservar o estado anterior, sem alegar confirmação do motor. Câmera deve
enquadrar a grade/ponto/seta no lado visível, semUp paralelo à direção.

Jornada nativa própria paraTerra eJúpiter: confirmar frame/visibilidade e
camadas, capturar depois de quadros renderizados em100/150%, mostrar/ocultar,
evoluir/amostrafixa e limpar ao restaurar/voltarAtlas. Conferir o estado
físico antes/depois. Perfil de desempenho desta geometria segue separado;
o desempenhoJ ouIS12 não é herdado pela camada planetária.

## Precisão da confirmação mundial — correção do harness A

O laboratório usa uma translação de exibição de1e14m emLabRoot, separando
esta cena doAtlas. Nessa magnitude, umULPfloat64 é0,015625m. A tentativa
nativaA exigiu1mm também para a subtração de duas posições mundiais e foi
recusada. Esse teste era mais estrito que a resolução dessas coordenadas.

Manter1mm para a translação LOCAL do frame e para a posição local do ponto,
que são as grandezas previstas acima. Para a diferença de posições mundiais,
adotar antes da tentativaB, por componente, o limite numérico conservador
ULP(posição mundial do ponto)+ULP(posição mundial do frame)+1mm. Guardar os
valores brutos e o limite efetivo. Isso cobre soma/subtração na confirmação
mundial; não amplia a precisão científica ou o limite dos vértices gráficos.
A tentativaA permanece incompleta; a geometria/modelo científico não mudou.

## Continuidade da interface na candidata de integração

A camada pertence à sessão atual do renderizador. Recarregar CEF recupera
seu identificador, leitura e estado pela API, evitando uma camada órfã.
Os formulários voltam aos valores locais padrão e a interface identifica
quando diferem da amostra ativa. Salvar não persiste a camada; restaurar,
trocar sistema/topologia ou voltar ao Atlas remove seus nós. Essa política
não modifica os checkpoints científicos nem exige outro ano de modelo.

Mostrar e ocultar são controles independentes da atuação física. Apenas
o marcador ampliado do corpo amostrado é ocultado; ao limpar a camada,
vale a política de exibição atual (marcadores ou raios SI definidos).
