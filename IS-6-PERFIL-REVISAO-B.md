# IS6 — revisão da mediçãoGPU,02/11/2026

PerfilA permanece recusado: as quatro capturas de quadros completaram,mas
o coletorGPU da quarta janela registrou40amostras inválidas em dois contadores
doPID16244,que não pertence ao produto. Status3221228486/0xC0000BC6.
O programa terminou com saída0 e a limpeza foi confirmada. Não reinterpretar
A como aprovado nem descartar suas amostras. Não foi identificada a causa
do contador externo inválido; não atribuir a um aplicativo específico.

Nova coleta limita a consulta aos caminhos concretos de memóriaGPU do
motor/servidor/descendentes,enumerados antes da janela por
`Get-Counter -ListSet ... .PathsWithInstances`. Registrar inventário e caminhos
antes e depois. Exigir que o conjunto de instâncias próprias não mude; novo
processo/instânciaGPU,inventário incompleto,caminho ausente,qualquer status
nãozero,erroPDH ou menos amostras recusam a janela inteira. Não substituir
valores por zero. Processos sem contador exposto são identificados como tais.

Consultar Dedicated/Shared Usage de cada instância própria e Dedicated Usage
dos adaptadores. Preservar todos os caminhos,status e valores brutos na nova
schema3. Guardas do cenário/identidade do executável continuam. Exigir66
amostras válidas abrangendo os60s;mesmos limites de fluidez,RAM,GPU e2Hz de
IS-6-PERFIL-PREVIO.md. Repetir as quatro janelas com novo label/fontesZIP;
não misturar janelasA eB. Auditor próprio confere a seleção e os dados.

Antes: análise dos40erros deA e smoke de3amostras no host próprio. Depois:
perfil novo,somente após preflight aceito. Nenhuma alteração no produto0.18.2.

Referências verificadas em02/11/2026: a Microsoft documenta seleção por
caminhos de instância em
[Get-Counter5.1](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-counter?view=powershell-5.1)
e exige conferir o status dos dados em
[PDH](https://learn.microsoft.com/en-us/windows/win32/perfctrs/checking-pdh-interface-return-values).
A definição do código está na
[tabelaPDH](https://learn.microsoft.com/en-us/windows/win32/perfctrs/pdh-error-codes).
Isso fundamenta o novo método; não demonstra a causa do erro observado.
