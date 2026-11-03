# IS5 — trabalhador Coulomb, resultado29/10UTC(28/10local)

**Aceito o trabalhador V2**, recibo
`evidence/is5-coulomb-worker-artifact-20261029b.json`: oito grupos e17
recusas, sem alterar a ciência aceita. Fontes e teste exatos estão arquivados
em `output/is5-coulomb-worker-artifact-20261029b/executed-sources.zip`.
Preservar `output/is5-coulomb-worker-v2-staging` e o roteiroV2.

Passaram processo real, cenário/referência completos,16espécies/18canais,
U_Coulomb e fatores de screening, modos e controles separados, restauração
exata em processo novo, selos/tipos antigos/corrupção, ramos/exportação,
locks transitório e permanente do Windows, e limite de32ramos.

Durante cálculo, state respondeu em0,112s. Criação padrãoO16 levou44,259s;
isso é tempo de cálculo, não desempenho de quadros. Prazo reduzido produziu
erro em0,418s, com artefato/preferências/token/revisão preservados e sem
publicação tardia. Quit durante cálculo encerrou em0,081s. A morte abrupta
do responsável também encerrou o filho. Inicialização com32ramos:3,823s.

## A reprovação A foi preservada

A tentativaA excedeu240s e não recebeu aceite. A observação dos processos
confirmou a camada lançador venv→Python real. Uma reprodução diagnóstica
sem thread Python de vigilância concluiu o cálculo em cerca de40–50s;
isso não estabelece isoladamente a causa completa da falhaA. A execução
instrumentada com faulthandler apresentou access violation e não é evidência
de precisão científica.

V2 inicia o interpretador real com `-S` e somente os pacotes do ambiente
científico fixado, conferindo a mesma geração. O Job Object Windows com
KILL_ON_JOB_CLOSE assegura a propriedade do filho; seu PID deve ser o PID
real de Popen. Nenhuma thread Python vigia o cálculo. A guarda de geração
recusou a combinação indevida de bibliotecas do Python base no smoke
anterior a `-S`; não foi ignorada.

Próximo: candidata0.15.0 isolada da0.14.0, com CEF/visual/perfil próprios.
O aceite acima não aprova a interface, os quadros ou o produto instalado.
