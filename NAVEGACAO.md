# Navegação do Atlas — contrato prévio C2-02

13/10/2026. Busca por nome/tipo/proximidade, filtros, árvore de sistema,
seleção por clique, visita/orbitar/seguir/livre, favoritos/retorno e linha do
tempo com cobertura. Percurso Terra→Lua→Saturno→favorito sem terminal.
Foco em campos não aciona atalhos de câmera; escala100–150% e painéis que
preservem a cena, com controles por teclado e botões equivalentes.

Saturno exige NAIF699, não o baricentro6. Manter DE442s como autoridade dos
corpos atuais e do baricentro6; adquirir SAT459 oficial, cujo merge conserva
699 de SAT441/SAT441xl. Extrair somente segmentos699 relativos a6, no recorte
1950–2051 (+2dias de margem técnica nos limites para a guarda de tempo), com SPICE spksub (cópia de polinômios, sem ajustar efeméride).
Preservar original/hash/MD5 publicado, descritores/ordem dos segmentos e
comparar o subconjunto com o original em épocas cobrindo o domínio. Não
carregar outros segmentos do SAT459 que substituiriam DE442s. SAT480 menor
foi considerado, mas termina em2050-01-01 e não cobre todo2050 já disponível
no produto. Não reduzir silenciosamente a cobertura antiga.

Backend e renderer calculam699→6(SAT441)+6→0(DE442s), J2000 como autoridade
e matriz explícita para GALACTIC. Forma elipsoidal PCK00011 e rotação
IAU_SATURN geral; imagem identificada e adquirida separadamente. GM do
sistema6 não vira GM do planeta699. Se não curado, GM/massa ficam ausentes
com origem identificada. Copiar Sol/Terra/Lua continua sendo um subconjunto
de três corpos explicitamente escolhido, excluindo Saturno da dinâmica.

Navegação consulta posições nativas/época/câmera de forma consistente.
Distância é distância física até o centro; altitude sobre forma adotada
tem outro nome. Ícones/listas não alteram tamanho dos corpos. Busca/filtro
não move câmera; selecionar e visitar são ações identificadas. Alternar
modo e editar condição preservam pose/época, exceto deslocamento solicitado.
Viagem suave deve poder cancelar, com início/fim/estado confirmado.

Favoritos persistem alvo/pose/referencial/época/mode/versão em arquivo local
selado e atômico. Validar todos os campos/cobertura/IDs antes de aplicar;
favorecer confirmação da pose nativa, não só texto de botão. Retorno restaura
uma vista conhecida sem herdar escala de mapa ou estado de laboratório.

Tempo é Atlas TDB/UTC por kernel fixo, nunca relógio do worker. Pausa,
retomar/taxa e limites precisam de confirmação nativa e feedback ao atingir
cobertura. Modos Atlas/Experimento permanecem distintos. Atalhos G/F/Espaço/
Esc não podem operar enquanto texto/select/modal tiver foco; estado de teclas
é limpo ao perder foco. Voo livre é movimento da câmera, não força física.

Critérios prévios: subconjunto699 coincide com original até1e-9km/1e-12km/s;
corpos anteriores permanecem no mesmo modelo sem kernels sobrescrevendo;
renderer coincide com backend até1mm (limite pela escala) e rotações1e-12.
Busca e favorito não alteram estados físicos. Inputs inválidos/favoritos
corrompidos recusados antes da mutação. Terra/Lua/Saturno/retorno percorridos
porcliques reais CEF, conferindo alvo/pose/época; voo/foco/atalhos/modos testados.
Imagens1920×1080 eUI150% revistas; ampliar benchmark apenas pela mudança de
conteúdo pertinente. C2-03 tem seu próprio aceite de luz/anéis/qualidade.

Fontes: NAIF SAT459.mrg/cmt, SPICE spksub_c e tutoriais SPK (IDs de corpo e
baricentro). APIs de navegação consultadas na fonte OpenSpace0.22 fixada,
incluindo NavigationState/OrbitalNavigator/PathNavigator. Não alterar o
executável do motor para a primeira integração, salvo limitação demonstrada.
