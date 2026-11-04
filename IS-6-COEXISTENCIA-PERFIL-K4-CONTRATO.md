# K4 — perfil próprio da candidata com armazenamento 0.20.0

Pré-requisitos: jornadas de salvar/restaurar/ramos/exportar e reinício,
capturas revistas e processos encerrados normalmente. Mesmas quatro janelas
e limites K3:30s aquecimento+60s medidos,1920×1080/UI100%,Terra/Júpiter
estáticos e quatro visibilidades a2Hz. Criar os pares pela UI e emitir120
set_visibility pela API em cada janela ativa, mantendo a UI real renderizada.

Adotar exatamente os modelos/pontos e a malha65×96,1–3Rref,XY,ampliação200
já contratados. Exigir240confirmações totais,p95≤0,5s,máximo≤1s e≥90%
dentro dos60s;mediana de quadro≤16,7ms,p95≤25ms,p99≤50ms,zero>100ms,
RAM≤8GiB,GPUdedicada+compartilhada≤5,5GiB. Mesmos quadros brutos e66
amostrasGPU schema3 válidas abrangendo cada janela,sem descartar erros.

Esta coleta usa armazenamento existente:latest disponível,ao menos três
ramos e exportações das jornadas nativas. A UI consulta catálogo/disponibilidade,
mas não grava durante a medição. Arquivar os registros antes da coleta e
exigir hashes e conjunto de arquivos exatamente iguais ao terminar.
Não usar arquivos vivos mutáveis como fonte histórica: guardar cópias seladas
na pasta do perfil e ZIP. Auditor valida também os registros arquivados.

Conferir revisão estável ao redor dos flags nativos nos segundos0/20/40/60,
fase,câmera,modelos/artefatos,UI/errosJS,receitas/ZIP e limpeza/restauração.
Auditar saída0/0 e ausência de PIDs. O resultado é perfil de renderização e
API de visibilidade com catálogo existente; não é throughput de gravação,
migração implícita de formatos antigos ou aceite de todaIS6/v1.
