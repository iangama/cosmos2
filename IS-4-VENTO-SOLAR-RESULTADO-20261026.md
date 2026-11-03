# IS4 — cenário de vento prescrito,26/10/2026

Candidata0.9.0 acrescenta uma carga-teste no campo de Parker com duas
polaridades, E=−u×B emSI e gravidade dos quatro centros congelados. Parâmetros
são didáticos, sem ajuste a observações atuais. Exclui banda equatorial±5°,
raios fora0,1–10AU e regiões próximas dos planetas. Não resolve MHD, CME,
espalhamento, magnetosfera, colisões ou resposta do plasma.

Campo:144pontos/32recusas, fórmulas esféricas independentes, divergênciaB e
curlE, trabalho por quadratura e rotaçõesgravidadeJ2000. Potenciais pareados
passaram20casos contraDecimal80, incluindo deslocamento1e−7m. Trajetórias:
seis físicas emdezgiros, umcasosintético e quatrocontroles passaramDOP853,
refinamento e trabalho;auditoriaDecimal60dos onze brutos passou. Caso
sintético converge energia por aproximadamente4 ao dividir o passo por2.

Worker/persistência:três espécies vento, trabalhoE não nulo,save/load/novo
processo comfuturo77exato,ramos+vista selados,14recusas e dois replays de
fases/trilhas corporais aceitas sem diferença. Não converter schemasantigos
silenciosamente. CEF:norte/sul,polaridades±,trêsespécies e trêsraios;recusaHCS,
E/B/g separados da exibição,save/load/ramos/novo worker/export/restart,12guardas
recusadas,pausas199–292ms. Stallnativo2s pausa/preserva/recupera.

Perfil0.9.0:quatrojanelas,30swarm+60smedidos,próton1AU/elétron5AU,visível/
oculto,200passos/s,CEFreal1080p. p95máximo14,0466ms;p99máximo14,5657ms;
0quadros>100ms;RAM1,196274GiB;GPUconservadora2,968933GiB;ritmomínimo0,999147
do solicitado. Atraso amostrado de confirmação máximo0,200s. Dadosbrutos,
coletor/inventárioGPU e fontes estão preservados com hashes;auditoriaaceita.

SeisPNGtrajetória e setecloseups revistos. A revisão detalhada encontrou um
rótulo enganoso quando a trilha estava oculta. Correção0.9.1 isolada altera
somente JS: informa dadosconfirmados/ocultos e nome científico da orientação.
TodosPythoniguais0.9.0;regressãoCEF e captura150% passaram. Perfil medido
continua identificado como0.9.0. Conteúdo longo exige rolagemvertical.

Evidências em evidence: is4-wind-field-20261025c;is4-wind-potential-20261025a;
is4-wind-trajectories-20261025b e audit-20261025b;is4-wind-experiment-20261025b;
is4-native-wind-product-20261025a;is4-wind-profile-20261025a e audit-20261025a;
is4-wind-hidden-label-20261025a e sua visual-review. Extensão .json.

Fontes físicas: Dalla et al.2013,https://doi.org/10.1002/jgra.50589,PDFautor
arquivado emstaging/research-sources.json. Nenhuma promoção. Próxima fatia do
planoIS5:zona nuclear ligada àfaseSolar,pp/CNO compartilhando combustível;
resposta térmica/transporte e luminosidade superficial exigem modelos próprios.
