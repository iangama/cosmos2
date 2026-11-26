# K5D — arquivos espaciais anteriores, sem inventar outra referência

Etapa posterior à consolidação K5 da importação composta. Preservar fontes,
arquivos e aceites da 0.21; usar nova candidata para a integração espacial.

O saved.json real da 0.18.2 contém uma malha solar, NAIF10, planoXY65×96,
exterior1–8Rref e ampliação200. A vista seleciona índices radial16 e azimutal95,
com referência radial0. Não há modelo magnético interno solar adotado nessa
vista. O arquivo não pode virar um par composto por renomeação, campo zero
ou amostra magnética implícita. Na UI composta, indicar o formato espacial
e encaminhar explicitamente ao instrumento Malha espacial.

A primeira fatia de compatibilidade importa a referência apenas espacial
no instrumento correspondente. Validar JSON estrito, campos, checksums,
geração conhecida e reconstruir o artefato e a vista. Preservar a fase,
corpo, configuração, índices selecionados, visibilidade, valores e bytes
originais. Parent IDs antigos permanecem na procedência; o novo ramo local
começa sem pai. Origem e destino ficam dentro do mesmo registro atômico.

Prévia não grava nem altera a cena. A confirmação cria um ramo novo; uma
ação explícita restaura esse ramo usando a cópia orbital viva atual para
câmera/flags e a fase arquivada para a ciência. A interface deve permitir
restaurar o ramo a partir do instrumento fechado, com source_guard atual,
e durante uma vista aberta. Guard obsoleto ou falha mantém a vista confirmada.

Provas CPU antes de integrar: formato real saved/branch/export, corrupção
com checksums recalculados, geração/corpo/época/vista adulterados, campos
extras, JSON duplicado/não finito, escrita interrompida, novo intérprete e
originais intactos. Depois, UI nativa100/150%, guardar/filho/exportar com
procedência, reinício com novos IDs vivos, cancelamento real, limpeza,
processos e perfil próprio da candidata com a malha1–8Rref efetiva.

Converter um arquivo espacial terrestre ou joviano para um par composto
será outra ação, exigindo uma amostra magnética explícita. Se mudar1–8 para
1–3Rref ou qualquer configuração de desenho, declarar a nova derivação e
conservar o artefato original; não alegar digest científico idêntico. Essa
conversão adicional e a integração descrita acima ainda não foram executadas.
