# Procedência e licença

`is5_coulomb_mixture.py` adapta a expressão escalar EXCOR7 e o ajuste de
polarização eletrônica dos módulos Skye do MESA26.4.1:

- https://github.com/MESAHub/mesa/blob/26.4.1/eos/private/skye_coulomb.f90
- https://github.com/MESAHub/mesa/blob/26.4.1/eos/private/skye_coulomb_liquid.f90

Copyright (C)2022 The MESA Team. LGPL-3.0-ou-posterior. A adaptação segue
a mesma licença. A cópia da licença LGPL está nesta pasta; a GPL incorporada
por referência é preservada como LICENSE-GPL-3.0.txt. Fontes originais
fixadas: output/is5-coulomb-research-20261028/mesa26.4.1-*.f90.

Modificações Cosmos2(2026): reexpressão em Python/SI, diferenciação completa
de composição, OCP clássico com os coeficientes Caillol do artigo de2009,
correção de mistura polarizável do adendo de2009, guardas explícitas e
ausência de limiar que descarte traços. Não inclui rotinas de fase sólida,
extrapolação, correções quânticas iônicas, ajuste de EOS ideal ou interface
do MESA. Isso não constitui instalação nem execução do pacote MESA.

`is5_jet.py` e o acoplamento termodinâmico são implementação própria.
Distribuição futura da biblioteca deve manter fontes modificáveis,
atribuição e licenças; nenhuma distribuição foi realizada nesta etapa.

Referência Fortran eos22.f dos autores é usada somente em verificação
local e permanece separada do produto e da adaptação Python.
