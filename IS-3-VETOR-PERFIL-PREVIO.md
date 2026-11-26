# IS-3 — perfil da camada magnética fixa

Receita anterior à captura: duas janelas próprias de 60 s, cada uma após
30 s de aquecimento, em 1920×1080 e CEF 100%. Uma janela usa IGRF14 e outra
JRM33 grau13, nos pontos padrão dos formulários. Cada uma começa de uma nova
cópia dos quatro centros na época original do Atlas. A camada é calculada
enquanto a cena está pausada e permanece fixa, explicitamente obsoleta após
evoluir. Não há amostragem contínua ou força magnética aplicada aos centros.

Evolução IAS15 epsilon10⁻⁹, ritmo canônico solicitado0,1 por segundo de
parede, a menor opção suportada pelo produto. A gravitação pode evoluir além da
cobertura temporal do provedor magnético; a camada permanece da época inicial,
sem extrapolar/reconsultar o modelo do campo. Avaliar ritmo
medido dividido pelo solicitado, com mínimo0,9. Não comparar esse recorte
à carga física do perfilIS12 emritmo1. A tentativaA pediu0,001, foi recusada
antes de qualquer aquecimento/captura e permanece incompleta; esta correção
foi fixada antes da tentativaB, sem alterar limites de quadros/recursos. Três vistas de20s da mesma camada:
vista inicial do ponto, lateral e polar; sem filtrar intervalos.

Limites: mediana≤16,7ms, p95≤25ms, p99≤50ms, nenhum quadro>100ms. RAM dos
processos próprios≤8GiB; WDDM dedicada somada≤5,5GiB e abaixo do orçamento
DXGI da placa física. Somas podem repetir memória compartilhada. Cada
janela exige66amostrasWDDM sem erro, cobrindo início/fim. Guardar intervalos
SGCT brutos e auditar janelas e cada vista. Energia/momento/angular≤10⁻⁸.

Confirmar identificador/modelo da camada, nós/visibilidade e marcador
ocultado no motor nas três vistas. Guardar leitura fixa, metadados e fase
dinâmica; todos os pontos seguem a época da amostra, sem serem arrastados.
Arquivar fontes/contrato/receita antes da execução. TransporteLua persistente
e chamada de memória com sessão explícita. Uma auditoria separada decide
aceite. Não herdar desempenhoJ/IS12 ou aprovar mapas, linhas/Lorentz e
consulta de campo a cada passo com esse resultado.
