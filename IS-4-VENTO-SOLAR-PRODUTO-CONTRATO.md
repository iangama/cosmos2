# IS4 — candidata0.9.0: vento prescrito e persistência

Antes dos testes: candidata própria output/is4-solar-wind-product0.9.0;
preservar0.8.1 e runtimeIS4. Fonte orbital pausada e snapshot prescrito,
sem MHD. Mesma integração Boris aceita; suporte explícito ao terceiro modelo
Parker, sem converter/renomear arquivos0.8 antigos automaticamente.

Checkpoint científico schema2/is4_static_prescribed_particle, geração0.2.0
inclui todos os módulos de ciência; kind da leitura distingue vento/campo
interno. E do vento pode acumular trabalho. E/g inativos têm trabalho nulo
desde a última intervenção. B continua sem trabalho. Guardar origem+offset,
fonte completa, parâmetros, época, controles, trabalhos compensados e ritmos.
Sonda inclui qDeltaPhiE e Delta(K+mPhiG+qPhiE); Delta(K+mPhiG) isolado
permanece apenas um diagnóstico quando E atua.

Antes de integrar UI: validar leitura contra recomputação, campos não nulos,
cinco casos de worker (três espécies no vento e replay exato de fases aceitas
Terra/Júpiter), pausa,save/load/novo processo/futuro77 exato, ramos com fase+
unidade+visibilidade selados. Recusar arquivos antigos, tipo/epoch/metadata/
geração/configuração alterados antes de substituir estado aceito. Fontes e
receita arquivadas antes de executar; falhas preservadas com novo label.

Depois: jornadaCEF real100/150 com fonte/unidades visíveis, física e exibição
independentes, domínio/HCS explícitos, controlesE/B/g, sonda e energia,
persistência/ramos/export/restart. Nova geração exige jornada própria;
perfil corporal0.8.1 não aceita automaticamente o cenário de vento.
