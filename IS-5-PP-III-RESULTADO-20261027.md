# IS5/C2-20 — ramo pp-III efetivo, 27/10/2026

Candidata local0.13.0: ciência, worker, jornadaCEF e revisão visual aprovados.
Perfil nativo próprioB aprovado; tentativaA reprovada e preservada.
A candidata continua isolada, sem promoção sobre o instalado ou outras bases.

A rede pp-I/II/III efetivo+CNO-I compartilha combustível em13espécies/14canais.
Be7+p→B8+γ compete com Be7EC. O canal B8→2He4+e⁺+ν agregaβ+ e continuação
forte por ressonânciasBe8. Não resolve populaçãoBe8 nem espectro; seu gate
forte+fraca não altera a meia-vida βintrínseca. O modelo mantém strict10<T6<16
pela leiECsolar, rho/V fixos e reservatório térmico ideal opcional.

QAME2020atômico: quatro ciclos aceitos (ppI,ppII,ppIII,CNOI)
fecham exatamente26.730968386MeV porDecimal. QcapturaBe7p=.136400064MeV;
QB8efetivo=18.07173726MeV. Meia-vidaB8NUBASEoriginal.7719s;wc12 disponível
separadamente. MédiaνB8=6.735MeV fixa por perfilSolar, sem espectro local.

Evidências científicas preservadas:

- is5-pp3-foundation-20261026a:8avaliaçõesdefits,4ciclosQ,131072gates,
  conservaçãoA/Z+léptons,2fixturesB8analíticos. ErroTtérmico8.48e−13rel.
- is5-pp3-mixed-20261026a:mistura prescrito/térmico contraBDFindependente
  com energiaU+inversãoEOS,refinamento e limiteppII comnovos2canaisoff.
  Maior erroBDFcomposição1.89e−15porbárion,T1.47e−13rel;limiteT1.07e−14rel.
- is5-pp3-competition-20261026a:Be7EC/protoncapture contraBDFindependente
  comH/Yevariáveis,erro3.50e−13porbárion;Jac13erro1.26e−9rel,6recusas.
  FraçãoEC.99831194 pertence somente àquelefixture, não é proporção universal.
- is5-pp3-science-20261026a agregaos3recibos com fontes/hash idênticos.
- is5-pp3-ledger-audit-20261027a:14Q ebalançosν/energia/e⁺/e⁻ de9datasets
  recalculados;refinamento térmico4.97e−15rel. Sem repetir integrações aceitas.

Worker is5-pp3-worker-artifact-20261027b ACEITO14recusas:sonda13/14,modos,
fonteSolararquivada,selos/recompute/save/load/newprocess,32ramos,locksWindows,
recusa tiposppII e arquivoscorrompidos semmutar oúltimoartefato. A parou
antes de executar porque faltava manifest;folder vazio preservado, B executou.

CEF is5-native-pp3-20261027a:4grupos/11recusas/zeroJS. ControleBe7p pelo
formulário mantémreferência,sondaB8/taxasecontagem,persistência/ramos/export,
fontearquivada sobreoutraórbita e limpeza passados. Revisão visual
is5-pp3-visual-review-20261027a aprova6PNG100/150 com21018pixels do marcador
cada,sondaB8 ecurva violeta com escala própria. O eixoB8não écomprimido
pela abundânciaBe7. MarcadorSolar tem dimensões/corgráficas,semcodificarT.

Perfil próprioB is5-pp3-zone-profile-20261027b ACEITO pelo auditor
is5-pp3-zone-profile-audit-20261027b:4janelas30swarm+60sSGCT/1920×1080,
2amostrascalculadas/s,weakon/off×gráficosvisíveis/ocultos.3264valores/24estados
conferidos poríndice,hashes/geração/fonte/RAM/GPU/UTC. Nenhum throughputODE.

| Medida | Pior resultadoB | Limite prévio |
| --- | ---: | ---: |
| Mediana | 13.340950ms | 16,7ms |
| p95 | 13.960800ms | 25ms |
| p99 | 14.376200ms | 50ms |
| Quadros>100ms | 0 | 0 |
| RAM produto | 1.202858GiB | 8GiB |
| GPU dedicada produto | 2.986755GiB | 5,5GiB |
| Ritmo medido/solicitado,mínimo | 0.964747 | ≥0,9 |

A executou4janelas mas falhou por1quadro de401,108712ms na janela4.
Causa não estabelecida nos logs. B repetiu as4janelas,sem reaproveitarA,
com MESMOS fontes/scripts/host/limites. Seus hashes e sessão foram conferidos
idênticos. A falhaA permanece em seu recibo e em is5-pp3-spike-20261027a;
B comprova a nova medição delimitada, sem apagar o pico ou garantir ausência
de travamentos em toda sessão futura. Contrato de reprodução preservado.


Fora do aceite: CNOII/III,pep/hep,screening/Coulomb,relatividade/pares,
ionização parcial,transporte/estrutura/hidrostática,luminosidade superficial,
fluxoespacial de neutrinos ou evoluçãoestelar calibrada. IS5/C2-20 continuam
parciais. Próximo recorte CNO-II contratado antes do modelo.
