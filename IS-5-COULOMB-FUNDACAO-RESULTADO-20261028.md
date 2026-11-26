# IS5/C2-20 — fundação Coulomb e resposta FD, 28/10/2026

**Aceita a fundação numérica com domínio restrito.** Recibo
`evidence/is5-coulomb-foundation-20261028b.json`, fontes e documentos exatos
em `output/is5-coulomb-foundation-20261028b.zip`. Não há nova candidata,
trabalhador ou evolução com Coulomb. A EOS ideal e a rede CNO-II 0.14.0
permanecem preservadas; 206 fontes anteriormente aceitas conferidas por hash.

Implementação própria: `output/is5-coulomb-staging/is5_coulomb.py`.
Contrato anterior ao código: `IS-5-COULOMB-CONTRATO-PREVIO.md`.
Referências primárias locais em `output/is5-coulomb-staging/references`.

## O que foi medido

- 9 estados η=−20..20: susceptibilidade do gás eletrônico FD e derivadas
  de `q=kTχe`, comparadas a polilogaritmos independentes com 50 dígitos.
  Máximo erro escalado 3,33e−15; diferenças finitas 3,45e−9 na escala ne.
- 12 estados de plasma H/He no domínio fraco e quase clássico: energia
  livre DH, P/U/Cv, potenciais químicos e gradientes de composição contra
  diferenciação independente de F(V,T,Ni). Máximo erro de referência
  6,19e−16 relativo; gradientes por diferenças 6,38e−11.
- Maxwell testada separadamente na correção e no total com a EOS ideal;
  máximo 3,29e−10 relativo ao respectivo P. Isso impede que o termo ideal
  grande esconda inconsistência de uma correção pequena.
- 12 pares p+p: screening concorda com a diferença de potenciais químicos
  neutros do mesmo banho. 21 recusas de tipos, composição, domínio e pares.
  Um traço O16 positivo de 1e−30 é recusado; O16 exatamente zero não limita
  o banho. Nenhum limiar de abundância remove espécie positiva.

A pressão de correlação nos 12 fixtures reduz a ideal em 0,1020–0,2548%.
Este intervalo descreve APENAS os fixtures H/He testados, não o Sol.

## Falha A preservada

O teste A foi reprovado no erro relativo de derivadas que tendem a zero
em η=−20; χe concordava em 2,17e−16. O contrato já previa escala explícita
nessa situação. A definição B foi fixada em
`IS-5-COULOMB-VERIFICACAO-B.md` antes da execução, preservando os erros
relativos crus e o ZIP/recibo A. B mudou somente o teste e a definição das
escalas, sem alterar o modelo nem limites físicos.

## Implicação para o passo solar

O fixture solar 15 MK, 1,5e5 kg/m³, XH=0,34 e XN14=0,01 foi recusado:
ΓN14≈1,806; neλe³/2≈0,2157; κλe≈0,891; linearização máxima≈0,361.
Com uma carga O16 de teste no mesmo banho, ΓO≈2,256. Portanto o fechamento
DH clássico desta fundação não pode ser aplicado à zona CNO aceita.

A referência de Potekhin e Chabrier (2012), equações 14–17 e texto seguinte,
também distingue o comprimento de resposta eletrônica do potencial de
contato. A substituição ne→kTχe, sozinha, não constrói uma EOS Coulomb geral
nem valida a taxa de fusão para degenerescência arbitrária.

Próximo: fechamento de misturas além de DH, com componentes de interação
identificados e derivadas da mesma energia livre. A mistura linear pura
também não resolve o limite fraco: avaliar a correção publicada em 2009 e
seu adendo antes de integrar a evolução. Não atribuir o desvio B23 anterior
de 1,7–2,3% a uma causa única nem declarar precisão física por estes testes.
