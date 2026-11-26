# Perfil composto K5A recusado — 05/11/2026

Candidata0.21.1, plano20261105k5a/executor-v4/driver-owned-v4: coleta terminou
quatro janelas, com prévia PDH pausada validada. Motor, servidor, launcher e
wrapper encerraram0/0/0/0. O auditor-v4 recusou o perfil, sem aceite parcial:
a janela2, Júpiter estático, contém um quadro de580,568612ms, acima do limite
zero quadros>100ms. O quadro medido1264 começa após16,845731s acumulados;
a causa não foi estabelecida. Não atribuir ao produto, sistema, CEF ou coletor
sem diagnóstico. Não remover esse quadro, aumentar aquecimento/limites ou
repetir até obter uma execução favorável. Uma nova medição exige hipótese e
alteração ou controle explicitamente documentados antes de plano novo.

Demais métricas descritivas: janela2 mediana13,3304ms/p95 13,8216ms/p99 14,2270ms.
Janelas1/3/4 não tiveram quadros>100ms, mas isso não as torna aceitas isoladamente.
A auditoria parou na recusa de quadros da janela2; verificações posteriores não
foram completadas pelo auditor. Coleta completa não equivale a aceite.

Recibo bruto: evidence/is6-layers-import-profile-20261105k5a.json.
Auditor: evidence/is6-layers-import-profile-audit-20261105k5a.json.
Diagnóstico descritivo: evidence/is6-layers-import-profile-hitches-20261105k5a.json.
Saídas: output/is6-layers-import-profile-20261105k5a-host/closure.json.
Fontes/planos/artefatos executados permanecem congelados. Produto3.13 e atalho
principal preservados. Perfil espacialP4 de0.22.1 continua aceito; não transferir
seu aceite ao perfil composto0.21.1. IS6/v1 continuam incompletos.
