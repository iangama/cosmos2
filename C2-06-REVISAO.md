14/10: revisão encerrada pelo aceite local em [C2-06-DECISAO.md](C2-06-DECISAO.md).
A matriz abaixo é o histórico anterior à conclusão do G0g0async4.

# C2-06 — revisão do editor gravitacional

14/10/2026. **Ainda sem decisão completa de aprovação.**
Motor final OpenSpace0.22 EXEcfcd7fff…3eb218d6, geração científica3.4.0,
REBOUND5.2.2/IAS15epsilon1e-9, Windows/RX7600/1080p/CEF nativo.

| Requisito | Evidência concluída | Pendência |
| --- | --- | --- |
| SI massa/fase e1–128massas/IDs estáveis | body-editor/registry-check +quatro jornadas nativas; guards e intervenções M/E/P/L | Nenhuma funcional conhecida |
| Raio/spin | atributos +UI no motor final; quaternion contraSciPy/continuidade/origem/SI | Sem torque/J2/energia interna por contrato |
| Cônicas/COM/escape e antes/proposta | orbital-diagnostics/session-orbits/orbit-editor-ui/edge-ui; CSPICE/REBOUND, prévia somente leitura | Não são trajetórias N-corpos futuras |
| Órbitas/conservação | editor-long-orbits-check,100períodos e0/0,6; <=3,681mm contraCSPICE | Nenhuma no domínio medido |
| Cópia real | Atlas/registry-ui preservam fonte/época/GM e relógio independente | Apenas Sol/Terra/Lua nesta cópia |
| Encontro/captura/ejeção | três modelos locais, DOP853/IAS15, horizonte/reset/checkpoint nativos | Classificação finita, sem garantia eterna |
| Sonda básica | analítico/−gradΦ,128fontes e edge-ui sem mutação | Rede/persistência/campo completo são C2-11 |
| Precisão/pausa/memória/FPS P128 | c206p128c +review no EXEfinal:3×60s/30s,20pausas | Perfil passou; G0não é substituído |
| Visual do editor | Dez capturas atuais revistas localmente, SHAem editor-visual-review.json | Não equivale a opinião estética do dono |
| Correção do log e regressão do motor | contrato Windows/Linux, diagnóstico120s/churn, UTF8/ordem/drain/shutdown e cinco jornadas passaram | Falta G0formal completo, labelg0async3 ativo |

P128c206p128c passou/auditou com fonte própria congelada:128massas positivas,
ativas, pedido1/efetivo>=0,9995616u/s. Erel<=5,34e-15/Pnorm<=5,69e-17/Lnorm0
nos estados registrados. p95máx23,405ms/p99máx24,600ms, zero>100ms.20pausas
API<=36,282ms, câmera<=24,684ms. Somaresidente1,06362GiB, somaWDDMdedicada
2,99042GiB, orçamentoDXGI>=7,19014GiB.66amostras por rota/coberturaUTC/SHA.
A somaWDDM pode repetir alocações compartilhadas; não representa VRAMúnica.
O inverso da mediana de intervalos não representa a taxa média de apresentação.

As tentativas anteriores permanecem: P128c206p128b passou no EXEc308;
G0g0labels reprovou8hitches até1057,719ms no mesmo motor. Diagnóstico detalhado
localizou155,808ms no log síncrono dentro de um quadro170,386ms. AsyncScriptLog
remove esseIO da threadgráfica, mantém ordem e informa perda/erro explicitamente.
DIAGNOSTICO-QUADROS.md reúne causa, intervenção e provas dirigidas.

G0g0async foi interrompido pelo pedido temporário de não usar janelas após
4rotas completas. O dono posteriormente liberou o acesso completo. G0g0async2
parou por CounterApiError de memóriaGPU na terceira rotaAtlas; duas anteriores
completas/semhitches, perfil inválido por faltar memória. Não é aceite parcial
nem falha de frame demonstrada. Os caminhos/status daquele evento não foram
emitidos pelo coletor antigo, portanto sua origem exata não foi determinada.

Coletor reforçado passou leitura real3amostras e contrato sintético de erro:
preserva todas as amostras/caminhos/status e RECUSA qualquer erro/inválido.
Não ignora processos externos nem substitui valores. Auditor também confere
counter_errors vazio quando presente. G0g0async3 é a nova coleta completa;
não alterar fontes nem cena enquanto roda. P128c foi medido com versão anterior
do coletor, mesmo motor/app; sua fonte congelada permite auditoria histórica.

Sem colisões/fusão/torques/J2/energia interna neste marco. Raio/spin são
geométrico/cinemático, balanços são translacionais. Fronteira singular1mm
pausa/recusa, sem resposta de contato. Gráficosfloat32 têm bound separado dos
valoresfloat64. Sonda básica não é persistida. Restam21marcos/15da v1 até
registrar uma decisão completaC2-06; C2-11staging não altera esse estado.
