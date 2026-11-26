# Perfil próprio da dinâmica16 — receita anterior à medida

Produto0.26.1, janela1920×1080, interface100%, cena de16massas pontuais.
Exigir jornada nativa100/150 e revisão direta das capturas antes de selar
o plano. Preservar cena/época/favoritos do dono; entrada inerte somente
durante aquecimento e coleta. Sem outros testes, backups ou downloads na medida.

Quatro janelas independentes: sistema completo pausado; sistema completo
em0,1unidade/s; Terra em1unidade/s; Titã em10unidades/s. Todas começam de
cópia16nova na mesma época confirmada. Na janela dinâmica, evoluir1segundo
para preparar o solver, pausar, aquecer a cena30segundos, retomar e coletar.
Os60segundos de quadros ficam dentro de66amostrasPDH a1Hz. O relógio segue
durante a coletaGPU e para antes de preparar a janela seguinte. Registrar
a duração física total e conferir que fica abaixo de30dias em cada janela.

Limites anteriores conservados: mediana≤16,7ms, P95≤25ms, P99≤50ms,
zero intervalos>100ms; RAM≤8GiB e somaWDDM dedicada+compartilhada≤5,5GiB.
Taxa física medida≥90% da solicitada nas janelas dinâmicas. Quatro amostras
de RAM/fase/contexto em0/20/40/60segundos; rastreio interno do motor e
intervalos brutos preservados. Nenhum controle de fonte/campo muda na coleta.

A coletaPDH pausada anterior exigia igualdade do cenário incluindo o tempo.
Para a dinâmica, criar coletor e auditores próprios, preservando os anteriores.
Modo, estado de pausa, taxa solicitada, revisão, população e confirmação do
renderer permanecem estáveis. Somente physical_time pode avançar; deve ser
finito, não negativo e estritamente crescente entre amostras1Hz quando em
movimento. Pausado exige tempo idêntico. Conservar bytesPDH, status, caminhos,
identidades dos processos e prova temporal de parentesco exatamente sob os
mesmos critérios. Testar esse adaptador separadamente antes de medir.

Selar todas as fontes/entradas/receita antes da coleta. Manter quatro handles
reais, fechar com quatro códigoszero, auditar em processo separado e reabrir
com a vista inicial. O resultado não herda perfis estáticos/compostos0.25.1,
não aceitaK5Aoriginal e não fechaIS6ou aV1.
