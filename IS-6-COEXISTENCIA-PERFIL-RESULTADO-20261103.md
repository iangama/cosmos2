# K2 — perfil de referências simultâneas

O perfil do protótipo K1C na candidata isolada 0.18.5 foi aceito nas quatro
janelas: Terra/Júpiter com ambas as camadas estáticas e com as quatro
combinações de visibilidade a 2 Hz. Cada janela teve 30 s de aquecimento e
60 s medidos em 1920×1080, UI 100%, fonte orbital pausada, malha 65×96
de 1–3 Rref e ampliação 200; IGRF14 e JRM33 grau 13 independentes.

Foram auditados 18037 deltas válidos. O p95 máximo foi 14.009 ms e o p99
máximo 14.363 ms, sem quadros acima de 100 ms. Os 240 comandos de
visibilidade concluíram dentro da janela, p95 máximo 0.107 s e máximo
absoluto 0.212 s. Pico RAM do produto 1.065 GiB; GPU dedicada+compartilhada
2.992 GiB, com as ressalvas de possível dupla contagem já declaradas.

O auditor conferiu os modelos recalculados, fase e artefatos, posições SI,
limites gráficos, arquivos e rotações nativas, visibilidades, deltas brutos,
receitas, ZIP e 66 amostras GPU schema3 por janela. Sem erro CEF. Todos os
nós foram removidos e câmera/flags restaurados. App/servidor encerraram
0/0; a auditoria de processos confirmou ausência de PIDs próprios e sessão
do dono preservada.

Recibos: evidence/is6-pair-profile-20261103a.json,
is6-pair-profile-audit-20261103a.json e
is6-layer-pair-profile-process-20261103a.json. ZIP em
output/is6-pair-profile-20261103a/executed-sources-and-inputs.zip.

Este é um perfil do protótipo dirigido pelo verificador na 0.18.5. Não
mede a interface coordenada 0.19.0 nem throughput de GR, persistência
composta, migração ou outras combinações. K3 exige provas e perfil próprios.
Nada promovido sobre a instalação 3.13; IS6/v1 permanecem abertos.
