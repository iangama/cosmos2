# IS5 — perfil próprio do instrumento solar0.10.3

Contrato antes do coletor e medição. Pré-requisitos: jornada CEF103 e revisão
visual dos originais aprovadas, bases anteriores preservadas. Nenhuma promoção.

Quatro janelas: cenário padrão com todos os operadores e com fraca desligada,
cada qual com gráficos de composição/energia/neutrinos/referência visíveis ou
ocultos. Mesmas condições padrão15MK,rho1,5e5kg/m³,H0,34,CNO0,01,N14,
duração1Myr,volume1m³. Marcador/rótulo da fonte arquivada visíveis em todas.

Reprodução de2amostras já calculadas/s real,começa index0.30s aquecimento e
60s SGCT por janela; não chega ao índice240. CEF1920×1080/100% ativa e
renderizada; body.inert só durante warmup/captura. Cenário nuclear calculado
antes, portanto este perfil NÃO mede throughput de integração Radau. Medir
reprodução/sonda/UI/marker/IPC, não evolução termodinâmica inexistente.

Limites G0 prévios:mediana16,7ms,p9525ms,p9950ms,0>100ms;RAMsoma working
sets8GiB,GPUdedicada conservadora produto5,5GiB;ritmo de seleção medido/
solicitado≥0,9 e≤1,05. Incluir todos intervalos, exceto primeiro intervalo da
captura segundo receita existente. Fonte orbital idêntica/pausada,zeroerro,
worker/artifact/token/revision e fonte nuclear constantes durante janela.

GPUcoletor66amostras cobre UTCintegral;ExpectedWorkerpaused é o ORBITAL.
WorkerIS5 separado deve permanecer vivo e reproduçãoativa com índices
crescentes. A cada0/20/40/60s: resumoIS5,orbital,native label/marker/position,
RAM inventário completo,incluindo subprocessoIS5,DXGI e identidade fonte.
Provar hash dono e arquivos executados inalterados. Guardar fontes/receitas/
recibosprévios/hashmotor/brutos antes executar. Auditor separado recalcula
percentis,ritmo,memória,coberturaUTC,identidades,visibilidades e invariantes.

Aceite restrito às quatrojanelas; não resolve cálculo concorrente,grandes redes,
transporte estelar,EOS,luminosidade,emissão espacial ou conclusão de IS5.
