# Catálogo planetário na candidata 0.23.1

A candidata isolada reúne Sol, oito planetas e Lua na página de dados,
alcançada por Dados e fontes → Catálogo dos oito planetas. A consulta aceita
uma época UTC explícita e exporta posições, velocidades, GM, formas,
orientações e suas fontes. A janela comum vai de01/01/1995 00h UTC a
30/12/2049 23h59min59s UTC.

Os subconjuntos499/799/899 passaram609comparações contra os kernels
completos, com estados relativos idênticos bit a bit. A soma independente
da cadeia SSB teve diferença zero nos seis componentes. A verificação do
catálogo passou em cinco épocas,16recusas e reabertura em outro intérprete,
conservando os estados anteriores e o inventário de kernels carregados.

O teste nativo da0.23.1 percorreu os dez corpos, consultou outra época,
recusou uma data externa conservando a leitura confirmada e exportou essa
leitura. Cinco consultasHTTP inválidas foram recusadas. Motor, servidor,
launcher e wrapper terminaram com quatro códigos zero. A sessão do dono
conservou seu hash.

A revisão visual passou nas capturas100%/150%. A data aparece em formato
ISO explícito. Rótulos e valores permanecem legíveis e a exportação tem
quebra de linha. A0.23.0 teve aceite funcional e recusa visual por data
ambígua e rótulos em inglês. Seus arquivos e recibos foram preservados.

As consultasHorizons conservaram os cabeçalhos das fontes. Marte/MAR099
passou em cinco épocas, com limites prévios1m e1e−5m/s. Mercúrio/Vênus
comparamDE442 eDE441; Urano comparaURA182 eura184_merged; Netuno comparaNEP097
enep098_merged. Os desvios entre essas gerações estão registrados no reciboC.
As duas primeiras versões do verificador externo foram recusadas e
preservadas, incluindo o erro de borda de24,76573µs ao converter o JD impresso.

Recibos de dados, CPU, comparação externa, funcional e visual estão em
`evidence/is6-planet-catalog-*.json`. A fonte dos estados pertence aos
[kernelsJPL](https://ssd.jpl.nasa.gov/sats/ephem/files.html).

A navegação3D ampliada, os perfis próprios da candidata e as luas adicionais
continuam pendentes. A candidata segue isolada, com promoção pendente.
K5A mantém sua recusa e causa em aberto. V1 permanece com7/21marcos aceitos.
