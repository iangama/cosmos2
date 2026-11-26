# K4 — persistência de duas referências independentes

Fundação CPU em módulo próprio, sem alterar as fontes K3 executadas.
Primeiro definir um envelope para a referência espacial, a leitura magnética,
o plano de admissão e as duas visibilidades. O digest científico independe
da visibilidade; o digest do checkpoint cobre ambos. Tipo e versão próprios;
não reinterpretar checkpoints espaciais antigos como compostos.

Na restauração, recalcular o artefato espacial e o campo magnético com a
mesma fase arquivada, corpo, época, centro, orientação, dados e geração.
Recalcular a admissão; recusar divergência em qualquer item antes de chamar
o motor. Exigir duas visibilidades booleanas explícitas e finitude, sem
campos extras. Arquivo inválido não altera a vista ou o checkpoint anterior.

Persistir geração das fontes, digests, corpo, unidades e procedência originais;
parentesco e nomes de ramos em invólucro próprio. Gravação temporária e troca
atômica somente após validação, em diretório da candidata; exportação conserva
o mesmo envelope. O serviço serial coordena load/save/ramo com o proprietário
comum; trocar uma referência exige preparar as duas ocultas e commit conjunto.

Provas CPU de round-trip e corrupção com os modelos reais precedem a UI.
Depois: salvar, fechar, reiniciar processo, restaurar cada visibilidade,
ramificar, exportar, arquivo inválido/geração antiga, recusa sem mutação,
cancelamento e limpeza. Conferir capturas, fontes congeladas e perfil se o
trabalho de persistência alterar o caminho medido. Fundação CPU não aceita
save de produto, migração, cena ou toda IS6/v1.
