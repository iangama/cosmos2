# C2-14 — representação e testemunhas do perfil

Complemento fixado antes dos dados. Os limites do contrato permanecem.

As respostas HTTP brutas são arquivadas uma vez por SHA-256 do corpo exato,
com tamanho e referência em cada amostra. Isso é deduplicação sem perda: a
auditoria reabre cada corpo, verifica seu hash e reproduz as projeções por
job, configuração, resultado e instante. Respostas diferentes geram objetos
diferentes; nenhuma transição é descartada. O JSONL continua contendo todos
os gauges, testemunhas nativas de RAM, inventários, histórico e leitura CEF.

Um observador requestAnimationFrame do controlador conta avanços e reinicia
a reprodução pelo botão existente ao fim da trajetória. Não altera física,
draw ou temporização do produto. Seu código fica arquivado com a receita;
seu custo está incluído no perfil. Exigir pelo menos mil avanços e quatro
voltas completas por janela de 60 s, relógio CEF compatível e vista visível.
Conferir configuração e leituras atuais em cada amostra estável, não apenas
um atributo de modo Atlas. Documento oculto, gráfico fora da vista ou job
divergente recusam o ensaio.

O capturador nativo inclui um intervalo que atravessa a abertura da janela;
excluir exatamente esse primeiro intervalo nas janelas estáveis. Nenhum
outro intervalo é filtrado. A soma dos intervalos úteis e o tempo de parede
devem ficar em 60±0,5 s, com mais de mil intervalos. Essa exigência é mais
estrita que a cobertura mínima de 90% do contrato. Três amostras completas
antecedem a captura; as primeiras 66 do controle estável devem cobrir seu
encerramento. Aquecimento tem 30 s e também é capturado sem corte inicial.

O limite de GPU aplica-se à soma dedicada própria indicada no contrato;
registrar também a soma dedicada+compartilhada e seus limites de atribuição.
Ausência de contador exposto não significa consumo zero. Contadores de
adaptador ficam como contexto e não substituem o escopo próprio.
