# IS4 — perfil nativo prévio25/10/2026

Candidata0.8.1 preservada, runtimeIS4; uma carga-teste e trajetória129amostras.
Quatro janelas: Terra IGRF14 próton500km e Júpiter JRM33 grau13 elétron1,5Rj,
cadauma visível/oculta. Pitch90graus; velocidades100000/1000000m/s.
Cada janela recria partícula, g+B+E=0 ativos; fonte orbital pausada e idêntica.
200passos/s real;30s aquecimento+60s captura SGCT, CEF1080p100%renderizado.
Câmera enquadrada no início, foco acompanha trajetória confirmada; sem entrada
humana durante warm/capture via body.inert, restaurado ao terminar.

Limites prévios: mediana<=16,7ms,p95<=25ms,p99<=50ms,nenhum>100ms,
RAMsoma working sets<=8GiB,GPUdedicatedprodutoconservadora<=5,5GiB,
passosaceitos/tempo/200>=0,9. Registrar integralmente quadros após descartar
primeiro intervalo; não filtrar picos. Registrar estado fonte/partícula/vista,
memória e visibilidade em0/20/40/60s. Nenhum erro/terminação de integração.
Visibilidade usaDrawElements mantendo receptor; confirmação pode atrasar
até2s, limitada no controlador. Captura não comprova cada apresentação GPU.

GPU: coletor diagnóstico66amostras, inventárioowned completo incluindopartícula,
ExpectedModeexperiment/ExpectedWorkerpaused (workerORBITAL). RUNNINGpartícula
verificado à parte. Exigir coberturaUTCintegral, semamostras/countererrors
inválidos. Não herdar automaticamente aceiteIS3. ZIPfontes+receitabuild e
hashmotor/owner preservados. Auditor separado decideaceite; conclusão do
coletor ou quatrojanelas não equivale aaceite. Sóestecenário, semMHD/plasma.
