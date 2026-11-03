# Mistura Coulomb — alinhamento da constante de referência B, 28/10/2026

Execução A REPROVADA e preservada em ZIP/recibo/bruto Fortran. Os dois
primeiros casos passaram. No terceiro, Cv da polarização eletrônica diferiu
1,00311e−4 relativo, acima dos 5e−5 do contrato. Não há aceite A.

Diagnóstico por inspeção: FSCRliq8 de eos22.f usa o coeficiente Thomas–Fermi
arredondado `0.2513`, com comentário que o identifica com
`(18/175)(12/pi)^(2/3)`. O MESA26.4.1 e o modelo Python calculam a expressão
completa. A diferença da constante é amplificada nas segundas derivadas.
Por isso os valores de Cv não devem ser comparados como se as constantes
de ambos os modelos fossem idênticas.

Antes da execução B, definir duas referências:

1. Código ORIGINAL dos autores, binário e resultados preservados: medir os
   resíduos em todos os 12 casos e reportá-los; a comparação A continua
   reprovada no limite original. Não afirmar concordância abaixo de5e−5
   com a versão arredondada quando isso não ocorrer.
2. Nova cópia Fortran, explicitamente MODIFICADA somente na constante CTF:
   trocar `Zion**2*.2513*(Z13-1.+.2/sqrt(Z13))` pela mesma expressão com
   `(18.d0/175.d0)*(12.d0/acos(-1.d0))**(2.d0/3.d0)` no lugar de `.2513`.
   Nenhuma fórmula de derivadas é alterada. Arquivo/binário/manifesto
   próprios, hashes dos dois e receita de substituição única preservados.

Comparar o modelo ao Fortran alinhado no MESMO limite de5e−5. Manter
mpmath50dps/AD, diferenças e Maxwell nos limites originais. Isso alinha a
definição de um coeficiente do ajuste e não é validação física adicional.
Não modificar o modelo Python para esconder a diferença da referência A.
