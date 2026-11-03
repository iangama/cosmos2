# C2-06 — experiências controladas de encontro, captura e ejeção

Contrato prévio14/10/2026. Três modelos definidos pelo produto e escolhidos
pelo usuário; nenhum é um sistema observado. Guardar fases iniciais completas,
GM/unidades, origem do modelo, horizonte recomendado, IDs e geração no seed.
Reiniciar recupera essas condições com novo sistema/token. Carregar um modelo
é substituição explícita do cenário pausado, assim como o reinício atual.

1. Encontro hiperbólico de duas massas: energia relativa positiva e desvio
   gravitacional, com trajetória entrante/saínte. Um par isolado conservativo
   não ganha captura ligada sem outro mecanismo de troca de energia.
2. Visitante inicialmente livre em relação a um binário, capturado por troca
   em uma interação de três massas; um dos membros antigos se afasta.
3. Tripla com visitante inicialmente ligado ao conjunto, que se desagrega
   em um binário e um corpo com energia orbital externa positiva e movimento
   de afastamento. Não chamar um estado momentâneo de prova de escape eterno.

Condições de2/3 selecionadas por investigação numérica local registrada em
output/gravity-experiment-search.json, não copiadas como observação. Examinar
com integrador independente antes de liberar no catálogo. Referência conceitual
primária: [McMillan/Hut, espalhamento binário–simples VI](https://arxiv.org/abs/astro-ph/9604015).
Não usar esses artigos como fonte dos números particulares definidos aqui.

Diagnóstico de três massas: par instantâneo ligado, energia externa de
separação entre terceiro eCOMdo par com mu incluindo todas as massas,
velocidade radial externa e distância/semi-eixo do binário. Identificar fase
hierárquica só com energia externa>0, afastamento e separação/a>30. Curvas
osculantes continuam aproximações instantâneas; energia total/P/L e COM do
sistema inteiro oferecem a verificação independente da troca de energia.
As fontes não são apagadas, nem as velocidades ajustadas para forçar resultados.

Mostrar entradas, objetivo, horizonte, antes/depois, estados intermediários,
resultado medido e conservação. Pausar uma vez no horizonte recomendado,
sem mexer na solução; permitir retomar além dele. Se o usuário altera massas,
fases ou população, sinalizar que mudou o modelo inicial e não prometer o
mesmo desfecho. Raio/spin cinemáticos conservam a dinâmica destas experiências.

Ensaio: IAS15 versus DOP853 e tolerâncias mais estritas nos mesmos dados,
domínio mínimo de separação, sinal de energias/IDs e afastamento em pelo
menos dois instantes distantes; E/P/L/COM conservados sem intervenções ocultas;
checkpoint antes/durante/depois e reinício exatos. Jornadas via CEFcom controles
reais e relógio efetivo; imagens da interação/resultados revisadas. Perfil128
massivos separado informa taxa efetiva/precisão/FPS. Não trocar o perfil
por partículas sem massa ou por128 marcadores sem interação gravitacional.
