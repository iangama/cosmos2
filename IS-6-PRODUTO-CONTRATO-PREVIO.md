# IS6 — candidata isolada0.18, contrato prévio02/11/2026

Base: cópia exata do app0.17.2. Diretório próprio, armazenamento próprio e
launcher diagnóstico; nenhuma promoção/alteração do instalado3.13 ou dos
módulos/recibos científicos aceitos. Dependências IS6 congeladas continuam
identificadas por caminho e SHA256; esta candidata local não é um pacote final.

O instrumento oferece referência esférica exterior de Sol/Terra/Lua/Júpiter,
seleção do corpo na cópia solar pausada, domínio1≤interno<externo≤100Rref,
33/65/129/257anéis,96setores,plano GALACTIC XY/XZ/YZ e altura0–1000.
Padrão1–8Rref,65anéis,XY,altura200. Mostrar ampliação e referência adotada;
não apresentar o desenho como deformação óptica nem gravidade recíproca GR.

Sondas usam anel/azimute exatos e observador receptor em anel independente:
raio areal,compactação,g_rr,K,razão/déficit do relógio estático,distância própria,
comparação emissor/receptor e posição física/exibida. Interior excluído;
GM deriva da massa do cenário,Rref do maior semieixo PCK. Mostrar época,
unidades,fonte e limitações. Nenhum controle muda órbitas,massa ou época.

Serviço serial com admissão imediata: recusar comandos concorrentes/atrasados,
identidade/revisão da vista e source_guard explícitos. Estado de consulta
permanece disponível durante a preparação. Cancelamento por ID de transação
tem rota curta independente; é permitido até a confirmação da candidata.
Um cancelamento confirmado só retorna após limpeza e impede publicação tardia.
Preparar nós ocultos; manter artefato/view/câmera anteriores até ACK nativo.
Falha de preparação/ACK mantém estado anterior; rollback não confirmado fica
explícito e bloqueia novos comandos até recuperação. Fechar restaura câmera
e flags originais. Campos/partícula/zona solar e malha não disputam a cena.

Persistência pelo Store científico aceito: saved separado,32ramos,linhagem,
exportação e carregamento recalculado antes da troca. Restaurar uma referência
arquivada não substitui a fase orbital atual. Salvar/mover sonda/ocultar não
recalculam o artefato; reconfigurar cria outro ID. Falhas de arquivo mantêm
artefato/view/cena anteriores. Não aceitar schema antigo/adulteração.

Interface CEF própria em português: abertura descoberta na navegação,
formulário validado,estado de progresso/cancelamento,mensagens de erro,
controles de sonda/visibilidade e save/load/ramos/export. Layout permite
observar a malha com painel lateral,rolagem e foco de teclado em100/150%.

Antes do aceite: arquivar fontes/contrato/limites. Testar matemática real e
serviço serial com protocolo controlado sem confundir isso com teste nativo.
Depois provar HTTP+CEF+motor reais: quatro corpos,configuração,resolução,
sondas,visibilidade,save/load/ramos/reabertura,cancelamento durante preparação,
recusas de concorrência/guard/arquivo e integridade da fase/dono/limpeza.
Medir preparação≤15s no motor (limite herdado) e comando completo≤30s nos
casos contratados. Inspecionar capturas reais100/150% separadamente.
Perfil próprio após correções: janelas de malha padrão,máxima,sondas e ocultação,
com limites registrados antes da execução. Nenhum aceite de throughput GR,
camadas simultâneas ou toda IS6 decorre destes resultados.
