# K5 — importação explícita e origem preservada

O próximo incremento de IS6 trata versões antigas em uma candidata nova.
Preservar 0.20.1, suas fontes e os arquivos originais. O aceite K4 continua
limitado a armazenamento, reinício e perfil próprio; não aceita migração.

K5A começa com a fundação CPU: importar envelopes compostos 0.1.0 e registros
K4 com envelope 0.2.0. Aceitar apenas as gerações conhecidas, com hashes
exatos dos validadores e geração espacial idêntica. O código importado nunca
é escolhido por um caminho contido no documento. Validar JSON estrito,
campos/tipos, checksums e ambas as referências por reconstrução completa.
Não atualizar hashes no documento para disfarçar uma geração desconhecida.

Cada conversão produz um pacote novo com o documento original, seu hash,
política/geração do conversor, checkpoint de destino e relatório das mudanças.
O digest científico, época, corpo, coordenadas SI, modelos, dados e duas
visibilidades devem permanecer exatamente iguais. Conferir novamente a
origem e o destino ao ler o pacote; recalcular apenas o checksum externo
não torna uma ciência adulterada válida. Não gravar durante a prévia.

Provas CPU antes do serviço: Terra/Júpiter × quatro visibilidades, ambas as
gerações; nova leitura em intérprete separado; JSON duplicado/não finito,
geração desconhecida, hashes adulterados, épocas/corpos/valores trocados,
campos extras e booleanos numéricos devem ser recusados. Arquivar as entradas,
saídas, fontes e recibos; registrar a preservação dos bytes de origem.

K5B acrescenta armazenamento com procedência dentro do mesmo registro
atômico, sem pares de arquivos que possam ficar incompletos. Importar cria
um ramo novo, sem substituir latest nem atribuir a ele um parentesco local
inexistente. Salvar, ramificar e exportar referências importadas conservam
sua procedência. Restaurar uma referência local limpa essa procedência.

K5C integra prévia/importação pela UI: escolher um arquivo JSON, mostrar
origem, corpo, época, modelos e mudanças; a ação explícita cria o ramo.
Cancelar a prévia não altera vista ou disco. Exigir guard atual e recusar
prévia obsoleta; alteração do arquivo após a prévia exige outra validação.
Restaurar o ramo continua usando a transação conjunta e cancelamento reais.
Testar reinício, falhas de escrita/validação, UI100/150%, limpeza, processos
e perfil próprio da candidata antes de qualquer promoção.

K5D tratará saves apenas espaciais como outra conversão, com escolha
explícita de uma nova amostra magnética. Ausência de amostra antiga não é
campo zero nem referência magnética arquivada. Preservar a vista espacial
original e declarar preferências que a vista composta não represente.
Essa etapa permanece pendente até contrato de entrada e provas próprios.

Este trabalho não amplia modelos físicos, não acopla as referências, não
aceita toda IS6/v1 e não transfere o perfil 0.20.1 para a candidata nova.
