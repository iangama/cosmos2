# IS6 — primeira malha utilizável no aplicativo,02/11/2026

Candidata isolada0.18.2,182arquivos. Aceites funcionais/nativos/visuais
concluídos no escopo abaixo. **PerfilC aceito no escopo das quatro janelas; encerramento com vista ativa ainda em verificação.**
Não houve promoção ou substituição do instalado3.13.

O aplicativo oferece corte espacial de referência para Sol,Terra,Lua e
Júpiter:corpo,domínio,33–257anéis,planoXY/XZ/YZ e ampliação da altura.
Sondas exatas consultam métrica,curvatura,distância própria e relógios estáticos.
Mostrar/ocultar mantém artefato e leitura. Save/load/ramos/export preservam
referência e vista; restaurar uma fase arquivada não substitui a órbita atual.

| Prova | Resultado aceito |
| --- | --- |
| ServiçoD | 4grupos,10recusas;matemática/arquivos reais,cena controlada |
| CacheA | 20consultas semreler catálogo;alteração,adulteração,reparo e novo ramo conferidos |
| NativoF | 5grupos,10recusas,quatro corpos e três planos;zero errosJavaScript |
| VisualF | 9capturas100/150%,identificação,geometria,câmera,sondas e brilho revistos |
| PersistênciaB | 7de7checagens em novo host/fase;CEF de ramos/export e arquivo inválido sem mutação |
| VisualpersistênciaB | 2capturas150%,fonte/época/GM/Rref/PCK e controles/arquivo exportado legíveis |

Recibos em `evidence/is6-product-service-20261102d.json`,
`is6-catalog-cache-20261102a.json`,`is6-product-native-20261102f.json`,
`is6-product-visual-review-20261102f.json`,`is6-persistence-native-20261102b.json`
e `is6-persistence-visual-20261102b.json`. As capturasRGB foram conferidas
pixel a pixel contra os PNG nativos. HostsF e persistênciaB encerraram exit0.

A candidata prepara nós ocultos e publica somente depois de ACK e readback
do motor. Cancelamento durante preparação e falhas de ACK/readback após
troca real preservaram a vista anterior. Guard/revisão,disputa da cena,
configurações inválidas e arquivo danificado foram recusados. Fase e sessão
do dono conservadas; ciência,artefatos,renderer e evidências anteriores intactos.

Correções de experiência encontradas pelos testes: carregar o mesmo artefato
agora atualiza os campos da sonda; restaurar outra fase identifica o corpo
arquivado sem remapear seus IDs; câmera acompanha o plano; linhas densas têm
atenuação própria.0.18.0 e0.18.1 permanecem preservadas com seus diagnósticos.

PerfilC aceito: `is6-spatial-profile-20261102c.json` e auditoriaC.
Quatro janelas de30s de aquecimento+60s medidos:65anéis,257anéis,sondas2Hz e
visibilidade2Hz.18016quadros,medianas13,28–13,31ms,p95máximo14,01ms,
p99máximo14,38ms,zeroquadros>100ms.120+120comandos sem erros,100% no
intervalo;p95 de confirmação72,2ms(sondas)/146,3ms(visibilidade). Auditor
conferiu272amostrasexatas. PicoRAM1,13GiB/GPU3,02GiB,abaixo8/5,5GiB.
ColetaGPU schema3 com66amostras/janela,caminhospróprios,status0 e inventários
conferidos. PerfisA eB permanecem recusados,com seus diagnósticos,sem mistura
de janelas. Todos os limites iniciais foram mantidos. HostC app/serverexit0/0.

Fechamento ativoA confirmou app0/server1 em0.18.2. Revisão isolada0.18.3
altera somente is6_laboratory.py e server.py. ServiçoE aceito4grupos/11recusas;
encerramentoativoB aceito em3,36s,app/server0/0,semPIDsrestantes. Ciência,
renderer e todos os arquivosUI são byte a byte iguais à0.18.2. O perfilC e as
capturasF continuam provas da0.18.2; não são anunciados como execuções0.18.3.
ContratoIS-6-PRODUTO-REVISAO-D.md. Sem promoção. Jornada integrada0.18.3
será verificada separadamente.

Esta entrega cobre referência esférica exterior isolada de Schwarzschild.
Altura ampliada é desenho de uma imersão espacial; não é solução óptica nem
dinâmicaGR de muitos corpos. Terra/Lua quase planas nessa escala não indicam
falha da leitura. GM vem da massa arquivada; Rref é fronteira PCK conservadora.
Dependências aceitas permanecem identificadas por caminho/hash no projeto;
a candidata ainda não é um pacote independente.

Ainda faltam percurso conjunto das quatro forças,camadas simultâneas com
perfil próprio,persistência composta,expansão do catálogo e extensõesGR do
plano. A primeira malha não encerra todaIS6 ou a v1. Próximo roteiro registrado
em `IS-6-PERCURSO-INTEGRADO-CONTRATO-PREVIO.md`,para executar após o perfil.
Uso local em `IS-6-MALHA-USO-CANDIDATA.md`.

Consolidação limitada aceita: `evidence/is6-spatial-cut-20261102a.json`,com
ZIP próprio e conferência das182entradas/receitas/recibos. Preserva a distinção
entre base0.18.2 medida e revisão0.18.3 de encerramento. JornadaJ0B recusada: doisgrupos concluídos e10capturas,mas o verificador
clicou em checkbox oculto por details fechado. DiagnósticoCEF0×0 preservado.
A revisão visualB recusou o rodapé antigo e a rolagem horizontal nuclear.
J0C repete os cenários com abertura/hit-test/espera de confirmação; em execução.
A0.18.4 contém os quatro ajustesUI e foi preservada sem teste nativo; diagnóstico
posterior localizou o caminhoexportado emzone-file como causador do overflow.
A0.18.5 acrescenta quebra desse texto. J0D verificará essa candidata com limpeza
nativa,câmera/flags,rodapé e largura100/150%. Nenhuma nova aceitação é antecipada.

Jornada sequencialJ0E aceita em0.18.5:3grupos,7recusas,5limpezas nativas,
10PNG revistos100/150%,zeroerroJS,app/server0/0. Rodapé eoverflow corrigidos
com4arquivosUI;ciência/serviços/renderer iguaisà0.18.3. Relatório próprio
IS-6-PERCURSO-INTEGRADO-RESULTADO-20261102.md preserva oescopo sequencial.
