# C2-14 — contrato de diagnóstico espacial anterior aos dados

Recorte novo da bancada Órbitas e relógios. Não altera o núcleo temporal
aceito, o produto0.29.0 ou a integração final. Base física e unidades:
C2-14-ORBITAS-CONTRATO-20261114.md; manter domínio e limites numéricos.

Três camadas distintas:
1. Sondas estáticas3D: raio areal, dτ_estático/dt=√(1-r_s/r) e
   K=12r_s²/r⁶ em m⁻⁴. Preservar36 posições em três cascas da bancada.
   Mapa de déficit de ritmo em ppm ou log10(K/[1m⁻⁴]), com unidade e
   extremos da amostragem. Valores iguais usam cor única e legenda explícita.
2. Diferença física: vetor coordenado x_GR(t)−x_Newton(t) em metros, na
   mesma grade temporal e estado inicial do contrato anterior. Nunca chamar
   esse vetor de erro de integração ou distância própria espacial.
3. Diagnóstico numérico: resíduos assinados adimensionais radial e métrico
   nos pontos da solução e em todos os nós internos. Não extrapolar esses
   resíduos para pontos do volume sem solução de trajetória.

Usar R,U,H,E,I,κ,A do contrato anterior. Radial:
U²/2+H²/(2R²)−1/R−κH²/(2R³)−I.
Métrico: −A·(dT/ds)²+κU²/(2A)+κH²/(2R²)+1,
com dT/ds=1+κ·[I/(E+1)+1/R]/A. Preservar essa forma estável.
Nos nós internos, R,U,φ,J são os estados originais. Na grade pública,
recuperar U projetando a velocidade coordenada no raio e multiplicando por
dT/ds; marcar a origem e tolerância de reconstrução. Não alterar os dados
originais nem usar a grade pública para substituir máximos dos nós internos.

Publicar formato c214.orbit-maps/0.1.0 com hash da configuração, hash do
núcleo, unidades e domínio, campos/posições e resumos. Limite4097 pontos da
grade,200000 nós internos,36 sondas; recusar dados não finitos, incoerentes,
estados internos sem tempo correspondente e orçamento excedido. Nenhum
cálculo pode publicar um resultado parcial como completo. A configuração
física permanece a do resultado confirmado. Intervenções da bancada exigem
identificar mapas de referência e trajetória aplicada, sem atribuir um
resíduo geodésico a uma reta de intervenção.

Verificação anterior à UI:
- círculo, duas excentricidades e ambas orientações; preservar entradas;
- comparar ritmo e K com referência Decimal80, erro relativo≤2e-14;
- rotação das posições preserva escalares; escala conjunta L,r_s por q
  preserva ritmo e faz K variar q⁻⁴, usando q=2 e1/2;
- separação inicial≤1e-12L; vetor em mesmo t reconstruído independente;
- reconstrução dos máximos radiais/métricos em grade+nós: diferença do
  máximo bruto≤1e-13; limites prévios2e-10/2e-12 continuam obrigatórios;
- injetar nó radial corrompido e exigir recusa; não mascarar por redução
  da grade, clipping, renormalização ou aumento das tolerâncias;
- recusar NaN/Inf, arrays inconsistentes e limites de amostragem excedidos;
- repetição determinística, JSON estrito e rastreabilidade das fontes.

Congelar a receita operacional e fontes antes de executar esses casos.
Validar UI isolada100/150%, escolha por mouse, escala/legenda/probe,
rotação/zoom/restaurar, tempo e erro/recuperação. Entregar somente depois
por nova revisão e caminho original, preservando a sessão do dono. Não
repetir por hábito o perfil de órbitas já aceito. Contrato novo não é prova
executada nem aceite de C2-14.
