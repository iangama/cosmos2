# Revisão F — inicialização explícita do provedor e preflight temporal

D20261113d permanece recusado: seu primeiro registro, ainda em prepare,
durou1,336167s. Todos os1070registros, ZIPs e recibos originais ficam
inalterados. As outras1069amostras duraram no máximo0,169475s. A análise
separada de quadros das dez janelas passou, mas não aceita o ensaioD.
O diagnóstico está em is6-expanded-residency-diagnosis-20261114d.json.

Um processo Windows novo reproduziu o custo em três observações diagnósticas:
1,343245s na primeira, dos quais1,272981s em discover_before; as duas
seguintes duraram0,070146s e0,065195s. A construção da query levou cerca
de1ms. Portanto o atraso observado está na primeira descoberta PDH,
sem evidência de travamento científico ou do renderizador. O diagnóstico
por estágio conserva os dados em is6-expanded-pdh-startup-20261114a.json.

Antes dos próximos dados, o coletor6/schema7 fará uma única inicialização
de descoberta, em prepare e antes de iniciar seu relógio1Hz. Essa operação
apenas enumera caminhos: não chama sample/CollectQueryData, não seleciona
uma observação bem-sucedida e não repete uma observação recusada. A Microsoft
documenta separadamente a [expansão de caminhos](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhexpandwildcardpathw)
e a [coleta dos valores](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhcollectquerydatawithtime).
O custo1,27s é medição local, não garantia da documentação.

O arquivo pdh-bootstrap.json conserva início/fim UTC, duração monotônica,
fase e cenário antes/depois, inventários, histórico nativo e caminhos
descobertos. A inicialização deve terminar em até10s, sem mudar fase ou
cenário e sem tomar gauges. O observador de processos permanece ativo
durante ela. Qualquer erro recusa; não há retry nem descarte de dados.
Ela não é amostra de residência nem transição de instrumento. O executor
só pode iniciar uma transição após os três registros prepare completos.

A série começa imediatamente após salvar a inicialização e continua do
índice0, sem filtro. Cada linha exige duração<1s, cadência0,5–1,5s e relógios
coerentes desde a primeira. Mantêm-se todos os critérios de GPU/RAM,
identidade, cenários, primeiros66registros, aquecimento, quadros e transições.
Auditor4 verifica a inicialização e todos os critérios anteriores. Preflight6
aplica os mesmos critérios temporais aos30registros, incluindo o primeiro;
o preflight anterior verificava bytes/identidades, mas não esses tempos.

Exigir fixtures de recusas temporais e de inicialização, fontes seladas,
preflight novo e plano novo antes de um ensaio integral. Não reaproveitar
nenhuma janelaD. Encerrar novamente com4handles/4códigoszero e restauração
do dono. Não promove candidata, não fechaIS6/K5A/V1 e não altera ciência0.27.
