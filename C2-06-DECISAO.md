# C2-06 — decisão local

**Aprovado localmente em14/10/2026, no recorte abaixo.** Editor gravitacional
com1–128massas ativas, criação/remoção e IDs estáveis; massa/fase SI, raio/spin
cinemáticos; cônicas antes/proposta, COM/conservação/escape; três modelos
controlados de encontro/captura/ejeção e sonda pontual sem retroação.

Geração editável3.4.0, REBOUND5.2.2/IAS15epsilon1e-9, semsoftening/colisões.
EXE OpenSpace0.22 SHA
cfcd7fff4a454a8f1024ccf7603fdc32b624bc6e142d4d7e65cbbbca3eb218d6.
Runtime oficial preservado. Contratos: EDITOR-GRAVITACIONAL, RAIO-SPIN,
ORBITAS-EDITOR, ENCONTROS e SONDAS-BASICAS.

O estadofloat64/checkpoints foi confrontado com CSPICE, DOP853, REBOUND e
SciPy, incluindo100períodos de duas órbitas (<=3,681mm). Entradas antigas e
corrupções são recusadas antes de instalar estado; fonte/época/GM da cópia
Sol/Terra/Lua e relógio Atlas permanecem independentes. As cinco jornadas
nativas finais passaram semJS, preservando o checkpoint do dono. Dez capturas
foram revistas pelo agente; isso não equivale a opinião estética do dono.
Recibos/imagens selados em evidence/c206-final/manifest.json.

P128c206p128c:3×60s após30s,1080p,128massas positivas gravitando, pedido1/
efetivo>=0,9995616u/s; Erel<=5,34e-15/Pnorm<=5,69e-17. p95<=23,405ms,
p99<=24,600ms/zero>100ms.20pausasAPI<=36,282ms, câmera<=24,684ms.
RAMsoma1,06362GiB/GPUWDDMsoma2,99042GiB/DXGIbudget>=7,19014GiB.
Fontecongelada native-benchmark-c206p128c-source.tar.gz permite re-auditoria.

Regressão geral g0async4:9percursos60s/30s, Atlas/Atlas+P32/P32visível,
p95<=18,003ms/p99<=19,210ms/zero>100ms; RAMsoma0,99556GiB/GPUWDDMsoma
2,99430GiB/DXGIbudget>=7,19014GiB.66amostrasGPU/rota, UTC/cenário/SHA/
cobertura conferidos. SomaWDDM pode repetir compartilhados, não é VRAMúnica.
Arquivo de fontes g0async4 SHA0551c3ded5c308084fbf7ddd6c57e04f505b0df88ad24c819d5cf977b2e2a348.
Mesmo motor/app nos dois perfis; coletor reforçado preserva/recusa erros sem
alterar método ou limites. P128 foi re-auditado com sua fonte congelada.

As tentativas rejeitadas/incompletas continuam preservadas. g0labels revelou
log síncrono na threadgráfica; AsyncScriptLog passou ordemUTF8/flush/close/
shutdown, contrato Windows/Linux e120s após12recriações semhitches/perda/erro.
g0async foi interrompido pelo pedido temporário de uso da tela; g0async2 falhou
na instrumentaçãoGPU. g0async3 teve jogo aberto (confirmado pelo dono), queda
DXGI7,19→3,86GiB e timeout do coletor. Não juntar amostras nem atribuir cada
hitch ao jogo. g0async4 foi integral, após fechar o jogo/reiniciar o simulador.
DIAGNOSTICO-QUADROS.md conserva a investigação e os limites.

Limites: semtorques/J2/energia interna/contato/fusão; raio/spin são geometria/
cinemática e os balanços são translacionais. Cônicas são instantâneas, com
quantização gráfica separada da física; escape/captura não têm garantia
eterna. Fronteira1mm pausa/recusa sem inventar contato. A sonda básica não
persiste; a rede de instrumentos pertence aC2-11. Cópia real apenas3corpos.

Uma consultaWS externa durante diagnóstico reproduziu pausa970ms emserver-
preSync, com forte suspeita dojoin de cliente desconectado; falta reprodutor
controlado. Não prometer ausência de pausas em reconexão/setup ou sob disputa
com jogos. Esse fluxo extra não integra as rotas quentes aprovadas; reparo
acompanhado em output/ws-cleanup-investigation.md, sempatch adicional aplicado.

Agora7marcos aprovados/20restantes,14da v1. PróximoC2-11: sondas salvas e campo
3D, cortes/potencial/maré/gráficos/ramos/J2/marés e perfis maiores; não tratar
seu protótipo como marco inteiro aprovado. Construção continua autorizada.
