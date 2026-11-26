# Referência dos oito planetas e sete luas

O catálogoCPU ampliado passou com16corpos: Sol, oito planetas, Lua,
Io, Europa, Ganimedes, Calisto, Encélado e Titã. Cinco épocas e25recusas
passaram, com restauração do poolSPICE, preservação de ET/TDB exato e
igualdade em intérprete novo. Os dez registros anteriores permaneceram
iguais. Os arquivos protegidos e a cena0.24 foram conservados.

As fontesJUP365/SAT441 passaram nos MD5 publicados e receberam SHA256.
Seis recortes totalizam32.379.904bytes. Foram206épocas por lua, incluindo
limites de segmentos e vizinhos representáveis,1.236comparações no total.
Os estados relativos copiados são idênticos bit a bit; a cadeiaSSB calculada
independentemente teve diferença zero nos seis componentes. Carregar cada
recorte preservou os estados dos dez centros anteriores e dos baricentros.

A primeira preparação foi recusada por um teste adicional excessivamente
estrito entre o centro599 do pacote completo e seu recorte anterior.
A correlação encontrou uma diferença de14,21pm/2,83e−14m/s em uma época.
A revisão documentada conserva a igualdade bit a bit das novas luas e dos
estados anteriores, e mede essa compatibilidade adicional pelo orçamentoSI
já fixado. A recusaA e suas fontes foram preservadas.

Recibos: aquisição20261111a, dados20261111b e verificação20261111a,
todos `is6-principal-moons-*.json` na pastaevidence. Modelo e módulo ficam em
`output/is6-principal-moons-model-20261111a`. O módulo possui SHA256
`de3c37996011f197bd92210bc4ee3a15daf8833ece471043ed00eb6238083c93`.

Este aceite cobre dados e API em CPU. Comparação externa, cena3D, mapas,
interface e perfil próprios das luas permanecem pendentes. As efemérides
são uma referência geométrica; não constituem dinâmica acoplada dos16corpos.
O aplicativo0.24 continua aberto com os oito planetas e a Lua. V1 segue7/21,
IS6 incompleto e K5A recusado.
