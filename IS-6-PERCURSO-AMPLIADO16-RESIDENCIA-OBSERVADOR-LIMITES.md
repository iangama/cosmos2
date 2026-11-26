# Limites de admissão do observador — anteriores ao ensaio C

Schema6 registra histórico nativo por linha e um journal separado de
nascimento/saída. O auditor recalcula os totais brutos, a pertença de cada
PID, as mudanças do inventário, a cronologia deRAM e a correspondência
do journal. Também exige mais polls que amostras1Hz e intervalo máximo
entre polls≤0,25s. Isso limita a interrupção do observador; não transforma
polling em rastreio completo de todos os processos do Windows.

Os primeiros66registros completos devem conservar o cenário científico
exato; cada registro verifica seu próprio conjunto de caminhos. As fases
de transição/aquecimento também conservam todos os quadros e dados. Saídas
nãozero, caminhos que mudam dentro da mesma consulta, valor inválido e
identidade não resolvida continuam recusando todo o ensaio. RAM indisponível
não recebe zero. WDDM sem contador exposto continua desconhecido e listado.
