# Residência do percurso 0.27.0 — preparação anterior à coleta

Este contrato inicia a próxima etapa;nenhum coletor,executor ou auditor
novo está pronto para execução. Exigir antes da coleta os aceites de
serviçoC,primeira jornada,recuperação de ciclo,reabertura e34PNG revistos.
Conservar os18arquivos originais de checkpoint/ramos/exportações por SHA.

Preparar dez janelas na mesma aplicação0.27.0/1920×1080/UI100%:
Atlas/Terra,cópia16/sistema,malhaTerra,parTerra,próton pausado256passos,
malhaJúpiter,parJúpiter,elétron pausado256passos,zona solar arquivada no
nó120 e retorno16/Titã. Uma única fase4 pausada serve aos instrumentos;
fonte16 e cada fonte arquivada conservam seu próprio guard e referência.
Usar somente as configs efetivamente aceitas e salvas pela jornada.

Cada janela tem30s de aquecimento+60s de quadros brutos completos,cobertos
por66amostrasPDH a1Hz,com preflight3 e identificação temporal dos processos.
Manter limites existentes:mediana≤16,7ms,p95≤25ms,p99≤50ms,zero>100ms,
RAM≤8GiB,WDDM dedicada+compartilhada≤5,5GiB. Somar somente processos
próprios,registrar nascimento/saída dos workers e conservar rastreio
interno completo. Esses estados pausados não medem throughput científico.

Registrar também todas as transições e seus contextos antes/depois,
latência,picos de memória,identidades e ausência de nós/callbacks antigos.
Os comandos gerais mantêm orçamento70s e operações solares750s de jornada,
600s de cálculo/660s de transporte. São orçamentos herdados de conclusão;
não aplicar artificialmente limite de visibilidade1s a um recálculo nuclear.
O rastreio deve distinguir explicitamente transição,cálculo e janela estável;
nenhum desses intervalos pode desaparecer da evidência bruta.

Antes de executar:implementar contrato de identidade de processos variáveis,
coletor,executor,driver destacado,auditor separado e regressões offline
de recusas pertinentes. Selar suas versões,inputs,configs e fontes antes
dos dados novos. Não inventar tratamento de intervalos após medir;
revisões exigem diagnóstico e preservação do ensaio original.

Durante a coleta,não navegar,fazerbackup,downloads ou testes pesados.
Encerrar com quatro handles e quatro saídaszero,reabrir a vista do dono e
validar18arquivos byteidênticos. Esta etapa não substitui K5A,não admite
campos/forte/fraca nos16 e não fechaIS6 ouV1 sozinha.
