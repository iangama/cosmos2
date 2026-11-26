# IS-4 — primeiras cargas-teste nos campos corporais

Contrato de construção, ainda sem aceite numérico/nativo. Parte do plano
PLANO-INTEGRACAO-SISTEMA-SOLAR.md, fatiaIS4. Começar em staging próprio
após o perfil dos mapas0.7.1, preservando bases/instalado/owner. Não afirmar
que esta primeira bancada conclui o ambiente solar ou integra todas as forças.

## Primeiro regime

Uma partícula-teste de massa positiva e carga±/zero, sem reação nos quatro
centros neutros e sem interação entre partículas. EquaçãoSI:

    dx/dt = v
    dv/dt = g(x) + (q/m)[E(x) + v × B(x)]

Posição/velocidade no mesmo instante inteiro. Controles físicos de gravidade,
E eB são independentes da sua visualização. Velocidade≤0,01c; sem radiação,
colisões, plasma, indução ou MHD nesta bancada. A ausência de campo adotado
permanece indisponível. E=0 é uma escolha explícita do cenário inicial,
não uma inferência observacional sobre Terra/Júpiter ou vento solar.

Primeira fatia: snapshot prescrito e estático da cópia solar pausada. B usa
IGRF14 ouJRM33 aceitos na época congelada, com o mesmo grau/orientação e
geometria de IS3. Os eixos são cartesianos com orientação corporal fixada
na época e tratados como eixos inerciais da bancada estática. Não são um
referencial que gira durante a trajetória: nenhum termo centrífugo/Coriolis
ou campo elétrico de corotação é implicitamente acrescentado.

A origem é fixa no centro do corpo na época do snapshot. Posições dos
quatro centros e seusGMs são prescritos/fixos nesse cenário; g é a soma
newtoniana nesses centros, convertidos para os mesmos eixosSI. Não
subtrair aceleração da origem e chamar isso inercial, nem atualizar centros
por efemérides durante o teste. Modelo estático tem potencial definido:
Phi_g = −soma GM_i / |x−x_i|. O cenário deve declarar que não representa a
órbita evoluída nem uma magnetosfera real. Partícula possui relógio próprio
em segundos; evoluí-la não avança silenciosamente o relógio orbital.

Integração a centros móveis, orientação/época variáveis, ambiente externo e
vento solar exigem etapas posteriores com contratos próprios de quadro,
E/B consistente, potência/trabalho de fontes e ligação ao relógio comum.
Não extrapolar IGRF/JRM para preencher esses requisitos.

## Domínios e passo

IGRF: altura geodéticaWGS84 de0 a1000km. JRM: raio1 a20Rj e graus1/13/18
adotados. Conferir início, meio e fim, e os DOIS segmentos de drift de cada
passo: endpoints válidos não permitem atravessar o corpo. Para Júpiter,
mínimo da distância ao centro no segmento. Para Terra, mínimo da forma
quadrática do elipsoide interno; a altura externa é a distância normal ao
elipsoide convexo e seu máximo em um segmento não excede os endpoints.
Conferir exclusões de todas as fontes gravitacionais. Nenhuma chamada ao
provedor fora do domínio, nem projeção/clamp de uma trajetória inválida.

Reutilizar por mérito o esquema sincronizado drift/Boris/drift validado em
C2-12, adaptando a aceleração não magnética a g+(q/m)E. Amostrar campos no
meio do drift; duas meias-kicks e rotaçãoB, depois segundo drift. Ângulo
giro≤0,1rad/passo. Tentativa fora do domínio, velocidade, orçamento, tempo
representável ou finitude é recusada sem substituir a última fase válida.
O ponto de parada é a última fase aceita, com motivo explícito; não alegar
intersecção física exata da superfície a partir de uma recusa de passo.

Guardar cargaC,massakg,proveniência das constantes, fonte/modelo/grau,
época UTC/TDB, matriz completa, posições/GMs/exclusões dos centros, controles,
passo, tempo próprio, origem sintética/observada dos parâmetros e hashes.
Separar a incerteza do modelo do erro do integrador e quantização gráfica.

## Critérios fixados antes de implementar/medir

- B uniforme: duas cargas de sinais opostos e q=0; solução helicoidal
  analítica e DOP853 independente, velocidade/energia magnética conservadas
  relativamente≤1e−12 em dez períodos. B não realiza trabalho.
