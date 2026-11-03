# C2-02 — decisão local de aceite

13/10/2026, Windows/RX7600, OpenSpace0.22 compilado e CEF nativo.
**Aprovado localmente o recorte de navegação C2-02.** Contrato prévio em
NAVEGACAO.md. O percurso Terra→Lua→Saturno→favorito foi executado por cliques,
com câmera e época verificadas no motor. A ampliação geral do catálogo e a
qualidade visual dos três mundos continuam nos marcos C2-04/C2-03.

## Experiência e domínio

Busca por nome/tipo, filtro de distância da câmera, ordenação por proximidade,
árvore do Sistema Solar e seleção em marcadores projetados da cena. Selecionar
consulta a ficha; Visitar move a câmera. Viagem suave de quatro segundos ou
salto direto, cancelamento e retorno à vista anterior. Órbita inercial,
seguimento da rotação até20raios e voo livre WASD/QE ou botões equivalentes.
Voo livre move a câmera em GALACTIC; não atua sobre a matéria.

Favoritos locais guardam pose/referencial/alvo/modo/época/ritmo, com integridade
SHA256 e gravação atômica. Recusa de arquivo corrompido/campos inválidos ocorre
antes de comandos ao motor. Pausa/ritmo reverso ou direto, slider e época UTC,
com guarda na cobertura1950–2050. UTC segue LSK fixo, sem prever novos segundos
intercalares. Atalhos G/F/Espaço/Esc respeitam foco de edição; testes usaram
também eventos reais do teclado Windows. Interface100/125/150%; com zoom alto
ou janela menor, catálogo/ficha alternam para preservar a cena.

## Dados e regressões

Saturno NAIF699, estado699→6 SAT441 +6→0 DE442s. Recorte de SAT459 por SPICE
spksub, preservando polinômios e ordem. Dois dias de margem técnica para a
guarda de tempo; API continua1950–2050. Apenas699 no kernel derivado:201épocas
idênticas ao original e estados anteriores bitidênticos. Kernel8.074.240bytes,
SHA1c581c20a49256550bab0368928f81e9c5da14f9bad127f09ff6a9edf490aa27.
J2000 é autoridade científica; render GALACTIC por matriz explícita.
GM6 não é massa do planeta; GM/massa699 permanecem desconhecidos.

verify-atlas local/nativo: cinco épocas/quatro corpos, diferença máxima de
componente0,000244140625m e de rotação1,11e-16. A comparação numérica não é
acurácia observacional. Mapa NASA/JPL de Saturno é ficcional e identificado.
O refinamento de imagens/anéis tem contrato próprio em QUALIDADE-VISUAL.md.

verify-navigation passou jornada, seleção sem deslocamento, pose ao alternar
modos, voo livre, foco, viagem/cancelamento, relógio e limites, favorito/época,
reload e cliques150%. Nove casos de corrupção/inconsistência recusados antes
da mutação; nenhum erroJS. verify-native-atlas-ui e
verify-native-atlas-import passaram: mudança de época, lado iluminado,
Atlas↔experimento, cópia estritaSol/Terra/Lua, checkpoints e P32/P128.
verify-atlas-import e verify-packages-properties passaram;13pacotes,
66arquivos/903760474bytes na geração desta decisão. Anéis posteriores
alteram esse inventário sem reescrever a medição histórica.

## Medição e revisão

evidence/atlas-route-c202b.json: três vistas aquecidas de15s,1920×1080,
UI/consultas reais, SGCT comVSync. Mediana74,997–75,061FPS; p95máximo14,711ms,
p99máximo15,256ms, zero pausas>100ms. É uma regressão específica; não substitui
as nove rotas G0 nem a memória total do produto. Captura inicial c202 preservada
como coleta inválida: fechava WebSocket durante cada janela, incluindo timeout
de~1s. A correção para conexão contínua removeu essas pausas.

Capturas nativas de Saturno100/150% revistas: texto legível, indicador central
coincide com planeta, ficha com procedência, controles sem sobreposição.
O mapa/anéis ainda não tinham qualidade aprovada. Aceite é revisão local do
agente; não atribuir uma opinião estética ao dono enquanto ele dorme.
