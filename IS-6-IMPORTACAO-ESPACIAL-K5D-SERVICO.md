# K5D — corte de serviço após o armazenamento CPU

Este documento especifica o próximo corte, sem declarar execução ou aceite.
Só integrar depois do recibo aceito do armazenamento espacial schema2. Conservar
a fundação A, o módulo de armazenamento executado e as candidatas0.18/0.21.
O serviço novo será preparado no staging espacial; a candidata nativa terá
diretório próprio e não substituirá o atalho principal ou a versão3.13.

O serviço serial usa Reference para transportar artefato, vista, origem e
parentesco. Prévia recebe o texto original estrito e produz resumo, ID efêmero
e guard da vista. Não grava arquivo, não abre instrumento e não chama o motor.
Cancelar consome somente a prévia identificada. Confirmar verifica o mesmo
guard, ID e texto, grava ramo local novo sem pai e consome a prévia somente após
commit atômico. Falha conserva prévia, vista confirmada e todos os arquivos
confirmados. Repetições de confirmação e guards obsoletos são recusados.

O catálogo identifica a procedência espacial e a vista original. A confirmação
nunca transforma a entrada solar em par composto ou cria magnetismo. Um arquivo
espacial escolhido no instrumento composto deve receber encaminhamento explícito
para Malha espacial, com explicação curta do formato e sem amostragem implícita.

Restaurar um ramo deve funcionar tanto com a malha fechada como aberta. A ação
exige guard do serviço e source_guard da cópia solar viva atual. Validar a fase
viva pausada de quatro corpos antes de abrir qualquer candidata. A fase arquivada
permanece no artefato, nos cálculos e na posição SI do corte; camera/flags pertencem
à cópia viva. IDs arquivados nunca selecionam nós da cena atual. Reabrir o host com
novos IDs vivos não invalida a ciência arquivada nem altera seus bytes.

Preparar, cancelar, confirmar e limpar seguem o protocolo nativo já provado:
candidata oculta, cancelamento antes do commit, troca em uma transação, leitura
de volta antes de publicar e conservação da vista anterior em falha. Guardar,
criar filho e exportar transportam a mesma Reference/cápsula, incluindo a vista
original, mesmo quando as sondas e a visibilidade atuais mudam. Recalcular uma
importada para outra configuração é outra derivação; esta fatia não a oferece.

A prova CPU do ator usa modelos e armazenamento reais, sem simular sucesso do
motor. Exercita as seis entradas A, prévia/cancelamento/confirmação, falhas I/O,
guards obsoletos, repetição e zero chamadas nativas. O proprietário de cena tem
prova separada para distinguir fase científica e contexto vivo. Depois vêm
HTTP/UI, restauração nativa a100/150%, reinício, cancelamento real, processos e
perfil próprio. Cada corte registra suas fontes e limita explicitamente o aceite.
