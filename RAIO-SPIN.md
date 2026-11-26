# C2-06 — raio geométrico e rotação cinemática

Contrato anterior à implementação,14/10/2026. A dinâmica atual continua sendo
newtoniana entre centros de massas pontuais. Raio e spin não ativam J2, marés,
contato, torques, precessão ou energia interna. Esses operadores exigem os
contratos próprios de C2-11. Os balanços atuais medem energia e momento
angular orbitais/translacionais, sem alegar incluir rotação interna.

Guardar atributos separados da identidade/fase e da fonteAtlas imutável.
Raio não definido é null; zero é raio pontual explicitamente definido. Atlas
pode fornecer uma esfera equivalente por volume de seus três semieixos
(r=(abc)^(1/3)), ou esfera de referência já declarada. Registrar a derivação e
o valor original, sem dizer que Terra é uma esfera observada. Sem fonte ou
escolha do usuário, raio permanece desconhecido. Alterar raio vira parâmetro
do usuário, mantendo os valores de origem no registro original.

Spin é vetor angular em rad/s no referencial inercial da sessão. null significa
não definido, distinto de vetor zero. Orientação inicial didática identidade;
ao editar o vetor, preservar a orientação atual por quaternion de referência
mais instante do modelo. Evoluir q(t)=exp(omega*(t-t0)/2)*q0 com tempo SI,
normalização e redução angular. Não copiar rotaçãoIAU automaticamente como se
fosse um grau de liberdade dinâmico. Não atribuir energia/momento de spin sem
um modelo de inércia interna.

Domínio operacional: raio0–1e12m ou ausente; normaomega<=1e3rad/s; quando há
raio positivo, velocidade tangencial R|omega|<=0,01c. São limites clássicos
adotados, não uma avaliação de estabilidade estrutural ou de material.
Atributos são transação guardada por sistema/token/revisão/tempo/frame; pausa
na aceitação, não modifica um bit da fase ou energia de referência IAS15.
Registrar antes/depois e que balanços translacionais externos são zero;
energia/torques internos não avaliados, em vez de inventar valores nulos.
Checkpoint3 passa a geração3.1, conserva leitura3.0 com atributos padrão e
compatibilidade1/2; validar atributos e reproduzir seu histórico antes da troca.

Visualização padrão continua com marcadores ampliados. Modo separado de raios
físicos usa exatamente o raio SI e não muda a dinâmica; objetos sem raio ou
pontuais não ganham esfera inventada. EixosRGB representam orientação
cinemática do corpo selecionado; amplificados junto do marcador no modo
marcadores e em escala geométrica no modo físico. Não são vetores de força.
Nome completo no cadastro; rótulos contextuais abreviados evitam sobreposição.

Aceite: vetorzero/ausente, esfera/derivação, ortogonalidade/quaternion, continuidade
ao editar, rotação direta em tempos e eixos variados, inversa da matriz de
renderAtlas, ausência de mutação de fase/drift/força, domínio inválido atômico,
criação/remoção/checkpoint/legados/histórico, UIreal e raio/rotação medidos no
motor. Testar física e orientação separadamente. C2-06 continua parcial até
prévias orbitais/baricentro/escape e experiências de conservação/encontros.
