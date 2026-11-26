# Camadas verificadas na cena de16corpos

A candidata0.25.1 passou pelas jornadas de importação/persistência e pelo
perfil próprio das referências gravitacional e magnética. O Atlas continua
com16centros; as camadas usam a cópia pausada de quatro corpos e os modelos
terrestre/joviano já adotados. A janela foi reaberta na vista inicial.

Na primeira jornada, dois pares atuais foram validados e dois registros
antigos foram importados pela interface real. Foram13confirmações e11recusas
de entradas inválidas sem trocar a vista confirmada. O reinício passou
sete confirmações, quatro combinações de visibilidade, exportação e um
cancelamento real. Cada ciclo fechou os quatro processos com código zero.
As23capturas originais do framebuffer foram inspecionadas em100/150%.

O plano próprio selou2192fontes antes da medição. As quatro janelas usaram
30s de aquecimento e60s medidos,1920×1080/UI100%, malha65×96 de1–3Rref,
ampliação200 e as mesmas amostras IGRF14/JRM33. O catálogo existente tinha
nove arquivos de latest/ramos/exportações, conservados byte a byte.

| Janela | Quadros | p95(ms) | p99(ms) | Acima de100ms |
| --- | ---: | ---: | ---: | ---: |
| Terra estática | 4.516 | 14,117 | 14,854 | 0 |
| Júpiter estático | 4.519 | 14,123 | 14,897 | 0 |
| Terra, visibilidade2Hz | 4.518 | 14,178 | 14,865 | 0 |
| Júpiter, visibilidade2Hz | 4.517 | 14,175 | 14,915 | 0 |

Total:18.070quadros. Máximo19,1212ms; maior mediana13,3504ms. Os240comandos
terminaram dentro da janela, com p95máximo0,231533s e máximo0,258147s.
RAM atingiu1,251690GiB; WDDM dedicada+compartilhada3,024120GiB. Preflight3,
66amostras PDH por janela, identidade temporal dos processos, fases e flags
reais, limpeza e restauração de contexto passaram no auditor separado.
O host terminou com quatro saídas zero e outra0.25.1 ficou aberta.

Recibos em evidence: is6-moons-layers-native-20261112a/b,
is6-moons-layers-native-process-20261112a/b,
is6-moons-layers-native-cycle-20261112a,
is6-moons-layers-visual-20261112a e
is6-moons-layers-profile[-audit]-20261112a, todos JSON.

O resultado cobre essa cena ampliada e a API de visibilidade com registros
importados existentes. Não mede gravação ou partida fria. Não resolve a
causa da pausa580,569ms do K5A anterior, que continua recusado. A expansão
dinâmica para16corpos exige seus próprios testes. V1segue7/21 e IS6continua
incompleto; nenhuma candidata foi promovida.
