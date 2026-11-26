# Perfil próprio da cena com sete luas

Executar uma única receita da candidata0.25.1 após seus aceites funcional
e visual. A cena possui Sol, oito planetas e sete luas. O teste usa o app
aberto e mapas previamente consultados; não mede partida fria ou aquisição.

Destinos na ordem:Mercúrio,Vênus,Terra,Lua,Marte,Júpiter,Saturno,Urano,
Netuno,Io,Europa,Ganimedes,Calisto,Encélado,Titã. Cada destino recebe a vista
Visão geral,30s de aquecimento e60s de coleta estática. FixarUTC11/10/2026
12h, relógio pausado, exposição3,7 e céu ativo. Resolução1920×1080,UI100%.
Conservar renderização/consultas da página e tornar a entrada inerte apenas
durante a receita. Restaurar entrada, escala, seleção e vista no final.

Limites:mediana≤16,7ms,p95≤25ms,p99≤50ms,zero intervalos>100ms,
RAM≤8GiB,WDDM dedicada+compartilhada≤5,5GiB. Guardar todos os intervalos
SGCT comVSync, preservando o primeiro no bruto e excluindo-o da estatística
pela regra anterior. Exigir>1000intervalos válidos por janela e60±0,5s.

Usar estabilização de propriedade temporal de processos antes do preflight,
três amostrasPDH de prévia e66por destino cobrindo sua janela. Contexto e
RAM são conferidos em0/20/40/60s. Ativar rastreamento nativo por etapa.
Selar fontes, receita, executor e auditor antes da coleta. Preservar recusas
e brutos; não repetir a mesma execução para obter resultado favorável.

O auditor independente verifica os15destinos, limites, memória, tempo e
estado doAtlas. O app permanece aberto; quatro saídas zero da0.25.1 serão
conferidas em ciclo posterior com reabertura imediata. Não executar backup,
downloads ou outras cargas pesadas durante as janelas. Esse perfil não
altera a recusaK5A nem conclui IS6/v1 automaticamente.
