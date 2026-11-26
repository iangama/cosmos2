# IS5/C2-20 — EOS não ideal de mistura, resultado28/10/2026

**EOS numérica aceita**, com a comparação B e a auditoria de composição A.
Fontes preservadas em `output/is5-coulomb-mixture-staging`; não há trabalhador,
produto nativo ou evolução com essa EOS ainda. Modelo ideal e 0.14.0 intactos.

Recibos complementares:

- `evidence/is5-coulomb-mixture-20261028b.json`: 12 estados com H/He e
  sementes N14/O16, quatro componentes ii/ie/ee/mistura, referência Fortran,
  diferenciação mpmath50dps, identidades e13 recusas.
- `evidence/is5-coulomb-mixture-composition-20261028a.json`: 96 gradientes
  por diferenças finitas (16 espécies em6 estados), incluindo espécies
  inicialmente ausentes, e3 recusas de traços positivos de alta carga.
- ZIPs de fontes exatas ao lado dos respectivos recibos em `output`.

A energia livre inclui OCP clássico com coeficientes Caillol, polarização
eletrônica PC, troca/correlação eletrônica EXCOR7 e correção da mistura
polarizável do adendo de2009. P/U/Cv e todos os gradientes derivam da mesma
função escalar, com neutralidade e médias de composição variáveis.
Os termos adaptados do MESA26.4.1 mantêm atribuição e LGPL na pasta.

Figura dos12 fixtures, com inspeção visual aceita e sem recomputar ciência:
[PNG](output/is5-coulomb-mixture-figure-20261028a/pressure-components.png)
e[SVG](output/is5-coulomb-mixture-figure-20261028a/pressure-components.svg).
Recibo `evidence/is5-coulomb-mixture-visual-review-20261028a.json`.

## Evidência e limites

| Verificação | Maior erro medido |
|---|---:|
| Fortran com a constante CTF alinhada | 5,402e−7 relativo |
| mpmath50dps, componentes e derivadas | 4,637e−14 relativo |
| Gradientes por diferenciação mpmath | 6,370e−15 relativo |
| 96 gradientes por diferenças finitas, correção e total | 1,379e−9 relativo |
| Maxwell, por componente e total | 1,476e−9 relativo |
| Cv por diferenças finitas | 1,504e−8 relativo |

Passaram invariância por permutação e divisão de espécie idêntica, correção
de mistura exatamente zero quando todas as cargas são iguais, integral
independente da uii publicada e aproximação ao limite DH polarizável. O
último teste é um limite matemático fora do domínio público da zona, não
permissão de extrapolação. Resíduos negativos raw de1e−30 são identificados
e preservados; nenhum clamp. Traços positivos de Fe26 de1e−8,1e−20 e1e−30
foram todos recusados no fixture de acoplamento fora do domínio.

## A reprovação original continua registrada

A comparação A foi **REPROVADA**: Cv da polarização eletrônica no terceiro
caso excedeu5e−5. O Fortran original usa CTF=0,2513; MESA/Python avaliam
a expressão completa desse coeficiente. A receita B criou arquivo e binário
novos alterando APENAS essa constante no comparador, sem mudar o modelo.
`IS-5-COULOMB-MISTURA-REFERENCIA-B.md` foi escrito antes de B.

Nos12 casos B, o resíduo máximo contra o Fortran ORIGINAL foi1,272e−4,
portanto não satisfaz o limite5e−5 de igualdade numérica. Ambos os brutos,
fontes e binários permanecem registrados. O aceite numérico é relativo à
expressão de constantes alinhadas, mpmath e às identidades; não alegar
igualdade abaixo desse limite com o Fortran arredondado.

A aproximação de mistura polarizável de2009 não é exata para qualquer
degenerescência. Os íons são clássicos; não há ionização parcial, campo
magnético, fase sólida, transporte ou estrutura estelar. Precisão numérica
não é precisão física e os resultados não calibram o desvio de pressão B23.

Próximo: screening derivado dos potenciais químicos da mesma energia livre,
e evolução isocórica com balanço energético e comparação Radau/BDF em U.
Contrato anterior ao código: `IS-5-COULOMB-REDE-CONTRATO-PREVIO.md`.
