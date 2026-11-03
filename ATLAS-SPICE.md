# Atlas solar inicial — contrato prévio

Fatia C2-01: Sol10/Terra399/Lua301 com IDs sol:naif:<id>, posições/velocidades
JPL DE442s, centro baricentro solar0, referencial inercial J2000/ICRF, estado
geométrico simultâneo (correção de aberração NONE). Metros e m/s no contrato,
conversão km/kms na borda SPICE. Época ET em segundos TDB desde J2000; entrada
UTC convertida via LSKfixo naif0012, sem subtrair constante informal. Cobertura
de aplicação inicial1950–2050, a confirmar por spkcov para cada corpo; fonte
DE442s anuncia1849–2150. UTC futuro usa segundos intercalares conhecidos,
sem garantir conversão de uma tabela futura ainda inexistente.

Fonte JPL/NAIF DE442s, recorte DE442 publicado2025. Aquisição com checksumMD5
publicado e SHA256 local; LSK e PCK00011 fixados separadamente. Terra WGS84 e
Lua esfera1737,4km são formas adotadas, não reconstrução geológica completa.
Rotação IAU_EARTH/IAU_MOON do PCK é modelo geral, sem alta precisão ITRF93/
orientação lunar binária. Texturas NASA permanecem propriedades independentes
de posição/rotação. Sol é fonte de luz sem superfície nesta fatia.

Fonte de Atlas continua independente dos operadores dos experimentos. Não
reintegrar/reinventar efemérides ao desligar uma força na bancada. Worker não
herda época/estados implicitamente; controle do Atlas permanece pausado ao
editar época. Comparar duas datas deve alterar separação/iluminação real do
modelo, preservando raio material. Fora da cobertura é recusado antes de enviar
um comando ao motor; erro de confirmação não deve anunciar época aplicada.

Critérios antes de implementar:
- Hash publicado DE442s e cobertura por corpo; unidades/IDs/frame/epoch/source.
- Estados de5épocas (1950,2000,2026,2030,2050) contra CSPICE nativo/OpenSpace;
  diferença posição≤1mm para o mesmo kernel, não é acurácia observacional.
- Conferir Terra/Lua contra Horizons com correçãoNONE/centro0/ICRF e épocasTDB
  equivalentes; diferença≤1km como cheque de integração entre versões JPL,
  registrar o modelo Horizons em vez de exigir igualdade de modelos distintos.
- Centro Lua−Terra confere distância; transformação rotação é ortogonal e
  coerente com PCK, sem chamar corpoIAU de ITRF de alta precisão.
- UI mostra época UTC/TDB e procedência; mudança de data e ida/volta Atlas/
  laboratório nativas, validação de domínio, imagens Terra/Lua revisadas.
- Preservar perfil/asset G0 aprovado antes de alterar a cena; medir regressão
  proporcional, sem reatribuir benchmarks antigos à cena modificada.

Estado: implementado e comparações/UI nativas passaram; regressão curta de
desempenho em coleta. Não encerra C2-01 nem aprova todos os conteúdos/observadores.

Integração: a autoridade científica continua J2000/ICRF. O renderer OpenSpace
usa GALACTIC, inclusive nos cálculos internos de eclipses atmosféricos.
O primeiro recorte J2000 passou coordenadas, mas a revisão visual encontrou
incompatibilidade de referência. A solução mantém GALACTIC no renderer e
exporta a transformação J2000→GALACTIC explicitamente, posições_render_m e
layout de matrizes por linhas para vetores coluna. Não altera o estado JPL.
Também corrigida a chave Lua ReferenceFrame (Frame era ignorada pelo motor),
conferindo ângulo da câmera iluminada contra o vetor Sol−corpo na raiz.
O resultado anterior fica em native-atlas-j2000-initial-check.json como
diagnóstico de coordenadas, sem aceite de iluminação/experiência visual.

Resultado final GALACTIC: cinco épocas, maior diferença por componente
0,00003052m, rotação1,11e-16. Horizons DE441 vs DE442s difere160,15–180,47m
nos quatro estados Terra/Lua; é comparação de pipelines/modelos, não precisão
observacional. Leap2016 preservado, seis datas inválidas recusadas e época
inválida nativa não altera o estado. UI confirmou época, mudança de distância,
retornoAtlas/Lab sem alterar época e recusa de alteraçãoAtlas no laboratório.
Câmera iluminada mede cos30°=0,8660254 na raizGalactic; não move Sol/fontes.
ImagensTerra/Lua finais revistas; a Lua mostra Terra ao fundo na posição real
do modelo. Horário UTC é ISO explícito, evitando calendário inglês ambíguoCEF.
