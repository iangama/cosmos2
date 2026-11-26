# Compatibilidade do centro físico preservado

A preparaçãoA dos recortes foi recusada no teste adicional de igualdade
bit a bit entre599→5 doJUP365 completo e o recorte planetário já preservado.
Os registros deIo501 recém-copiados passaram na comparação bit a bit.
O contrato exige igualdade dos novos recortes com suas fontes e dos dez
estados anteriores antes/depois de carregar esses recortes. Esse teste
adicional entre produtos planetários diferentes havia sido mais estrito.

A correlaçãoA confirmou599/5 e699/6 em quatro épocas, sem diferenças.
A correlaçãoB verificou206épocas, incluindo as bordas de segmentos e seus
vizinhos representáveis.599diferiu em uma época: máximo1,4211e−11m e
2,8298e−14m/s por componente.699permaneceu igual em todas essas épocas.
As diferenças são muito inferiores ao orçamento numérico já fixado de
1mm e1µm/s. Não foram alterados os kernels planetários preservados.

A revisãov2 conserva as duas exigências de igualdade bit a bit do contrato:
novos registros de luas contra a fonte completa, e estados dos dez corpos
anteriores antes/depois de carregar cada recorte. A comparação adicional
dos centros planetários usa o orçamentoSI já fixado e passa a guardar as
seis diferenças máximas, em vez de afirmar identidade entre esses produtos.
A primeira recusa e suas fontes continuam preservadas. Essa revisão não
reduz as exigências das novas luas nem altera a cena0.24.

Evidências: `is6-principal-moons-data-20261111a.json` recusado e
`is6-principal-moons-center-correlation-20261111a/b.json`, na pastaevidence.
Ainda não se atribui uma causa interna específica ao arredondamento na
amostra; a compatibilidade é julgada pelo erro numérico medido.
