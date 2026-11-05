# IS6 — coletor Windows PDH em Python, antes de novos perfis

Coletor novo e somente leitura. Não executar ou empacotar PowerShell, retomar
threads suspensas ou alterar políticas. O lançador Python já validado pode abrir
um host próprio para a prova do coletor. Preservar todos os coletores/perfis antigos.

Usar PdhAddEnglishCounter para resolver nomes neutros, obter o caminho localizado
e expandir instâncias antes de escolher os contadores. Só adicionar à consulta de
amostragem os pares Dedicated/Shared dos processos próprios e Dedicated dos
adaptadores, identificados separadamente como uso de todas as aplicações.
O procedimento segue a [documentação Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcounterw).

Cada leitura registra retorno da API, CStatus, tipo, valor bruto First/SecondValue,
MultiCount, timestamp bruto e valor inteiro formatado sem escala. Os contadores
adotados devem ser gauges64 de bytes; valor formatado deve coincidir com o bruto,
sem converter falha em zero. Falta, tipo incompatível, erro, valor negativo ou
troca de instância invalida a captura inteira. Os estados0(VALID_DATA) e1(NEW_DATA)
são sucessos documentados; preservar o estado efetivo, sem reescrevê-lo como0.
Referências: [status](https://learn.microsoft.com/en-us/windows/win32/perfctrs/checking-pdh-interface-return-values),
[dado bruto](https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_raw_counter),
[formatação](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue).

Congelar a árvore própria a partir do motor/servidor, mantendo PID, parentesco,
nome, instante de criação e caminho. Processo sem contador exposto deve ser
listado como tal, nunca receber zero. Guardar inventários próprios antes/depois;
novo filho, saída ou reuso de PID recusam a coleta. Não serializar nomes de
processos alheios ao produto. Confirmar geração/executável, sessão e cenário.

Schema4 separa esta prova do antigo schema3 PowerShell. Auditor novo, independente,
reconstrói caminhos, pares, somas e cobertura temporal a partir das amostras brutas.
Soma dedicada+compartilhada é uma contagem WDDM por processo, pode duplicar
alocações compartilhadas e não significa ocupação física única da placa.

Antes de qualquer perfil: prova nativa curta com motor/CEF próprios, leitura real,
recusas de dados adulterados, reabertura do recibo em outro intérprete, limpeza e
fontes intactas. Provar o coletor não aceita desempenho. Só então congelar o plano
de perfil0.22.1 para a referência importada solar1–8Rref65×96 efetiva, sem derivar
ou alegar257anéis, medir startup/importação ou herdar perfil de outra candidata.
