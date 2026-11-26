# Perfil próprio da navegação dos oito planetas

Esta medição pertence à candidata isolada0.24.0. A cena possui os oito
planetas, Lua e Sol com os kernels e mapas fixados no manifesto. Os aceites
funcional e visual são pré-requisitos. O teste utiliza o aplicativo já
aberto para o dono, com recursos previamente consultados; não mede partida
fria, aquisição de mapas ou importação das camadas K5.

Executar uma janela por destino, na ordem Mercúrio, Vênus, Terra, Lua,
Marte, Júpiter, Saturno, Urano e Netuno. Fixar épocaUTC11/10/2026 12h,
relógio pausado, vista Visão geral, exposição3,7 e céu didático ativo.
Conferir o destino e aguardar30s antes de medir60s estáticos. Resolução
nativa1920×1080, interface100%. A página mantém sua renderização e consultas;
entrada fica inerte durante aquecimento/coleta para preservar a receita.
Restaurar entrada, escala, ficha selecionada e vista original no final.

Limites conservados: mediana≤16,7ms, p95≤25ms, p99≤50ms, zero intervalos
acima100ms, RAM≤8GiB e soma WDDM dedicada+compartilhada≤5,5GiB. Intervalos
vêm do SGCT incluindo VSync. O primeiro intervalo é preservado no bruto e
excluído da estatística pela mesma regra dos auditores anteriores. Exigir
mais de1000intervalos válidos e duração60±0,5s; nenhum corte adicional.

Usar a propriedade temporal de processos já estabelecida, estabilização
limitada antes do preflight, três amostras PDH de prévia e66por destino,
cobrindo integralmente a janela. Conferir RAM e contexto em0/20/40/60s.
Ativar o rastreamento nativo por etapa em cada janela; sua finalidade é
diagnosticar pausas, sem substituir intervalos de quadros ou memória PDH.

Selar fontes, recursos, receita, executor e auditor antes da execução.
Preservar todos os brutos. Qualquer recusa exige registro; não repetir
a mesma medição para obter aprovação. O auditor independente calcula
percentis, recursos e invariantes a partir dos registros preservados.
O app fica aberto; quatro saídas zero exigem um ciclo posterior próprio.
Este perfil não transfere aceite para K5A nem conclui IS6 ou a v1.
