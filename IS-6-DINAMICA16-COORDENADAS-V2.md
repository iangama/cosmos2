# Revisão numérica dos16corpos

Registrada antes do ensaio formalB. A original20261112a permanece recusada:
posição0,344698m e velocidade18,239958µm/s contra DOP853; transformação
absoluta0,385853m/20,331371µm/s. Limites10m/10µm/s continuam vigentes.
Cinco épocas,25recusas,120pares e balanços passaram. Encélado domina o
desvio de velocidade; refinamento IAS15 ficou em0,029104m.

O diagnóstico fixado testou três representações da referência independente:
SI com os mesmos doubles iniciais, unidades canônicas e incrementos SI.
As duas primeiras deram51,932075 e34,274796µm/s; incrementos SI deram
6,411590µm/s. Não basta mudar unidades ou alinhar o primeiro estado. A
referência deve acumular deslocamentos em relação à fase inicial e avaliar
separações como separação inicial+diferença dos deslocamentos. São as mesmas
equações newtonianas, tolerâncias e passo máximo; muda a representação da
ODE independente. A condição inicial SI vem dos doubles canônicos do
produto, com ida/volta ao catálogo verificada separadamente.

Um segundo controle normalizou a transformação absoluta com move_to_com,
guardando a origem. Ainda deu12,958809µm/s. A ida/volta inicial já perdeu
até0,909495mm. Recentralizar depois não recupera bits perdidos ao somar
trilhões de metros em cada coordenada. Esses controles são diagnóstico,
sem aceite do teste original ou autorização para afrouxar tolerâncias.

A representação adotada mantém origem inercial e velocidade uniforme em
componentes separados. Uma mudança de referencial altera esses componentes,
mantendo as coordenadas locais usadas pelo solver. Não fundir a origem
grande nas partículas para depois subtraí-la. Implementar essa regra em
system16_frames.py, conferindo entrada finita, composição da origem ao
longo do tempo, independência de cópias e serialização explícita. O solver
continua recebendo a fase baricêntrica canônica, com os mesmos operadores.

O ensaioB usa a ODE SI incremental e uma segunda simulação envolvida nesse
referencial separado, guardando fases internas e origem/velocidade em toda
a série. A invariância é da interface de referencial adotada; não declara
que IAS15 em coordenadas absolutas trilionárias passou o ensaioA. Exigir os
mesmos limites de conservação, pares, refinamento, posição e velocidade.
Auditor próprioB reconstrói as métricas a partir das séries, sem interpretar
o formato deA como se já tivesse origem separada.

O passo máximo solicitado continua3600s. A diferença de dois tempos double
pode exceder isso em menos de1ns; sua auditoria admite somente2ULP do tempo
final na comparação desse intervalo, registrando o valor bruto. Isso não
altera o parâmetro fornecido ao integrador ou o horizonte de30dias.

Preservar módulo/conversor, executor e auditorA. B tem fontes/cápsula/recibo
próprios. A janela0.25.1 continua aberta; nenhuma candidata dinâmica foi
conectada à UI ou promovida. Não declarar aceitoB antes dos novos recibos.
