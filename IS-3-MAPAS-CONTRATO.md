# IS-3 — mapas e corte meridional associados à amostra

Fatia seguinte em staging, mantendo a candidata medida intacta. Gerar mapa
latitude×longitude de |B| e corte meridional a partir da mesma leitura
congelada, síntese, grau, época e orientação adotados. São produtos de
modelo, sem nova medição e sem incerteza observacional propagada.

Casca:19latitudes−90..90° e37longitudes inclusivas, com10° de intervalo.
Terra usa latitudegeodética/longitude−180..180° e alturaWGS84 da amostra;
Júpiter usa latitudeplanetocêntrica/longitudeLESTE0..360° e raio da amostra.
Guardar vértices físicos, vetoresB e móduloSI. A longitude duplicada na
costura é explícita; não integrar áreas dando dois pesos a essa borda.

Corte meridional: plano que contém o eixo corporalZ e o meridiano da
amostra, coordenadas cartesianas u/z em metros. Grade65×65; extensão da
Terra a+1000km e joviana max(3Rj,raiodaamostra), sempre≤20Rj. Ponto fora
do domínio recebe máscara/None, nunca B=0. Não interpolar lacunas internas,
preencher o interior corporal ou atribuir um campo externo não adotado.
O número de células não mede precisão ou máximos globais comprovados.

IGRF:altura0..1000km; JRM:raio1..20Rj. Guardar a transformação completa
modelo→J2000→GALACTIC e a origem evoluída da leitura. Cortes/mapas ficam
congelados; módulos não recebem translação. O ponto selecionado é uma
sonda explícita, mesmo quando não cai na grade. Conferir seu B com a
consulta original:≤2e−18T/componente. Isso é tolerância numérica, não
barra de erro. Densidade fixa≤5000células para limitar esforço nesta fatia.

Verificar ambos os modelos: cardinalidade/formas, periodicidade≤2e−18T,
vetor único nos polos≤2e−18T, convenções leste/norte, plano meridional
≤1e−10R, covariância de módulo≤2e−18T, altura/raio adotados e máscaras
em todas as células; nenhuma chamada ao provedor fora do domínio. Recusas
de metadados/época/grau/parâmetros sem mexer nos dados de origem.
Arquivar fontes/fixtures antes de executar. FigurasPNG/PDF/SVG próprias,
com unidades, época e modelo; inspecionarPNG original antes de aceitar
imagem. A integraçãoCEF/nativa, seleção de células, exportação, persistência
e perfil próprio são etapas posteriores e não são aprovados pela figura.
