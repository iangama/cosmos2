# C2-12 — taxa da nuvem na retomada de 21/10

O instalado 3.13, as sessões do dono e os núcleos da candidata F permanecem
preservados. Este registro trata a falha de desempenho como falha, sem
alterar o limite mínimo de 0,9 s/s para ritmo solicitado de 1 s/s.

- A tentativa c212timesrca terminou antes de iniciar a captura de quadros:
  o sinal de prontidão existia, mas o Windows ainda mantinha seu arquivo
  bloqueado. Fontes e dados foram congelados em archive próprio. O runner
  agora aguarda leitura completa dentro do mesmo prazo de 15 s e encerra
  o coletor se a inicialização falhar. Não houve alteração em F.
- c212timesrcb completou as três rotas e foi **reprovado**: a segunda rota
  mediu 0,843525526 s/s. Quadros, recursos, energia e referência DOP853
  passaram. O último estado retido dessa rota informou compute_ms=73,6747,
  contra cerca de 1,4–2,6 ms nas marcas anteriores. Não havia telemetria de
  CPU nessa captura para atribuir a causa a um processo ou ao escalonamento.
- Dois diagnósticos posteriores de 45 s, com a mesma configuração de fontes
  e camadas da segunda rota, terminaram perto de 1 s/s. O primeiro consultou
  o shim Python do venv e seu campo de CPU do worker não é representativo;
  fonte executada preservada em output/em-cloud-live-rate-afterb1-source.py.
  O segundo soma os descendentes reais: o worker usou aproximadamente
  7,3–7,9 processadores lógicos. Houve carga alta do sistema. Isso mede as
  janelas posteriores, não explica retrospectivamente a falha B.
- O diagnóstico isolado ensaiou 256 passos com 8/6/4/2/1/1/2/4/6/8 threads.
  Todos os endpoints e trabalhos foram byte a byte iguais. As oito threads
  foram as mais rápidas nas duas passagens; reduzi-las não fornece margem
  suficiente. Nenhuma configuração do produto foi alterada por esse teste.
- Após fechamento normal e processos novos, c212timesrcc e seu auditor
  passaram: taxas 0,999968/1,000245/0,999177; p95 máximo 18,114220 ms,
  p99 18,842838 ms, vinte pausas ≤107,082 ms; RAM 1,21350 GiB,
  WDDM 2,96426 GiB < orçamento DXGI 7,19014 GiB. A referência DOP853
  independente deu erro de posição/velocidade ≤3,487e-5 e energia ≤1,106e-11.
  O runner agora retém tempos brutos de CPU do sistema e dos processos do
  produto no início, nas três marcas e no fim, sem mudar os critérios.
- c212timesrcd e seu auditor também passaram no mesmo processo, depois da
  auditoria C, como repetição adicional previamente anunciada: taxas
  0,998182/1,000592/1,000567; p95 máximo 18,044091 ms, vinte pausas
  ≤110,841 ms. Erro DOP853 ≤3,473e-5 e energia ≤1,241e-11. As duas
  capturas completas consecutivas não reproduziram a falha B.

Os JSONs, auditorias e fontes congeladas ficam em evidence/. A causa exata
da falha B continua indeterminada; ela não será reclassificada se as outras
capturas passaram. F foi congelada com C e D aprovados, preservando a rejeição
e os diagnósticos, em c212-em-time-candidate-20261021.tar.gz, SHA
2f2ec09945d4e0fefd104a5b97d9dfcb6291e2af2a2428c29844b93e51ede6fd.
Não constitui promoção, garantia
contra pausas de escalonamento ou aceite completo do C2-12.
