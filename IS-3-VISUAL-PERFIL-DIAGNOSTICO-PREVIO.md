# IS-3 — camada persistente, perfil ligado/desligado anterior à captura

Candidata0.6.1 isolada, quatro janelas60s após30s de aquecimento cada:
IGRF14 visível, IGRF14 oculto, JRM33grau13 visível e JRM33grau13 oculto.
Cada janela começa de nova cópia dos quatro centros na época original,
com a mesma receita de cinco/quatro curvas e três vistas20s. Ocultar usa
o controle booleano público sem remover/recalcular a leitura; nós/frame
continuam presentes e o marcador corporal volta pela política vigente.

1920×1080,CEF100%,IAS15epsilon1e−9,ritmo solicitado0,1,amostras magnéticas
congeladas. Não reconsultar durante evolução. Guardar quadros brutos,
visibilidade nativa e id/leitura constantes em cada vista. Todas as janelas
e vistas exigem mediana≤16,7ms,p95≤25ms,p99≤50ms,zeroquadros>100ms e
ritmo medido/solicitado≥0,9. Energia,momento/angular≤1e−8 normalizados.

RAM própria≤8GiB; dedicadaWDDMsomada≤5,5GiB e abaixo do orçamentoDXGI.
66amostrasWDDMválidas por janela cobrindo início/fim. Auditor separado
recalcula tudo e confere recibosSI/arquivosgráficos/fontes/executável.
Arquivar antes de capturar; não alterar a candidata no perfil. TransporteLua
persistente e soma de memória com sessão explícita. Não herdar perfis0.5.

Comparação cobre visibilidade de uma camada interna por vez, com eventual
retorno de marcadores da política de exibição; não isola só o custo dos
meshes e não prova ausência de toda diferença física entre evoluções
adaptativas. Passividade binária exata é verificada pausada na jornada.
Sem amostragem contínua, múltiplas camadas, mapas/cortes ou Lorentz.

Coletor diagnóstico: collect-gpu-memory-diagnostic.ps1. Corpo original
verbatim, todos os predicados preservados; captura inventários e amostras
mesmo quando houver recusa. Exigir preflight real aceito e jornada nativa
de topologia aceita antes de começar. Resultado0.6A segue incompleto.
