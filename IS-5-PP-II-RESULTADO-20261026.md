# IS5/C2-20 — ramo pp-II,26/10/2026

Candidata local0.12.1 aprovada no recorte de zona pp-I/pp-II/CNO-I com
composição e temperatura acopladas, rho e volume fixos. Sem promoção.
12espécies e12canais compartilham H/He e intermediários. A extensão soma
He3+He4→Be7, capturaeletrônicaBe7→Li7 eLi7+p→2He4.

Ciência is5-pp2-20261026a ACEITA:44verificações de taxas/EC,32768gates,
10casos e6recusas. JacobianoEC incluiYe variável;testes analíticosEC/Li7,
BDFindependente em modos prescrito e térmico (energiaU+inversãoEOS),
refinamento,conservação e limites passaram. FixturetérmicaECb inclui2casos.
Worker is5-pp2-worker-artifact-20261026a ACEITO:13recusas,sondas,T/U,
checkpoint/save/load/newprocess,32ramos e locksWindows.

Todos12Q usam diferenças de massas atômicasAME2020originais, com Qfit
preservado separadamente. pp-I,pp-II,CNO-I fechamDecimal26.730968386MeV.
ECsolarSFIIeq40 exige estritamente10<T6<16 e usaρYe uma vez;incerteza
reportada2%,nãoerro numérico. MédiaνBe7.814MeV fixada por perfilSolar,
sem espectro local. ECconsomee−;βproduze+;Qatômico inclui aniquilação.

CEF0121 ACEITO4grupos/11recusas/zeroJS.4PNG100/150 revistos,marcador
21018pixels emcada;sonda rotula abundância negativa minúscula como resíduo,
sem alterar dado bruto/exportação. A0120 foi preservada:CEFfuncionalpassou,
reviewvisualfalhoupelo resíduo semrótulo;0121isolada corrige a apresentação
e guarda modo térmico na interface dedicada. Modelos científicos preservados.

Perfil is5-pp2-zone-profile-20261026a:4janelas próprias30swarm+60sSGCT,
1920×1080/100%,2amostrascalculadas/s;fracaon/off×gráficosvisíveis/ocultos.
Auditorframes is5-pp2-zone-profile-audit-20261026a ACEITO. Auditor
suplementar is5-pp2-zone-profile-probes-20261026a ACEITO:24estados,
2976valores escalares/12espécies/12canais exactos por índiceactual+reference.
Ambos vinculam dados brutos e hashes. Não é throughput dointegrador.

| Medida | Pior resultado | Limite prévio |
| --- | ---: | ---: |
| Mediana | 13.341500ms | 16,7ms |
| p95 | 13.883410ms | 25ms |
| p99 | 14.277658ms | 50ms |
| Quadros>100ms | 0 | 0 |
| RAM produto | 1.214195GiB | 8GiB |
| GPU dedicada produto | 2.982849GiB | 5,5GiB |
| Ritmo medido/solicitado mínimo | 0.964512 | ≥0,9 |

EOS ideal: íons clássicos,elétronsFDnão-relativísticos e radiaçãoLTEconfinada.
Sem Coulomb/screening/relatividade/pares/ionizaçãoparcial/estrutura estelar,
transporte/hidrostática/luminosidade superficial. FonteSolar arquivada é
referência didática, não calibração de um modeloSolar completo. IS5/C2-20
continuam parciais. Próximo pp-III efetivo contratado separadamente.
