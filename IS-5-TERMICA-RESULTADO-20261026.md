# IS5/C2-20 — resposta térmica ideal,26/10/2026

Candidata local0.11.0 aprovada no recorte de uma zona pp-I/CNO-I com
temperatura/composição/reservatório evoluídos, densidade e volume fixos.
Não houve promoção;103 e redes de temperatura prescrita permanecem intactos.

EOS: íons clássicos ideais,elétronsFermi–Dirac não relativísticos e radiação
LTEconfinada. Reter energia nuclear nãoν;neutrinos escapam localmente,sem
perda fotônica,expansão outrabalho externo. A equação de energia inclui
dependência da composição/neutralidade na energia interna. Não converte
potência nuclear em luminosidade superficial;marcadorSolar temcor/tamanhográficos.

Ciência aceita:

- is5-thermal-eos-20261026a:27integraisFD vsmpmath50dps,27EOS/derivadas/
  Maxwell,12recusas. Maior erroFD3,67e−16rel;resíduoMaxwell1,92e−10.
- is5-thermal-20261026a:8casos/5recusas,pp/CNO/misto,gates,cold1s/hot1yr,
  BDFenergiaUinversa e refinamento. Maior erro deenergia6,38e−15normalizado.
- is5-thermal-feedback-20261026a:15→18,503490MK em1Myr,mesmas condições
  iniciais didáticas;BDFindep erroT2,06e−10rel,composição8,96e−14porbárion,
  refinamento1,22e−11relT,energia6,07e−14normalizada.
- is5-thermal-worker-artifact-20261026a:13recusas,fonteSolar arquivada,
  T/Usonda,save/load/newprocess exato,32ramos e locksWindows.

CEF011a passou4grupos/9recusas/zeroJS:controles,T/Uevoluídos,sondas,
gráficos,save/load/ramos/newworker/restart/export,fonte antiga sobreórbita
posterior e limpeza.4PNG100/150aprovados por revisãooriginal e21018pixels
do marcador emcadaimagem. Original versus préviainline conferidos porhash.

Perfil próprio is5-thermal-zone-profile-20261026b aprovado por
is5-thermal-zone-profile-audit-20261026b.4janelas30swarmup+60sSGCT,
1920×1080/CEF100%,2amostrasjácalculadas/s;fracaon/off×gráficosvisíveis/ocultos.
Resultado térmico integral arquivado;auditor confereT/P/U/Cv/energias de cada
índice,artifact_sha,identidades,fonteorbital,owner,RAM/GPU/coberturaUTC.

| Medida | Pior resultado | Limite prévio |
| --- | ---: | ---: |
| Mediana |13,33690ms|16,7ms|
| p95 |13,97617ms|25ms|
| p99 |14,41297ms|50ms|
| Quadros>100ms |0|0|
| RAM,soma working sets |1,202763GiB|8GiB|
| GPUdedicada produto |2,995056GiB|5,5GiB|
| Ritmo medido/solicitado,mínimo |0,964898|≥0,9|

TentativaA parou antes de medir por guard de versão herdado;nenhuma janelaA
foi reutilizada. Bexecutou as4janelas após corrigir o guard para0.11.0.
Perfil medeUI/reprodução/cena/IPC, não throughput do integrador térmico.

EOSideal não incluiCoulomb,screening,relatividade,pares térmicos ouionização
parcial. Não há pp-II/III,estrutura/transporte/hidrostática,perfil estelar
observado,luminosidade ou emissão espacial. Resíduosnuméricos não medem erro
dessas aproximações. C2-20/IS5 permanecem parciais. Próximo recorte pp-II
contratado em IS-5-PP-II-CONTRATO-PREVIO.md,domínio próprio10<T6<16.
