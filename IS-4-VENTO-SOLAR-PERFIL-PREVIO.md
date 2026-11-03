# IS4 — perfil próprio do vento prescrito0.9.0

Quatro janelas fixas: próton1AU/+30°/A+ e elétron5AU/−60°/A−, cada qual
visível/oculta. Velocidade relativa100/1000km/s,pitch90°,vento400km/s,
Br3nT@AU,Omega2pi/(25,38dias). E/B/g atuam. Fonte orbital pausada e
inalterada; uma partícula e até129 amostras reais na trajetória nativa.

30s aquecimento+60s captura SGCT por janela, CEF real1920×1080/100%,
200passos/s real (=200*dt emsegundosSI/sreal). Câmera enquadrada no início,
foco acompanha janela recente confirmada. body.inert somente durante captura
e aquecimento, com render/integração/UI ativos; restauração nofinally.

Limites prévios iguais aoG0 vigente:mediana16,7ms,p9525ms,p9950ms,0>100ms,
RAMsoma working sets8GiB,GPUdedicadaconservadoraproduto5,5GiB,
ritmomedido/solicitado≥0,9. Sem descartar picos; registrar todos intervalos
e descartar somente o primeiro intervalo da captura, conforme receita anterior.
Inventário completo do produto a cada janela inclui worker da partícula.
GPUcoletor66amostras deve cobrir UTCintegral,sem countererrors/invalid_samples;
ExpectedWorkerpaused refere-se ao workerORBITAL. PartículaRUNNING verificada
separadamente em0/20/40/60s, junto de fonte,vista,flagsnativas,RAM eDXGI.

Exigir nenhuma terminação/erro, fonteidêntica e uploadconfirmado com atraso
amostrado≤2s. Oculto usaDrawElements=false eEnabled=true para manterreceptor.
Arquivar fontes, contratos, recibos prévios e hashmotor/owner antesexecutar.
Auditor recalcula métricas e correla processoGPU/relógios/visibilidade.
Conclusão do coletor não é aceite. Aceite restrito às quatrojanelas; não
validar MHD, dados solares atuais, múltiplas cargas ou todasconfigurações.
