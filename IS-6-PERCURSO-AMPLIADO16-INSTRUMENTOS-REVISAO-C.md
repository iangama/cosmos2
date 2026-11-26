# Revisão C — cápsula da fase pausada

O ensaio B consultou corretamente a leitura magnética pelo worker real,
mas parou na igualdade de todo o envelope publicado. Cada comando do worker
renova sequence e history_evaluation_ms, mesmo quando nenhuma grandeza
física ou identidade muda. A asserção comparou esses metadados de publicação
com o envelope anterior. Isso não demonstra mudança de fase orbital.

O adaptador de status passa a fornecer uma cópia fixa do snapshot real
inicial, para que cada artefato científico retenha a mesma cápsula de origem.
Antes de cada retorno do adaptador, exigir igualdade exata entre o worker
real atual e essa cápsula em todos os campos físicos já fixados: IDs,token,
revisão,tempo,corpos,origem,intervenções,metadados16,pausa,contrato e unidades.
Nenhum dado científico é substituído. A leitura magnética completa continua
vindo do worker real e seus campos continuam comparados exatamente.

A recusa intencional de fonte16 usa somente um adaptador negativo separado;
nunca troca o snapshot corrente do worker real. Preservar A/B e executar C
em namespace novo. Nenhuma fonte,limite ou regra do produto muda.
