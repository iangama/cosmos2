# Evolução Coulomb — correção do controle EM,28/10/2026

Identificado durante a execução A, antes de sua conclusão: o teste A supõe
que EMoff mantém toda a composição e temperatura constantes. Isso contradiz
a semântica aceita de atuação, que habilita p+p com forte+fraca, e He3+He3
com forte. Não modificar a física para satisfazer essa expectativa.

Conclusão real de A conferida na retomada29/10UTC (28/10local): os cinco
casos e os controles ideal/prescrito, ideal/térmico e todosoff passaram.
A parou ANTES da assertiva EMoff: weakoff enviou somente `weak=False`,
mas o contrato exige o dicionário completo forte/fraca/EM. A recebeu
`ValueError: Exact explicit physical switches required`. EMoff também
tinha esse erro de forma. B corrige AMBOS os pedidos para esquemas
completos e mantém o controle EMoff conforme a semântica já descrita.

Deixar A concluir, preservando seu script, ZIP, casos e eventual reprovação.
Auditoria B poderá reutilizar os cinco casos Radau/BDF/refinamento e os
três controles anteriores SOMENTE se os casos estiverem completos, os limites
originais passarem e todos os hashes de fontes/artefatos forem idênticos.
Se A falhar em outro ponto, diagnosticar a falha; B não pode aceitá-la por
suposição. Não reeditar o script A nem repetir casos válidos
sem necessidade.

O controle corrigido EMoff exige p+p ativo, capturas radiativas desativadas,
D crescendo, H diminuindo, ν de p+p e balanço de carga/energia preservados.
No estado inicial H/He4+N14, sem D/He3 ou intermediários beta, os demais
fluxos ficam zero dentro do orçamento numérico. Todosoff continua invariante.
Completar em B os controles que A não alcançar (Coulomb sem screening,
tipos/orçamentos e recusa integral de trajetória quente).

Aceite agregado deve citar A como execução reprovada por pedido de teste
malformado e B como auditoria complementar; não converter A em aceita nem
herdar casos com fontes ou resultados alterados.
