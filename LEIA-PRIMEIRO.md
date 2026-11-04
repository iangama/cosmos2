COSMOS2 — RETOMADA 04/11/2026 — FLUXO PERSISTENTE ATIVO

Ler AGENTS.md. Sem subagentes. Trabalho local contínuo autorizado; 8% da cota
é checkpoint, não parada. Usar telemetria real da sessão para 5h e semanal.
Preservar Cosmos/Revenant, instalação3.13 e sessão do dono SHA256
 ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825.
Sete dos21marcos v1 têm aceite; não afirmar aceite integral IS6/v1.

PRÓXIMO EXATO — NÃO DUPLICAR PROCESSOS
Existe um fluxo Windows destacado: scripts/run-is6-k5-import-flow.py
--label20261104a. Wrapper23228/worker18196. Estado e logs:
output/is6-k5-import-flow-20261104a.{json,log} e ...-errors.log.
Consultar o estado antes de lançar qualquer etapa. O fluxo:
1. Aguarda os dois CPU stores J/J2, já em execução nesta retomada.
2. Roda verify-is6-layers-import-service.py --label20261104l (usa Storev2/J2).
3. Roda perfil K4 I, audita desempenho e saída normal.
4. Só com H/J2/L/I/processI aceitos constrói0.21.0 e inicia primeira jornadaM.
5. Audita processoM e termina; reinícioN, revisão visual e perfilK5 ficam para
   o agente. Qualquer falha interrompe o fluxo e preserva diagnóstico.
Fontes do fluxo/estágios estão seladas enquanto ele executa. Não editar.
Se falhar, examinar recibo/logs e criar versões novas, preservando executadas.

CPU J/J2 — EM EXECUÇÃO, NÃO DUPLICAR
CLIunified J98538/J214419 (IDs da sessão corrente; use recibos após retomada).
Scripts verify-is6-layers-import-store.py e ...-v2.py, labels20261104j/j2.
Pastas output/is6-layers-import-store-20261104j/j2; recibos próprios em evidence.
Ambos testam8combinações,24registros,recusas/falhasI/O/reabertura; sem aceite
até accepted=true. V2 evita reconstruções redundantes ao projetar resumos;
read/write ainda validam origem e destino completos.

PERFIL K4 I — HOST PRONTO, COLETA AINDA NÃO INICIADA NESTE CHECKPOINT
output/is6-layers-storage-host-profile-k4-i-20261104.*,
app25320/server13340. Não abrir outro host. Fluxo inicia driver-v2 label20261104i
após CPUs. Mesmos planoF/candidata0.20.1/4janelas/240comandos. Evitar tarefas
CPU/GPU/IO pesadas durante captura. Processo usa auditorstoragev4.

ESTADO ACEITO
0.20.1 nativoE/F:11confirmações,6recusas,12imagens revistas100/150%,
reinício com nova identidade viva,4visibilidades e cancelamentoHTTP real.
Processos E-r2/F0/0,semprocessos próprios. E original foi auditado cedo demais;
E-r2 preserva a recusa anterior e distingue PID23368 reutilizado por svchost.
Recibos evidence/is6-layers-storage-native-20261104e/f.json,
is6-layers-storage-visual-20261104f.json,is6-layers-native-process-20261104e-r2/f.json
e is6-layers-storage-cut-20261104f.json. Relatório K4-RESULTADO-20261104B.md.
PerfilG RECUSADO:helperCEF transitório28536 na RAM40s/janela1 fora do inventário
GPU. Não relaxar auditor. Gcoletado/processos0/0; falta perfilK4aceito.
PerfilK3 0.19.1 aceito,sem transferência para0.20.1/0.21.0.
K5A H ACEITO:24conversões,229recusas,24reaberturas em intérprete novo;
8originais intactos. evidence/is6-layers-migration-20261104h.json.
Fontes congeladas: output/is6-layers-migration-staging/is6_layers_migration.py.
Relatório IS-6-COEXISTENCIA-MIGRACAO-K5-RESULTADO-20261104.md.

K5 PRODUTO — FONTES PREPARADAS; SEM ACEITE NATIVO
Contrato IS-6-COEXISTENCIA-MIGRACAO-K5-CONTRATO.md; nativo próprio em
IS-6-COEXISTENCIA-MIGRACAO-NATIVA-K5-CONTRATO.md. Staging na pasta de migração:
Storev1/v2,import_laboratory,server-import.py eui/*. Prévia/cancelar/importar
novo ramo, origem incorporada em registro atômico, UIuploadJSON8MiB e endpoints
exclusivos32MiB. Builder prepare-is6-layers-import-product.py exige provas.
Launcher/start/verificador/driver/process-auditor import próprios preparados.
PrimeiraM usa legadoCPU terrestre0.1.0 e exportação joviana realK4 deE;
prévia/cancelar,arquivo alterado/préviaobsoleta,restaurar/salvar/ramificar/exportar.
Esperadas8imagensM. Fluxo cria host k5-first-m-20261104 e label20261104m.
SeM eprocessoM aceitos: abrir hostimport k5-restart-n-20261104; driverimport
--label20261104n --phase restart --seed-label20261104m. Esperadas6imagensN.
AuditarprocessN; rever14imagens e consolidar cut próprio; preparar perfil0.21.
Não promover nem transferir perfil anterior. Nenhum cut/perfilK5 existe ainda.

DEPOIS
K5D saves apenas espaciais ainda pendentes. Exemplo real0.18.2 saved.json é
solarNAIF10,malha1–8Rref,65×96,ampliação200; não há modelo magnético interno
adotado para esse corpo. Não inventar B=0 nem renomear como composto. Contrato
próprio precisa preservar vista/seleção e declarar qualquer nova amostra/malha.
Depois integração geral,expansão de catálogo eGR adicional seguem no plano.

BACKUP AUTORIZADO
GitHub público https://github.com/iangama/cosmos2; checkout separado
../cosmos2-github-snapshot-20261103. Original continua SEMgit. Snapshot parcial
de fontes/evidências, sem runtimes/sessões pessoais/ZIPs; não é instalador nem
pacote integralmente reproduzível. inventory SHA confere arquivos selecionados.
Scripts sync-github-source-snapshot.py e recibos github-source-sync-b/c/d.
Conferir git log/status para a sincronização mais recente; avanço desta retomada
está sendo commitado. Não confundir checkout de backup com workspace original.
Histórico anterior da passagem preservado em output/handoff-archive/.
