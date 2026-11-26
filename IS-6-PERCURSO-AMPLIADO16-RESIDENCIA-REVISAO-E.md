# Revisão E — compartilhamento dos arquivos de controle no Windows

C20261113c ficou recusado por PermissionError ao abrir collector-status.json
durante uma substituição atômica. Coletor4 encerrou válido com187amostras;
histórico nativo10processos/6386polls,maior intervalo0,1132s. Controlador
encerrou4handles/códigoszero e restaurou o dono. Todos os originais ficam
inalterados, incluindo a captura parcial16. Nenhum dado é reaproveitado
como janela do próximo ensaio.

Leitor novo abre controle/status com compartilhamento de leitura, escrita
e exclusão, compatível com a troca atômica. [CreateFileW, Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
documenta a compatibilidade dos modos de compartilhamento com renomeação.
Só tentativas de abrir esses arquivos IPC podem aguardar até1s em erros
transitórios de nome/compartilhamento. JSON comprometido, leitura incompleta
ou tamanho acima16MiB recusam imediatamente. O limite admite as cápsulas
de cenário científico/traçados presentes no controle de fase.

Não aplicar essa rotina a snapshots de processos, PDH, RAM ou JSONL de
amostras. Nenhuma amostra é descartada ou repetida. O motor continua
capturando quadros enquanto o controlador aguarda IPC; atrasos integram
o intervalo bruto e seus limites vigentes. A fixture deve substituir o
arquivo1000vezes enquanto o leitor verifica integridade/ordem, conferir
controle grande UTF8 e recusar JSON malformado. Depois preparar fonte/ZIP,
preflight próprio e plano novo antes de qualquer repetição integral.
