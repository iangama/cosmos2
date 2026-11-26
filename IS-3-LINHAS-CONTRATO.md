# IS-3 — linhas magnéticas corporais, contrato anterior à verificação

Fatia nova em staging, derivada da candidata de vetores já auditada. Não
alterar essa base, instalado, dados científicos ou sessões do dono. Usar uma
nova candidata e armazenamento próprio somente após a bancada passar.

As curvas integram dx/ds = ±B(x)/|B(x)| no referencial corporal, em uma
época confirmada. IGRF14 usa o ano decimal da leitura e eixos ITRF93; JRM33
usa o mesmo grau 1/13/18 da leitura e Sistema III. Aplicar exatamente a
rotação corporal→J2000→GALACTIC e o centro evoluído da amostra. A camada
continua congelada ao evoluir e não aplica força aos centros neutros.
Linhas não são trajetórias de partículas, tubos de plasma ou intensidade.

Domínio terrestre: altura geodética WGS84 entre 0 e 1000 km, como a consulta
aceita. A inversão cartesiana deve recuperar os pontos geodéticos com erro
de altura ≤1 µm e ângulo ≤1e−10 grau, inclusive polos. Domínio joviano:
raio entre 1 e 20 Rj, preservando o domínio numérico já declarado, sem
afirmar precisão observacional do campo total nessa região. Aceitar apenas
1 µm de arredondamento nas bordas terrestres e 2e−15 relativo nas jovianas.
Nunca avaliar B em estágio fora do domínio. A borda encerra o traçado;
não extrapolar, ligar as pontas ou chamar uma curva truncada de fechada.

Integrador próprio: RK4 com duplicação de passo, erro estimado pela
diferença/15 e passo adaptativo em unidades do raio de referência. Usar
passo máximo 0,04 R, tolerância local 1e−9 R, passo mínimo 1e−7 R;
encerrar junto da borda a até 1e−6 R. Cada sentido tem limite explícito
de 16 R de arco e 2048 passos aceitos, com teto de avaliações. Campo
exatamente nulo encerra por direção indefinida, sem substituir falha por zero.
Erro numérico da curva e quantização gráfica são separados da incerteza
observacional, que não é propagada nem tomada como zero.

Primeiro conjunto: linha pela amostra e quatro sementes equatoriais
canônicas, removendo duplicatas. Terra: altura WGS84 500 km; Júpiter: 1,5 Rj.
Longitudes leste 0/90/180/270 graus. Guardar sementes, vértices SI, B em
cada vértice, arco, parâmetros, número de avaliações e motivo de término
em cada sentido. Setas de direção na curva usam o mesmo B; seu tamanho
é gráfico. Grade de referência e ponto continuam identificados.

Antes da integração nativa, comparar curvas em comprimentos de arco
comuns com DOP853 independente (rtol1e−11, atol1e−12 nas coordenadas/R):
erro por componente ≤2e−6 R. Casos dos dois modelos, anos/graus, posições
acima/abaixo/laterais, polos e ambos os sentidos. Refinar tolerância para
1e−11: diferença ≤2e−6 R. Campo uniforme: linha reta ≤1e−12 R;
dipolo analítico: invariante r/sin²θ ≤2e−6 relativo e comparação DOP853.
Conferir covariância por rotação e inversão do sinal, sementes na borda,
ausência de avaliações externas, campo nulo, vetores/números inválidos e
limites de esforço. Dados/fontes/oráculos/contrato arquivados antes do teste.

Integração futura exige controles reais, substituição/limpeza, recusas sem
mutação da camada anterior, época/modelo visíveis, 100/150% com revisão de
pixels originais e perfil próprio sem herdar o perfil do vetor único.
Persistência em checkpoints/ramos e mapas/cortes continuam saídas próprias
do requisito geral; esta fatia não as declara concluídas.
