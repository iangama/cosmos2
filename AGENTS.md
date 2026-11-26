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
2. Ao retomar com `cosmos2` ou `cosmos 2`, revisar primeiro a parte "Agora"
   da diretriz em CAMADAS-QUATRO-FORCAS.md e priorizar o que cabe nesta fase,
   antes de executar outras frentes. Ler apenas as seções da etapa ativa.
   A palavra de retomada, sozinha, não indica término dos testes manuais;
   enquanto não houver essa indicação, trabalhar fora da sessão interativa.
   O painel integrado permanece requisito do produto final, para depois.
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
Durante os testes manuais do dono, prevalece a restrição posterior da seção
"Integração visual final e testes manuais" abaixo.

Documentação para o dono em português brasileiro. Usabilidade, imagem,
estabilidade e física são critérios de entrega; contar funcionalidades ou
testes não substitui o aceite da experiência. Preservar unidades, época,
referenciais, procedência e incertezas. Distinguir dados observados, modelos,
geração procedural e efeitos de exibição. Não prometer física unificada das
quatro forças em todo o universo nem desempenho ainda não medido.

## Curadoria permanente da experiência — pedido de 14/11/2026

O dono mostrou uma bancada vazia, erro de arquivo científico ausente e
dificuldade com um botão do painel original que apenas amplia a área.
Validar pelo mesmo atalho, painel e botão que ele usa, com mouse/teclado
comuns. Acesso direto por URL, API ou JavaScript é evidência complementar;
não substitui a jornada real. Conferir descoberta, abertura, controles,
resultado, leitura, recuperação de erro e retorno ao Atlas. Botões precisam
cumprir o rótulo; painéis, foco, rolagem e estados de carregamento/erro devem
ser compreensíveis. Curar o conjunto da experiência, não só esse exemplo.
Separar claramente candidata isolada testada da versão acessível ao dono.
Reproduzir e corrigir o caminho original antes de contabilizar sua entrega.

## Integração visual final e testes manuais — pedido de 14/11/2026

Reafirmado em 15/11/2026 com pedido de registro no núcleo do projeto e
separação entre agora e produto final. O requisito e seus critérios de aceite
estão em [CAMADAS-QUATRO-FORCAS.md](CAMADAS-QUATRO-FORCAS.md), seção
"Integração da visualização na versão final".

### Agora

Malha espacial e Camadas têm problemas relatados e seguem pendentes de
triagem/correção. Verificações separadas são aceitáveis nesta fase, sem
constituir aceite da experiência integrada. Não implementar a reorganização
visual agora. Enquanto o dono testa manualmente, não abrir/fechar o aplicativo,
trocar sua versão/processo, navegar, selecionar controles, mudar câmera ou
rodar automação na tela. Pode registrar achados e trabalhar fora da sessão
interativa. Não retomar manipulação da interface sem indicação do dono de
que os testes terminaram; depois, priorizar os defeitos dos percursos reais.

### Atualização de 20/11 — autorização e seleção manual

Depois do relatório de pendência nativa, o dono respondeu “Continue o que
precisar” e reiterou “Continue”. Essa autorização posterior permite a
curadoria funcional necessária pelos atalhos e controles reais, preservando
a sessão antes de qualquer troca. A restrição temporária acima não deve
ser usada para pedir autorização rotineira novamente.

Na sequência o dono relatou, repetidamente, que a seleção de opções
continuava inviável no uso manual. Priorizar esse defeito. Mudar o valor de
um select com setas, DOM ou API não comprova a seleção pelo mouse: abrir a
lista, conferir as opções visíveis, clicar, rolar e cancelar na janela real,
incluindo100% e150%. Registrar separadamente o que foi efetivamente testado.
A integração visual final continua adiada nesta fase.

### Aceite da experiência — pedido do dono em21/11/2026

O dono declarou: “Processo de experiencia do usuario substancialmente melhor,
tudo citado no ultimo ciclo do dia20 corrigido de forma correta. Faltam so os
ajustes de integração mas isso é para o fim do projeto”. Registrar esse aceite
da experiência corrigida no ciclo20; não convertê-lo em aceite científico ou
em conclusão de marcos. Não repetir sua curadoria sem novo defeito ou alteração
que justifique. A integração visual permanece para o fim. O dono pediu listar
o trabalho do ciclo de5horas e continuar; priorizar as pendências técnicas e
científicas após concluir a compatibilidade de arquivos já em desenvolvimento.

### Produto final

Explorar, Forças fundamentais, Malha espacial e Camadas devem compartilhar
uma visualização principal, comandada por um painel único retrátil. O painel
terá segmentos expansíveis/recolhíveis e caixas ou controles simples para
selecionar corpos/modelos e ligar as visualizações desejadas, incluindo
planetas, gravidade e modelos nucleares. Testes e experimentos podem ter
áreas próprias. Esse resultado é obrigatório no fechamento de C2-16/17,
com aceite pelo caminho comum do dono; permanece não implementado e pendente.

## Cota e registro

Acompanhar as janelas de 5 horas e semanal por telemetria da sessão atual.
Não inferir porcentagens por tokens, contexto ou tempo decorrido. Em 8% ou
menos, salvar passagem e continuar no escopo autorizado até conclusão,
bloqueio real, esgotamento ou pedido de parada. Leitura indisponível ou antiga
deve ser registrada como tal. Nunca contornar limite esgotado.

## Identidade e republicação Git — pedido de 26/11/2026

O dono excluiu o repositório remoto anterior por atribuição incorreta de
commits e autorizou republicar o estado atual corretamente. O destino continua
sendo o repositório público https://github.com/iangama/cosmos2. O checkout de
fontes continua em /mnt/c/Users/Ian/cosmos2-github-snapshot-20261103; a pasta
principal Cosmos2 permanece sem Git e com sua sessão de execução preservada.

Use user.name=Ian e user.email=113548582+iangama@users.noreply.github.com.
Autor e committer devem corresponder a essa identidade. O Git do WSL foi
corrigido, com cópia de sua configuração anterior guardada localmente.
Ative core.hooksPath=.githooks e execute scripts/verify-github-authorship.py
--history antes de publicar. Os hooks verificam a criação e o envio de commits.
Preserve bytes conforme .gitattributes e confira os hashes do inventário.

O novo main começa com um histórico limpo. O diretório Git antigo fica em
/mnt/c/Users/Ian/.cosmos2-git-history-before-republish-20261126 e não deve ser
usado como ancestral do novo main. Referências antigas em evidências são
históricas; não reescrever resultados científicos para trocar IDs de commits.
Esta autorização é para republicar o estado atual; não altera as instruções
vigentes para publicações futuras nem o próximo passo científico.

Pedido posterior do dono em26/11: “Quando acabar e hospedar certinho pode
parar os trabalhos”. Concluir a publicação e a confirmação no GitHub e então
parar. Não retomar a implementação científica neste pedido.
