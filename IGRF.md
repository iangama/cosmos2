# Campo terrestre IGRF14 — contrato e validação

FatiaC2-01/13: instrumento de campo principal terrestre, não magnetosfera ou
simulador de tempestades. CoeficientesIAGA/NOAAfixados emigrf14coeffs.txt;
reciboigrf-acquisition.json. FortranBGS original fica apenas em.upstream para
comparação local independente; não assumir que a licençaGeomag7 abrangeBGS.

Época1900.0–2030.0, ano decimal explicitamente informado. Interpolação linear
entre épocas5anos;2025–2030 usa variação secular prescrita, grau8. Campo principal
grau10 antes1995, até13 posteriormente. Raioharmônico6371.2km, distinto do raio
6371km do dipolo ideal. Sem extrapolar até2035 só porque o Fortran a permite.

Entrada: latitude geodética[-90,90], longitude leste[-180,180], altitudeWGS84
[0,1000]km (domínio escolhido do instrumento), ano decimal. WGS84preciso para
conversão geodética/geocêntrica; referênciaFortran usa constantes arredondadas,
cujo efeito será quantificado. Componentes locais norte/leste/baixo emnT eT;
intensidadeshorizontal/total, declinação e inclinação emgraus. No polo, norte/
leste dependem do meridiano escolhido; posiçãoECEF e vetor3D ficam definidos.
Declinação perde significado quandoHse aproxima dezero; mostrar indefinição.

Mapa geográfico e globo3D calculados na mesma altitude/época, comparação do
modelo completo com truncamento de grau1 (dipolo do próprioIGRF, não o preset
artificial anterior). Sonda por coordenadas, componentes e diferença vetorial.
Força magnética instantânea qv×B numa partícula de teste clássica local, velocidade
definida emnorte/leste/baixo. Gate atuação/efeito suprime essa força mantendo
campo/fontes de referência; sem trajetória inventada ou evoluçãoMHD. Controle
de referência só altera visualização. Forte/fraca/gravidade têm palcos próprios.

Fontesprimárias: [NOAA/IAGA](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field),
[BGS](https://geomag.bgs.ac.uk/research/modelling/IGRF.html),
[limitações](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field/health-warning).
Resíduos numéricos entre códigos não são acurácia observacional. Não converter
incerteza global históricaBGS em barra de erro exata de um ponto/época novo;
modelo omite campos externos e detalhes locais, incerteza não tomada comozero.

Critérios prévios:
- Pelo menos20posições/épocas/altitudes contraFortranBGS original, mesmos
  coeficientes: cada componente≤1nT; incluir polos, datas1900/1995/2025/2030,
  interpolação e longitudeperiódica. Conferir referências geocêntricas também.
- Grau1 contra fórmula dipolarCartesiana independente; escala r^-3; vetorECEF
  invariável pela escolha de longitude no polo, componenteslocais coerentes.
- ConversãoWGS84 contra coordenadas conhecidas, ida/volta como chequeadicional.
- Gatesforça/campo independentes, potência magnética nula, código/dados/época/
  frame/unidades no export. Datas/altitudes fora do domínio recusadas.
- UI mapas/probes/meridianos/unidades/PT-BR/viewport720px e CEFnativo, sem errosJS.

O contrato acima foi registrado antes da implementação. Backend próprio em
app/geomagnetism.py usa harmônicos de Schmidt sem fase Condon–Shortley,
conversão WGS84 precisa e limite analítico nos polos. Código Fortran BGS não
foi portado para o produto. Coeficientes SHA256
8f8d88403028fc4ee92c4f38d97b46e0a87e2cfc496045b43c9e26c1d6b0903c.

verify-igrf.py passou 58 casos contra o Fortran original: maior diferença
por componente 0,0145434 nT; geocêntrica 0,00435173 nT. O Fortran emprega
constantes WGS84 e conversão angular arredondadas; mantivemos as constantes
precisas, sem ajustá-las para reduzir resíduos. Grau 1 conferido contra
dipolo cartesiano independente, erro relativo 3,98e-16. Polos, periodicidade,
conversão conhecida, oito combinações de carga/gates e potência magnética
nula foram conferidos. Fora da cobertura temporal/altitude é recusado.

Reprodução Linux: scripts/build-igrf-reference.py compila a subrotina original
com GNU Fortran13.3 extraído localmente; scripts/collect-igrf-reference.py
regera o fixture de 58 casos, SHA256
7837fdb549b90a98ac62476208a550e6da74c5fe302af61063174cd96643f1d1.
scripts/verify-igrf.py roda no Python Windows do produto contra esse fixture.
Recibos igrf-reference-build/reference/check identificam fontes e versões.

UI oferece 703 amostras espaciais, uma sonda por coordenadas e componentes
X/Y/Z/H/F/D/I, com a mesma escala de cor para IGRF completo e grau 1. Cores
entre amostras são apresentação; declinação usa média angular circular.
Medições ficam fora do desenho. Força qv×B é instantânea, sem órbita ou
tempo fictício; time_s é vazio e o contrato declara spatial_snapshot. UI Edge
passou globo/rotação/mapa/sonda/comparação, operadores/referência independentes,
época/altitude/polos, 720px e zero erros JS. Validação CEF nativa é separada.
verify-native-igrf.py passou no CEF real: ambos os mapas/componentes/grau 1,
sonda, snapshot sem timeline, forceoff/referência preservada, visibilidade e
retorno a outros palcos. Imagens globo/mapa nativas revistas, sem sobreposição
das medições; época é apresentada como ano, sem separador de milhares.
