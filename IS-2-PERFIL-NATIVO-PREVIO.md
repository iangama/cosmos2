# IS-2 — perfil próprio da candidata de quatro centros

Receita anterior à captura: três execuções com aquecimento de30s e janela
de60s cada,1920×1080,CEF real100%,IAS15epsilon10⁻⁹,ritmo canônico1.
Em cada janela,20s de visão geral,20sTerra/Lua e20sJúpiter, usando os
controles reais da candidata. A leitura por fonte é calculada antes de
evoluir e fica corretamente marcada como amostra fixa. Nenhuma camadaEM,
mapa3D ou bancada nuclear entra nesse perfil. Registrar as três janelas e
as três partes sem escolher os melhores trechos.

Limites herdados dos perfis gravitacionais: mediana≤16,7ms,p95≤25ms,
p99≤50ms,nenhum intervalo>100ms; ritmo medido≥0,9unidade/s;RAM somada dos
processos próprios≤8GiB;memóriaGPU dedicada somada≤5,5GiB e abaixo do
orçamentoDXGI da placa física do motor. Toda janela exige66amostrasWDDM,
sem erros de contador e cobrindo começo/fim da captura. Os somatórios podem
contar páginas/alocações compartilhadas mais de uma vez; preservar essa
limitação. Não atribuir memória de outros aplicativos ao produto.

Fixar hashes e arquivar fontes antes da execução. Guardar snapshots das
quatro identidades10/399/301/599,intervalosSGCT brutos,tempos,PID/enginehash,
RAM e recibosGPU. Verificar energia/momento/angular≤10⁻⁸ durante o perfil,
sem tratar isso como substituto da auditoria numérica de30dias. O perfil é
próprio dessa cena e não substituiG0,C2-12/J ou a integração das quatro forças.
Auditar os dados preservados antes de dar aceite. Se houver falha de coleta,
guardar a captura parcial e o diagnóstico; não executar repetição cega.