- E uniforme e gravidade uniforme: solução analítica, sinais, q/m e soma
  das acelerações; desligar cada atuação sem mudar o campo desenhado.
- Campo corporal congelado e gravidade dos quatro centros: DOP853 com
  rtol1e−11,atol separados para posição/velocidade; comparação em instantes
  iguais e refinamentoN=2000/4000/8000 em dez períodosgiro. Razão dos erros
  consecutivos3,4–4,6 quando acima do piso numérico; erro fino de posição
  ≤5e−4 do raio de giro inicial+1e−5m, velocidade≤5e−4 da escala inicial.
- Diagnósticos: deltaK, trabalho elétrico e gravitacional por passo,
  potência magnética, potencial estático e energia total. Residual do
  trabalho discreto≤1e−12 da escalaK+|trabalhos|; erro da energia com
  potencial deve convergir com o passo. Não usar conservação mecânica
  sem incluir o trabalho deE ou ignorar fontes que variam no tempo.
- Fixtures com gravidade comparável à forçaLorentz podem usar q/m sintético,
  explicitamente identificado, além de casos físicos próton/elétron.
- Recusas: tiposbool/nãofinitos, massas/passos inválidos, energia/tempo não
  representáveis, gyroexcessivo,v>0,01c, fonte/campo indisponível, cruzar o
  interior com endpoints externos, limites externo/interno de ambos modelos.
  Fase de entrada imutável e nenhum dado de origem alterado.

Arquivar fontes/fixtures e receita antes de testes. Após ciência: trajetória
3D/sonda ligada ao mesmo estadoSI; worker com orçamento explícito; pausas,
save/load/ramos/restart/export; jornadaCEF100/150 e perfil próprio. Não
herdar o perfil de nuvens de C2-12, dos mapas ou dos quatro centros.

## Validação do adaptador, fixada em 25/10 antes dos testes

O adaptador exige uma fase pausada com exatamente quatro centros, identidade,
revisão, tempo e escalas canônicas coerentes com a leitura. Ele reproduz o
provedor na mesma fase antes de congelar as fontes. Converte a gravidade para
SI e para os eixos locais pela transposta da matriz corporal; conserva a
aceleração do centro na soma.

Comparar g com um avaliador independente em J2000 e rotação de volta:
2e−13 relativo + 1e−12 m/s². Potencial: 1e−12 relativo. Comparar B com o
provedor já aceito em até 2e−18 T, sem repetir toda a validação de IGRF/JRM.
Cobrir IGRF e JRM nos graus 1, 13 e 18. Máscaras, cruzamentos internos e pontos
fora do domínio não podem aumentar o contador de consultas de B. Alterações
nos dados de entrada ou descritores exportados não podem mudar o snapshot.
Recusar unidades, referencial, centro, época, grau e metadados incoerentes,
além de termos gravitacionais não adotados.

Antes da execução corporal de 25/10: a referência DOP853 integra deslocamento
em relação à semente, com atol de 1e−11 m e 1e−7 m/s, rtol de 1e−11 e passo
máximo de um doze avos do período inicial. Comparar em 40 instantes por
trajetória. Testar os quatro modelos com ambas as cargas de massa de próton,
e elétrons em IGRF e JRM13, todos em dez períodos. Acrescentar um cenário
sintético terrestre a 500 km, v=100 m/s e omega inicial de 0,1/s, durante um
período: gravidade e Lorentz comparáveis, com convergência da energia. Esse
cenário complementa os dez períodos físicos; não substitui nenhum deles.
Constantes e incertezas estão fixadas em staging/constants.json, pela tabela
primária CODATA2022 do NIST. As incertezas não são propagadas neste teste.

Correção numérica antes da rodada corporal E: preservar uma origem fixa e
acumular deslocamentos separados na Phase. A posição absoluta publicada é
a soma arredondada; origem e deslocamento também precisam ser arquivados
para continuar exatamente. Posição e velocidade continuam sincronizadas.
Calcular trabalho pela soma cinemática dos dois drifts e a variação do
potencial pela diferença algébrica estável, sem subtrair dois potenciais
grandes. A rodada B passou os dez casos físicos, mas o caso sintético
expôs arredondamento nos diagnósticos e na acumulação absoluta. A rodada D
corrigiu os diagnósticos, preservou os estados anteriores bit a bit e ainda
encontrou um piso na energia fina. A rodada E deve repetir todos os casos
com a nova acumulação; nenhuma tolerância é ampliada.
