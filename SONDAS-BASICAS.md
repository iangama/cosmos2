# Sonda básica do editor gravitacional

Contrato de implementação, 14/10/2026. Completa a leitura pontual prevista em
C2-06; a rede de sondas, vetores, equipotenciais, marés e persistência pertence
a C2-11. Uma leitura é uma amostra congelada, sem massa e sem retroação.

O usuário fornece x/y/z em metros no referencial inercial do experimento.
A consulta exige sistema, token, revisão, tempo e referencial confirmados.
O worker avalia as mesmas massas e posições float64 usadas na integração:
`g = Σ GM_i (r_i−x)/|r_i−x|³`, `Φ = −Σ GM_i/|r_i−x|`, zero no infinito.
O GM aplicado é a massa canônica multiplicada pelo GM nominal fixado nas
unidades do projeto. A fonte Atlas continua identificada separadamente.

O resultado contém posição, aceleração vetorial/norma em m/s², potencial em
J/kg, fontes individuais, geração científica, tempo e revisão. Não é força
sobre uma massa material nem previsão relativística. Raio e spin geométricos
não alteram o campo pontual. Distância menor que 1 mm de qualquer fonte é
recusada, sem regularização ou valor finito inventado. Componentes somadas
com math.fsum; posições limitadas ao domínio SI do editor.

Calcular, mover a câmera ou esconder a marca não altera estado, integrador,
pausa, energia, histórico ou checkpoint. A interface pausa explicitamente
antes da consulta e informa quando o estado posterior tornou a amostra antiga.
Uma mudança de sistema limpa a leitura. O marcador é contextual e não define
raio ou extensão física da sonda. A leitura não é persistida nesta fatia.

Verificação: solução de massa isolada, superposição simétrica/cancelamento,
diferença finita de −∇Φ, deslocamento comum, fixtures 2/32/128 e cópia Atlas,
entradas inválidas sem mutação e marca/tempo/revisão no CEF nativo.
