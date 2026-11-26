# Admissão B do protocolo de residência — anterior às dez janelas

A revisão de fonte posterior ao preflight Atlas identificou dois formatos
publicados distintos: a malha simples usa `artifact.source.reference_id`,
e o par coordenado usa `artifact.source.body_reference_id`. A revisão2 do
contrato puro respeita esses nomes; o coletor2 importa esse contrato.
Nenhuma fonte do produto mudou. O preflight e as28recusas da revisão1
permanecem como evidência do seu escopo original; não provavam uma janela
de malha simples. Não houve coleta sustentada anterior a essa correção.

O executor lê o payload científico simples diretamente em `result`; para
o par coordenado lê `result.scientific`, conforme cada endpoint. As fontes,
regressões adicionais, executor, controlador e auditor serão selados antes
de qualquer janela nova. Repetir somente o preflight curto do coletor2.
Os limites, dez estados, aquecimento, duração, primeiros66registros e
retenção das transições dos contratos originais permanecem vigentes.
