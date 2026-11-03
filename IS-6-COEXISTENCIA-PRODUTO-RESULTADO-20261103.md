# K3 — controles coordenados na candidata 0.19.1

A jornada funcional e a revisão de seis capturas foram aceitas na candidata
0.19.1. O menu Camadas seleciona Terra/IGRF14 ou Júpiter/JRM33, abre as duas
referências e permite esconder cada uma sem alterar a ciência ou a órbita.
Leituras e legendas mantêm B em tesla, curvatura em m⁻⁴, posições em metros,
referenciais e época. A saída restaura câmera e flags.

Foram verificadas oito combinações de visibilidade, posições científicas,
14 recusas de conflito com as APIs anteriores e cancelamento HTTP real
durante preparação. O cancelamento retornou após a limpeza e a criação
cancelada não publicou artefato. Sem erros JS; app/servidor saíram0/0 e a
auditoria confirmou ausência dos PIDs e sessão do dono preservada.

A 0.19.0 mantém seu aceite funcional separado. Suas imagens revelaram que
a razão do relógio terrestre arredondava para1; a 0.19.1 acrescenta o déficit
já calculado, alterando somente um JS. As seis imagens incluem os dois
painéis magnéticos rolados em150%, com B e coordenadas legíveis, sem barra
horizontal e com a saída sempre visível. Todos os hashes/pixels RGB conferidos.

Recibos: evidence/is6-layers-native-20261103b.json,
is6-layers-visual-20261103b.json e is6-layers-native-process-20261103b.json.
Fontes, candidatas e execuções A/B permanecem congeladas. O perfil próprio
da interface está contratado em IS-6-COEXISTENCIA-PERFIL-K3-CONTRATO.md,
mas ainda não foi implementado/executado; o perfil K2 não foi transferido.

Fundação K4 CPU aceita em is6-layers-checkpoint-20261103a.json: oito
round-trips de dois corpos/quatro visibilidades e32recusas, inclusive
alterações com checksum recalculado. Recalcula espaço, B e admissão antes
de restaurar. É somente um envelope CPU: gravação atômica, serviço/UI de
salvar/restaurar/ramos, reinício e migração composta continuam pendentes.

Nada promovido sobre3.13. K3/K4 não encerram IS6/v1 ou um novo marco completo.
