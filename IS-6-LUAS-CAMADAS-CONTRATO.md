# Camadas na cena ampliada0.25.1

Contrato anterior à execução,12/11/2026UTC. A cena agora consulta16centros
físicos e desenha15destinos, com seis mapas e seis nós adicionais em relação
à0.24. Os adaptadores de época/navegação também mudaram desde0.21.1.
Isso altera o trabalho do motor mesmo quando a bancada composta é a mesma.
Verificar a composição nessa candidata requer fontes, registros e perfil
próprios. Não é uma correção demonstrada da pausa580,569ms deK5A: a recusa
original e sua causa desconhecida ficam preservadas. Não repetir K5A.

O Atlas16 é referência. A cópia dinâmica continua com Sol/Terra/Lua/Júpiter,
pausada na época inicial. As camadas usam Schwarzschild exterior de uma
fonte esférica isolada, IGRF14 terrestre e JRM33 joviano. Não somar métricas,
atribuir campo intrínseco às outras luas ou declarar dinâmica de16corpos.
Modelos, unidades, referenciais e limites anteriores permanecem vigentes.

Primeira jornada na janela0.25.1: conferir os16registros do Atlas e sua
identidade; criar a cópia4; gerar um par atual terrestre e um joviano pela
UI, validar sua ciência e os parâmetros65×96,1–3Rref, ampliação200. Usar o
input real do CEF para o envelope terrestre0.1.0 e a exportação joviana
anterior já fixados emK5. Prévia/cancelamento não gravam; confirmação cria
um ramo com origem integral e sem parentesco local fictício. Verificar
ciência idêntica ao original, posição da amostra no motor com orçamento
1mm+ULP, flags reais, salvar, filhos, exportar e alternar ramos.

Arquivo inválido, bytes diferentes depois da prévia, prévia obsoleta,
identidade de ramo inválida e ciência adulterada devem ser recusados sem
trocar a vista confirmada. Qualquer corrupção temporária de latest fica
restrita ao armazenamento isolado desta candidata e deve ser revertida
em finally, preservando os bytes anteriores mesmo se a asserção falhar.

Reabrir em processos novos e conferir quatro saídas zero do host anterior.
Outra cópia4 deve ter identidade nova. Restaurar latest e o ramo terrestre
mantendo a ciência/origem arquivadas e o vínculo separado à fase viva atual.
Salvar/fechar/restaurar as quatro visibilidades; exportar e cancelar uma
restauração real. Cancelamento conserva guard, câmera e artefato. Deixar
remove todos os nós temporários e restaura o contexto vivo. Conferir Atlas16
ao retornar, a sessão protegida, atalho principal e todas as fontes seladas.
Repor a vista/época inicial e manter uma janela0.25.1 aberta ao terminar.

Capturas sem edição: usar openspace.takeScreenshot no framebuffer1920×1080,
copiar os PNG originais e conferir SHA. Primeira jornada: por corpo, prévia
100/150%, quatro visibilidades100%, composição150% e armazenamento150%
(16imagens). Reinício: sete imagens segundo a revisãoK5B, incluindo prévia
terrestre150%. Inspecionar as23imagens, confirmar legendas, mapas, leitura,
fontes, limitações e rolagem em100/150%. Não usar PrintWindow como aceite.

Após aceite funcional/visual, selar um plano próprio com as quatro janelas
Terra/Júpiter estáticos e visibilidade2Hz. Manter30s de aquecimento+60s por
janela,1920×1080/UI100%, mesma malha e amostras IGRF14/JRM33. Catálogo com
pelo menos três ramos válidos e um importado; latest/ramos/exportações são
arquivados antes, validados e mantidos byte a byte. Sem importação/gravação
durante a medida. Os pares medidos são criados pela UI corrente; esta
medida cobre convivência e API de visibilidade, sem throughput de saves.

Limites mantidos: mediana≤16,7ms,p95≤25ms,p99≤50ms,zero>100ms,RAM≤8GiB,
WDDM dedicada+compartilhada≤5,5GiB;240comandos,p95≤0,5s,máximo≤1s,
≥90% concluídos nos60s. Preflight3 e66amostras PDH por janela, identidade
temporal dos processos e quadros brutos completos. Guardar também rastreio
das etapas internas para correlação se houver pausa. Só o primeiro
intervalo é excluído das estatísticas conforme regra anterior, retido bruto.

Auditor separado confere fontes, cápsulas, parâmetros, registros, contexto,
quadros, comandos, memória, limpeza e quatro saídas zero. A janela pode
ser reaberta em seguida para o dono. Recusa ou falha exige diagnóstico
preservado e revisão explícita antes de outro ensaio. Não promover a
candidata nem alterar a contagem7/21 da v1 por este ensaio parcial do IS6.
