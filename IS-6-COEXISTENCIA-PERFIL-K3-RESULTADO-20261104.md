# K3 — perfil próprio da interface 0.19.1

Quatro janelas aceitas: Terra/Júpiter estáticos e com visibilidade a2Hz,
30s de aquecimento e60s medidos,1920×1080/UI100%,mesma fase pausada.
Foram auditados 18029 deltas. P95 máximo 14.139ms, p99 máximo 14.484ms,
zeroquadros>100ms. Todos os240comandos concluíram dentro das janelas;
p95 máximo 0.217s e máximo absoluto 0.263s. RAM 1.131GiB, GPU 3.010GiB.

Auditor conferiu modelos,artefatos,receitas,guards,UI/flags nativos,
fase/câmera/limpeza,ZIP/fontes,quadros brutos eGPU schema3 sem erros.
App/servidor encerraram0/0,semPIDs próprios e sessão do dono preservada.

Recibos is6-layers-profile-20261104a.json, is6-layers-profile-audit-20261104a.json
e is6-layers-profile-process-20261104a.json. São latênciasAPI com aUI
real renderizada/polling,não velocidade de digitação humana. O aceite
pertenceà0.19.1;0.20.0 com armazenamento requer seu próprio perfil.
IS6/v1 e migrações ampliadas continuam pendentes.
