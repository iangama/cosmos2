# Palco dipolar — especificação antes da implementação

Fatia autorizada de C2-01/12/13/20. Não é aceite desses marcos nem campo IGRF.

Uma partícula de teste clássica, próton ou antipróton de massa positiva, em
campo dipolar estático e gravidade Newtoniana de uma esfera prescrita. Integrar
posição e velocidade completas: m dv/dt = q v×B − m GM r/|r|³, com operadores
independentes. E=0. Não há colisões, plasma coletivo, atmosfera, vento solar,
rotação terrestre, campo induzido, reação de radiação ou QCD nessa partícula.

R=6.371e6 m é o raio esférico escolhido para o modelo; GM terrestre nominal
IAU2015=3.986004e14 m³/s², multiplicável. B equatorial superficial e eixo são
prescritos; B=B_eq(R/r)³[3(d·r̂)r̂−d], com d unitário. Não atribuir época,
coordenadas geográficas ou precisão observacional a esse planeta ideal.

Fontes: [Fitzpatrick, dipolo, equação660](https://farside.ph.utexas.edu/teaching/jk1/Electromagnetism/node52.html),
[partículas/espelhamento, equações2.92–2.100](https://farside.ph.utexas.edu/teaching/plasma/lectures/node24.html),
[IAU2015](https://iauarchive.eso.org/static/resolutions/IAU2015_English.pdf).
Usar DOP853 refinado para a órbita completa; a previsão de espelhamento por
momento magnético é aproximação adiabática comparativa, não força adicional.

Entradas: raio equatorial inicial2.5–6R, B_eq5–40µT, energia1–30keV,
ângulo com B5–85°, inclinação do eixo0–60°, carga±e, duração5–50s,
GM0.1–3nominais. Limitar cálculos e amostragem explicitamente; rejeitar uma
combinação que ultrapasse o orçamento, sem substituir por trajetória falsa.

Apresentação: campo omnidirecional3D, esfera na escala física, linhas do dipolo
analíticas identificadas, trajetória completa e referência com operadores
ligados. Gravidade e B têm visibilidade independente da atuação. Sondas devem
ler B, g, forças, velocidade, energia, potência magnética e pitch no instante.
Curvas de B/pitch/energia, linha do tempo e exportação com contrato/procedência.
Não ligar visualmente amostras incapazes de resolver a giro-órbita sem avisar.

Verificações fixadas antes do cálculo:
- Campo: polos/equador e escala r^-3 contra fórmula esférica independente;
  divergência e rotacional no exterior, erro normalizado≤1e-7 por diferenças
  finitas; covariância da inclinação, linhas r=L R sin²θ tangentes a B.
- Dinâmica: limite uniforme contra solução Lorentz analítica; duas forças
  desligadas contra reta inercial; magnético não realiza trabalho.
- Energia K+U do operador aplicado: erro normalizado≤1e-7 no preset, com escala
  K0+|U0|; refinamento em integrador independente para a janela não caótica.
- Espelhamento: inversão de v_parallel e aproximação adiabática identificada;
  diferença da latitude≤0.2° em preset com raio de Larmor/escala de campo pequeno.
- Controles: todas as combinações preservam fonte/campo completo; visibilidade
  não muda hashes físicos nem medições. Limites terminam a integração sem
  inventar produto de colisão. Validar UI nativa, sondas/gráficos e errosJS.

Estado: implementado e validado localmente. dipole-check.json registra campo/operadores/energia/RK45/espelhamento/limites. dipole-ui-check.json e native-dipole-check.json passaram; imagens finais nativas revistas. Não aprova marcos inteiros nem modelo de campo terrestre observado.
Antes dos testes: mínimo do pitch ampliado de15° para5° para explorar a
fronteira interna e o cone de perda. Mesmos critérios de precisão/orçamento;
atingir1R encerra o modelo, sem afirmar colisão atmosférica simulada.
