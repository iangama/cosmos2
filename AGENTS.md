# Cosmos2 — instruções de continuidade

## Pedido e autorização

Em 11/10/2026, o dono pediu começar do zero, investigar SpaceEngine,
Universe Sandbox, OpenSpace e Celestia, elaborar um plano profundo e
registrar **cosmos2** como palavra de retomada. Pedido literal:
“Primeiro faça o plano e dps tomamos as medidas”.

O pedido inicial autorizava pesquisa e planejamento. Autorização posterior
em 11/10/2026: “Vc n vai construir o projeto não?” e “Eu quero que mostre como
esta o plano atualmente e dps ja siga trabalhando”. A implementação local
está autorizada, começando por C2-00 e avançando no plano conforme os resultados.
Inclui dependências necessárias, downloads proporcionais, builds, execução
Windows, testes e benchmarks. Não pedir autorização novamente para essas
etapas rotineiras. Despesas e publicação não foram solicitadas.

Em 12/10/2026, o dono pediu aumentar quantidade e qualidade do conteúdo,
interações gravitacionais, verificação de campos eletromagnéticos e distorções
gravitacionais. Plano 3.0 incorpora esses requisitos na v1 ampliada, com
21 marcos (C2-00–20). C2-10 é entrega intermediária; C2-17 é a candidata final.
Correção posterior do dono: forte/fraca não ficam para depois. Começar pelas
quatro forças, palcos científicos e controles separados de atuação e visualização.
QUATRO-FORCAS.md registra o pedido e prevalece sobre adiamentos da revisão2.0.
Consultar ESCOPO-CIENTIFICO.md na etapa pertinente. As palavras `cosmos2` e
`cosmos 2` retomam este projeto. Não tratar o protótipo simples como escopo final.

Em12/10, o dono pediu revisar o roadmap inteiro, pesquisar além das ideias
anteriores e devolver etapas/ciclos como noRevenant antes de aplicar mais.
ROADMAP-GERAL.md revisão4.0 registra27marcos:21da v1 (IDs conservados) e6de
aprofundamento proposto. C2-00 aprovado;26sem aceite completo. Horas/ciclos
estimam esforço restante, nunca janelas de cota. Pesquisa/plano completos
podem ser lidos nesta revisão; nas retomadas ler só a etapa ativa. C2-21–26
permanecem propostas de expansão, sem alegação de implementação/aceite.

Correção posterior12/10: o dono fixa um mês e manda calcular por quantidade
semanal. PLANO-UM-MES.md revisão4.1 governa calendário/orçamento de uso.
Retirar previsão9–55meses e horas não calibradas da4.0 do acompanhamento.
Meta12/11/2026; telemetria recente indica~6cotas completas300min equivalentes
por semana e25–27no mês. Não são horas executadas nem prova de que26marcos
cabem no prazo. Preservar requisitos/rigor e apresentar avanços/pendências reais.

Correção do dono na retomada de 11/10/2026: houve interrupção por limite de
uso durante a finalização do plano. Um pedido de continuidade com esse trecho
deve retomar o trabalho indicado, sem apenas reapresentar um resumo de entrega
ou atribuir à interrupção um encerramento normal. Conferir o estado real dos
arquivos, resolver pendências e registrar o avanço. Instruções posteriores
do dono prevalecem sobre a interpretação gravada por um agente no resumo.

## Separação

- Pasta própria: `/mnt/c/Users/Ian/cosmos2`; produto e arquitetura novos.
- Preservar `/mnt/c/Users/Ian/cosmos` e `/mnt/c/Users/Ian/revenant`.
- Não copiar automaticamente código, ambientes, sessões, aceites ou dados do
  Cosmos anterior. Fontes públicas podem ser avaliadas novamente por mérito.
- “Do zero” significa um novo projeto; bibliotecas e bases abertas podem ser
  propostas, identificando origem, licença e adaptações. Não equivale a
  reimplementar todo algoritmo conhecido.
- Godot não é obrigatório. A escolha técnica permanece condicionada à
  avaliação descrita no plano; uma recomendação não é um teste executado.

## Retomada

Pedido do dono em18/10: incluir malha espaço-temporal e camadas semelhantes
para todas as forças, incluindo campos eletromagnéticos dos corpos que os
possuem. CAMADAS-QUATRO-FORCAS.md integra o escopo obrigatório da v1. Depois
do relatório pontual, o dono revogou a parada e autorizou voltar ao trabalho
contínuo; seguir a preferência de cota vigente.

1. Ler `LEIA-PRIMEIRO.md` antes de explorar pastas ou pesquisar novamente.
2. Ler apenas os documentos/seções apontados para a etapa ativa.
3. Separar resultados medidos, fatos de fontes externas e metas propostas.
4. Atualizar o resumo após avanço material e antes de encerrar.
5. A preferência de trabalho contínuo vale para a implementação autorizada.
   Concluir apenas o planejamento ou um marco não encerra a construção.
6. Não delegar a subagentes sem pedido explícito do dono.

## Qualidade e ciência

### Uso da tela — pedido do dono em 14/10/2026

Após perguntar por testes sem tomar o foco enquanto joga, o dono esclareceu:
“Pode manter da forma original, quero que vc tenha acesso a tudo para ficar
o melhor possível”. Esta é a preferência vigente: testes completos, acesso
ao simulador, interface, capturas, teclado/mouse dirigidos ao aplicativo e
benchmarks nativos continuam autorizados. Não sacrificar qualidade para
evitar abrir a janela e não exigir nova liberação rotineira da tela.

Documentação para o dono em português brasileiro. Usabilidade, imagem,
estabilidade e física são critérios de entrega; contar funcionalidades ou
testes não substitui o aceite da experiência. Preservar unidades, época,
referenciais, procedência e incertezas. Distinguir dados observados, modelos,
geração procedural e efeitos de exibição. Não prometer física unificada das
quatro forças em todo o universo nem desempenho ainda não medido.

## Cota e registro

Acompanhar as janelas de 5 horas e semanal por telemetria da sessão atual.
Não inferir porcentagens por tokens, contexto ou tempo decorrido. Em 8% ou
menos, salvar passagem e continuar no escopo autorizado até conclusão,
bloqueio real, esgotamento ou pedido de parada. Leitura indisponível ou antiga
deve ser registrada como tal. Nunca contornar limite esgotado.
