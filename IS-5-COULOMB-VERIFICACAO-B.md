# Fundação Coulomb — definição das escalas numéricas B, 28/10/2026

A execução A foi reprovada na primeira derivada em η=−20. Modelo e fonte
do teste A estão preservados no ZIP e recibo `is5-coulomb-foundation-20261028a`.
χe acertou a referência em 2,17e−16 relativo. As derivadas de q em lnT
tendem a zero no limite clássico; avaliar erro relativo ao próprio valor
minúsculo produziu 6,21e−7 e 1,66e−6 por cancelamento de termos em float64.
Isso não foi uma prova de falha da quadratura de χe, nem um aceite.

O contrato original já pede escala explícita quando a derivada tende a zero.
Antes de executar B, fixar:

- χe, q e dq/dne: erro relativo ao próprio valor da referência.
- dq/dlnT e d²q/dlnT²: erro absoluto dividido por ne da referência.
- d(dq/dne)/dlnT: erro absoluto (escala unitária).
- Diferenças finitas de derivadas de q: erro absoluto dividido por ne.

Limites permanecem 2e−9 para referência e 2e−6 para diferenças. Registrar
também os erros relativos crus para que a escala não esconda o cancelamento.
Nenhuma mudança de modelo, domínio físico, EOS ou taxas de reação em B.
Os pontos parcialmente degenerados continuam verificando derivadas
significativas; χe recebe verificação independente em μe.
