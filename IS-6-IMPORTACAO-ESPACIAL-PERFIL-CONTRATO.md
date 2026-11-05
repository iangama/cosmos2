# K5D — perfil próprio da referência importada0.22.1

Pré-requisitos: E/F funcionais nativos0.22.1, visualE aceita, byte-identidade dos
modelos/backend com0.22.0 e coletor PDH v2 com auditor independente. Validar também
uma coleta curta no modo Experimentos/worker pausado antes da janela formal.
Nenhum perfil anterior é transferido para esta candidata.

Usar exatamente a referência solar arquivada A, com cápsula, artefato e sondas
originais,1–8Rref,65×96 e ampliação200. Restaurar um ramo local importado da
candidata, com source_guard da nova cópia solar viva pausada. Não recalcular,
amostrar magnetismo, mudar domínio/resolução ou gravar durante a medição.
Conservar bytes de todos os registros confirmados antes/depois e arquivá-los.

Congelar quatro janelas1920×1080/UI100%, cada uma com30s de aquecimento e60s
de captura bruta do motor: malha visível estática, malha oculta estática, sondas
com malha visível e visibilidade alternada. As duas últimas têm120comandos
set_view, a cada0,5s. Sondas usam índices determinísticos dentro da malha;
todos os resultados esperados são calculados/arquivados antes de cada janela.
Visibilidade não altera o artefato ou a vista original na cápsula.

Limites conservados do IS6: mediana<=16,7ms, p95<=25ms, p99<=50ms,
zero quadros>100ms, RAM da árvore própria<=8GiB e soma WDDM dedicada+compartilhada
dos processos próprios<=5,5GiB. Completar pelo menos90%dos120comandos até60s,
latência p95<=0,5s e máxima<=1s. Não descartar quadros além do primeiro parcial
já definido na metodologia nem substituir amostras GPU recusadas.

Pausas, cenários, identidades, época, fonte viva e artefato devem permanecer
confirmados. Conferir quatro leituras de estado/RAM/nativo por janela, em0/20/40/60s,
incluindo valores SI das sondas e draw efetivo, com guards antes/depois iguais.
O UI pode acompanhar o estado por polling; este perfil é da API de vista e do
desenho, sem alegação de throughput humano, importação, salvamento ou startup.

Coletar66amostras PDH v2 por janela, com o conjunto de caminhos e árvore própria
congelados. Sinalizar prontidão depois da primeira amostra válida; dados GPU devem
cobrir o intervalo completo dos quadros. Validação nova usa schema4/bytes brutos,
timestamp local preservado e UTC convertido nativamente; o antigo schema3 não é
recodificado. Resource limits e cobertura temporal permanecem obrigatórios.

Arquivar fontes, plano, referência, cápsula, receitas e arquivos de cena antes da
execução. Auditor independente recompõe ciência/sondas, contagens, percentis,
cadência, guards, origem, somas e cobertura GPU. Exigir limpeza, câmera/flags
restauradas e saídas reais0/0/0/0 do host próprio. Falha recusa o perfil; não
normalizar o código executado ou o recibo para fazê-lo passar.
