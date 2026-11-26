# IS-3 — IGRF14 ligado à Terra e ao relógio da cena

Contrato antes de implementar/capturar a ligação. O instrumento antigo e
seus coeficientes fixados permanecem preservados. A maré externa já aceita
na candidata tem escopo próprio; não aprova antecipadamente este campo.

## Provedor de orientação e domínio

Adquirir apenas `earth_000101_270118_261022.bpc`, cerca de4,9MB, comentários
e documentação necessários. Usar nome datado, hashes próprios e eventual
checksum publicado verificável; não inventar checksum quando indisponível.
Conferir identidade com o alias oficial e verificar cobertura pelo próprio
SPICE. Não substituir o PCK genérico nem carregar dados globalmente sem
restaurar a pool. O arquivo traz o frameITRF93, código3000, nãoIAU_EARTH.

O [comentário oficial](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/earth_000101_270118_261022.cmt)
informa cobertura2000-01-01 a2027-01-18 e último datum2026-10-22. Instantes
depois desse datum são previsão do provedor e devem ser identificados.
Confirmar limitesTDB no arquivo; recusar fora da cobertura sem fallback.
Movimento real de estações no referencial terrestre não é fornecido por
esse arquivo. O [PCK genérico](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc)
adverte contra uso deIAU_EARTH para alta precisão; sua limitação não pode
ser ocultada sob um rótuloECEF de precisão maior.

## Leitura vinculada à solução

Selecionar somente o corpo físicoTerra399 ativo. Usar seu centro EVOLUÍDO
na fase confirmada, sem repor a posição pelas efemérides. A época será
`ET0 + t*time_unit_s`, convertida pelo LSK fixado para UTC/ano decimalIGRF.
Não aceitar ano independente no formulário nem aceitar uma época obsoleta.
Domínio efetivo é a interseção da orientação, da cena e doIGRF14 adotado.

O ponto é construído com latitude/longitude/altura do elipsoideWGS84 em
eixosITRF93. Isso define uma geometria de modelo; não é transformação de
coordenadas de uma estação geodésica medida. O vetor de posição relativo
e o campoIGRF são transformados porITRF93→J2000 na mesma época. Somar a
posição daTerra para localizar a sonda na dinâmica e rotacionar o vetor
J2000→GALACTIC para a exibição. Translação afeta posição, nunca o vetorB.

O [IGRF14](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field)
descreve o campo principal terrestre. Reutilizar a síntese própria já
comparada aoFortranBGS e os coeficientes cujoSHA já está fixado. A síntese
não inclui tempestades nem ambiente externo. Não converter estatística
global de erro em barra de erro local. Não assumir campo0 quando indisponível.

Para o ano decimal, usar a fração de dias/calendário gregoriano deUTC entre
os inícios dos anos, respeitando ano bissexto. Se a conversão fornecer um
segundo intercalar `:60`, recusar explicitamente essa amostra até adotar uma
convenção própria; a dinâmica continua. Não arredondar para outro dia em
silêncio. IGRF usa1900≤ano decimal≤2030, e este instrumento mantém a faixa
geodética já validada de0–1000km.2025–2030 é variação secular prevista.

## Critérios prévios

1. Fontes/coeficientes/PCK/LSK com hashes antes da execução; estadosSSB e
   orientaçãoIAU anteriores preservados com carga/descarga do novoPCK.
2. Confirmar que a sínteseIGRF permanece com o mesmoAST; verificar as58
   fixturesFortran fixadas sem sobrescrever recibos anteriores. Limite já
   vigente de1nT por componente; registrar o valor realmente medido.
3. Em cinco épocas cobertas e seis posições geodéticas, conferir rotações
   inversas/ortogonalidade/determinante, norma deB e consistência de posição
   no frame da simulação. Limites numéricos: erro da matriz≤2e−14, norma deB
   preservada em≤1e−18T, posição ida/volta≤1mm. Isso mede consistência do
   transporte, não precisão observacional do campo ou doEOP.
4. Dois instantes separados de6h devem rotacionar posição e vetor no frame
   inercial; a variação secular segue o ano calculado. Conferir data/ano
   contra cálculo de calendário independente, inclusive ano bissexto.
5. Recusar corpo/guard/posição inválidos, booleanos e não finitos, época
   fora da cobertura, longitude/latitude/altitude fora do domínio e segundo
   intercalar não contemplado. Nenhuma recusa modifica fase, câmera ou
   arquivos. Ler e ocultar campo não alteram órbitas de centros neutros.
6. Depois da função/worker, integrarAPI/UI com metadados de época/frame,
   fonte, indicação de previsão e amostra fixa após evolução/restauro.
   Jornadas nativas/capturas próprias continuam exigidas.

Rotação cinematográfica de um marcador não muda esse provedor científico.
Aplicação deLorentz e partículas éIS-4; linhas/mapas e evolução conjunta
precisam compartilhar a mesma leitura/época antes de obter aceite. JRM33,
campos lunares, correntes externas e vento solar continuam etapas distintas.
