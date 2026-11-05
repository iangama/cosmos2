# PDH — FILETIME local preservado, conversão nativa para UTC

A primeira coletaA expôs os contadores corretos e bytes brutos/formatados iguais,
mas foi recusada: o auxiliar tratou FILETIME local como UTC. O retorno e todos os
timestamps brutos coincidiram entre si e ficaram exatamente3h antes do relógio
UTC da chamada. A documentação da [estrutura bruta](https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_raw_counter)
identifica o timestamp como local. O reciboA permanece recusado e não comprova GPU.

A revisão nova mantém query_filetime e timestamps brutos intactos; usa
[LocalFileTimeToFileTime](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-localfiletimetofiletime)
para obter query_utc_filetime. Registra a base temporal e o deslocamento real
retornado, sem subtrair3h por constante nem afrouxar a tolerância da chamada.
O UTC convertido deve estar entre o início/fim reais, tolerância100ms, e o auditor
reconstrói ambos os FILETIMEs e suas diferenças. Não usar o campoUTC equivocado deA.

A conversão usa as regras atuais do Windows. Esta coleta é de tempo real e deve
manter fuso estável durante o intervalo; não se aplica a arquivos históricos ou
transições de fuso/DST sem outra prova. Fonte oficial e API preservadas no recibo;
v1 fica congelada, v2 tem nova geração e precisa de coleta/auditoria próprias.
