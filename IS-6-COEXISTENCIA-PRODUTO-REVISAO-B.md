# K3B — leitura de relógios e inspeção em 150%

A 0.19.0 passou pela jornada funcional: Terra/Júpiter, oito visibilidades,
14 recusas, posições científicas, restauração e cancelamento HTTP real na
primeira tentativa. App e servidor encerraram 0/0 e não restaram PIDs próprios.
As fontes e evidências A ficam preservadas.

A inspeção de quatro PNG encontrou uma limitação: a razão dτ/dt∞ da Terra
arredonda para 1 com oito algarismos significativos. A revisão 0.19.1 acrescenta
o déficit do relógio já calculado pelo modelo, em notação científica quando
necessário. Muda apenas ui/is6-layers.js; ciência, serviço e cena são idênticos.

O verificador B conserva a jornada e acrescenta leitura não nula do déficit
e uma captura do painel magnético rolado em 150% para cada corpo, totalizando
seis imagens. O painel mantém o botão de saída visível. A revisão não altera
qualquer tolerância científica nem transforma a prova A em aceite da UI final.
Perfil da interface final, persistência composta e migração continuam pendentes.
