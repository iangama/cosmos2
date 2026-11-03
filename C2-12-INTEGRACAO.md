# C2-12 — integração e aceite pendentes

Registro de trabalho de 21/10/2026. O marco continua parcial. Os perfis
congelados validam os recortes declarados; a experiência integrada precisa
de evidência própria antes de qualquer promoção.

## Próximo recorte

1. Concluir e auditar a nuvem de 10 mil partículas/128 fontes fracas da
   candidata F, preservando a tentativa interrompida c212timesrca. A leitura
   do sinal do coletor agora aguarda arquivo completo e legível, dentro do
   mesmo prazo de 15 s; nenhum critério de quadros, ciência ou recursos muda.
2. Congelar F somente com os três perfis aceitos, exigindo também a repetição
   adicional D da nuvem após o diagnóstico registrado em
   C2-12-DIAGNOSTICO-TAXA-20261021.md. Preservar a rejeição B. Fechar normalmente e
   restaurar o instalado 3.13 antes de abrir outra candidata.
3. Criar uma cópia de integração com armazenamento próprio. Preservar F,
   o núcleo científico 0.4, o helper da nuvem e o motor já medidos.
4. Revisar a interface real e os percursos abaixo; corrigir os problemas
   observados nessa nova cópia e medir de novo as alterações relevantes.

## Lacunas identificadas na leitura do produto

- A operação científica `update_test_particle` existe e tem validação
  transacional, mas a interface do laboratório pequeno não permite editar
  posição, velocidade, carga e massa da partícula de teste. J7 exige esse
  percurso. A escolha de espécies de referência precisa de constantes com
  procedência e de passo/ritmo apropriados, sem esconder as condições.
- A leitura exportada inclui força de Lorentz, mas a interface destaca
  somente os campos. Mostrar força e trabalho/energia no instante declarado
  é parte do aceite das cinco experiências.
- Os painéis da cópia F são longos e os eixos são proeminentes, conforme a
  revisão visual já registrada. Conferir a área útil da cena, legibilidade,
  acesso aos controles e uso em zoom de 100% e 150% antes de escolher o ajuste.
- Conferir alternância Atlas → forças → laboratório → nuvem → Atlas,
  restauração de câmera/seleção e ausência de camadas e workers órfãos.

## Percursos de aceite

| Percurso | Evidência exigida |
| --- | --- |
| Cinco experiências | Elétrica, hélice, E×B, dipolo e Coulomb: carregar, evoluir, pausar, editar, medir e comparar com referência no mesmo instante. |
| Partícula definida | Editar posição, velocidade, carga e massa pela interface; conferir SI, revisão, delta da intervenção e futuro; entrada inválida preserva o estado. |
| Força e energia | Ler contribuição elétrica/magnética, força total e energia/trabalho disponíveis no modelo; exportação conserva fontes e unidades. |
| Atuação/camada | Quatro combinações para cada contribuição suportada, incluindo E/B independentes e potencial; ocultar preserva resultados. |
| Persistência | Salvar fase/vista/tempo, fechar normalmente, reabrir e reproduzir continuação; arquivos anteriores exigem migração explícita quando aplicável. |
| Navegação | Alternar os palcos pelas ações visíveis; restaurar câmera, limpar camadas e manter os controles das quatro forças acessíveis. |
| Imagem e acesso | Capturas reais em 1080p, zoom 100% e 150%; cena utilizável, texto legível, formulários sem sobreposição e ação de pausa acessível. |
| Desempenho | Repetir os perfis afetados após a integração, com os mesmos limites e recursos, antes de qualquer aceite final. |

Campos associados a corpos e épocas continuam em C2-13; malha relativística
continua em C2-14/15. Forte/fraca permanecem obrigatórias na v1. Este registro
não aceita essas entregas nem encerra o C2-12.

## Avanço e revisão de 21/10

F foi congelada com 128/potencial e duas rodadas próprias da nuvem aprovadas;
a rejeição B e os diagnósticos continuam preservados, sem atribuir uma causa
não estabelecida. O instalado 3.13 foi restaurado e conferido antes de G.

G mantém todos os arquivos dos núcleos e workers byte a byte. Seu laboratório
pequeno tem edição da partícula de teste, referências de carga/massa,
instrumentos SI e um painel por vez, com pausa fixa e escala 100–150%.
Vinte casos escalares independentes dos instrumentos, o percurso CEF com
17 verificações e zero erros JS, 16 combinações das quatro forças e a
retomada com futuro exato de 777 passos passaram. A revisão de duas capturas
do layout pausado foi registrada. Os três perfis próprios G ainda estão em
medição; fonte, configuração e runner ficam intactos durante as capturas.

Depois de congelar esse recorte, a próxima revisão de integração deve cobrir:

- A nuvem ainda usa dois painéis e perde área útil ao ampliar a interface.
  Aplicar a mesma organização por ferramentas e manter seleção, camadas e
  pausa acessíveis em 100% e 150%.
- A API da nuvem já permite configurar até 128 fontes por `set_model`, com
  validação transacional. Sua interface só oferece editar campos uniformes.
  Expor criar/selecionar/editar/remover fontes sintéticas pela interface,
  aproveitando essa operação existente, com unidades, exclusões, fontes
  congeladas das medições e salvar/retomar próprios.
- No laboratório pequeno, a legenda fixa da cena nativa permanece no HTML
  do modo canvas. Conferir e corrigir a legenda ao alternar para a projeção
  interativa; o fator gráfico 10⁹ pertence à cena nativa.
- Capturar e revisar as cinco experiências com campos/linhas/potencial onde
  aplicáveis e trajetórias observadas, incluindo a alternância de vista. O
  layout pausado sem mapas não aprova esse conjunto.
- Conferir o save parcial da nuvem: a leitura do código mostra que o parent
  relata erro de gravação de preferências como falha de exibição e o botão
  sobrescreve a mensagem com sucesso completo. Separar confirmação da fase
  e das preferências, testar falha real de IO e impedir sucesso completo
  quando a vista não foi gravada. A correção já feita no laboratório pequeno
  não demonstra que a nuvem passou por esse caso.

G foi congelada após os três perfis próprios aprovados: 128/potencial/nuvem,
com p95 máximo de 17,052/17,099/18,122 ms e taxas mínimas de
0,999740/0,999037/0,998676 s/s. A nuvem passou também pela referência DOP853
independente (erro máximo de trajetória 3,4901e-5) e energia estática total.
Archive `evidence/c212-em-integration-candidate-20261021.tar.gz`, SHA
`8fd132671504eb33632f398e7cc7846b5f6cccf499304c24e2e7a21f35641fd7`.
Não houve promoção. A preparação H foi escrita em scripts separados e ainda
exige cópia, execução e verificações próprias.

Esses itens ainda precisam de execução e aceite próprios. Não editar uma G
congelada para realizá-los nem promover G alegando que a experiência inteira
ficou concluída.


## Integração H em execução —21/10

Cópia H criada com armazenamento próprio e núcleos/workers byteiguais a G.
A organização da nuvem, editor de fontes e save parcial foram implementados.
O primeiro CEF encontrou o limite HTTP herdado de 8.192 bytes ao configurar
128 fontes; tentativa e fonte foram preservadas em
`output/em-cloud-editor-before-api-fix-20261021.tar.gz`, SHA
`784c7e81c932241163f3e16a15e964ffbdd15bbf5b8e9b6c306b6ccc1709f1c7`.
Somente `/api/em-cloud/command` passou a admitir até 262.144 bytes, mantendo
as validações científicas e os limites dos demais endpoints.

`em-cloud-editor-ui-release1-check.json` passou sem erros JS: rascunho,
criação/edição/remoção, 128 fontes, recusas atômicas, campos SI conferidos por
fórmula escalar, save2/retomada e legacy1 real produzido por G sem reescrita.
Uma colisão real de diretório recusou a gravação da vista: a fase válida foi
guardada, o botão informou save parcial e a cena permaneceu saudável. O save
seguinte recuperou o resultado completo. Layout100/150% passou e duas capturas
foram inspecionadas, com escopo limitado ao editor pausado.

`em-cloud-editor-restart-check.json` passou após reinício normal: fase,
seleções, ritmo e visibilidade retomados; 777 passos exatos contra o núcleo
congelado G, arquivos preservados e três recusas de preferências resseladas
sem alterar fase/vista. Cinco experiências, alternância nativa/canvas e perfis
próprios continuam pendentes; H não foi congelada ou promovida.


## Potencial H — recusa antes dos quadros

H128 passou em `native-em128-c212h128a-review.json`: p95 máximo17,733680 ms,
taxa mínima1,000096 s/s, recursos/conservações aprovados. O percurso de cinco
experiências gerou dez imagens e passou sem JS; a inspeção registrou problemas
de enquadramento/contraste e sobreposição em `em-cloud-editor-five-experiences-visual-review.json`.

O potencial H A parou antes dos quadros com HTTP400; o runner original não
registrava o corpo. Fonte e tentativa foram preservadas em
`native-em128-c212hpota-interrupted-source.tar.gz` (SHA
5ae9f88503320a4d7f9d96636b362d7902560e9cbb457da9f04a7ab788afa4b5).
B, com captura explícita do corpo, confirmou o limite de2s do sampler;
archive `native-em128-c212hpotb-interrupted-source.tar.gz`, SHA
cdd3f1ba07826796d45813efd5ca2181ba4fd247a04540873c2a0043633e8e9f.
Não foram medidos quadros/rotas de potencial em A/B, nem alterados limites.
Não atribuir retroativamente o motivo exato de A a B sem o corpo original.

Diagnóstico isolado com worker real e o mesmo núcleo/fixture/64registros/33²
passou três vezes em1,750–1,875s. A maior parte do tempo está nos nove lotes do
worker (aproximadamente85–207ms cada); pré-validação dos contornos custou
68–90ms e geometria final114–124ms. Recibo
`em-cloud-editor-potential-sampling-release2-diagnostic.json`.
Os dois harnesses anteriores usaram storage fora da base permitida e falharam
antes de medir; fontes e provas preservadas. A hipótese inicial de UTF8 foi
refutada pelo stderr completo: o motivo era o caminho de storage.

Diagnóstico no produto vivo recusou cinco tentativas em~2,01–2,09s, tanto
com o refresh CEF normal quanto suspenso e restaurado. Isso não estabelece
causa de agendamento nem culpa da interface. Recibo
`em-cloud-editor-potential-live-polling-diagnostic.json`; fase preservada.
Verificar um reinício normal antes de escolher uma correção isolada. Não
repetir capturas formais indefinidamente nem reduzir a grade/fontes do perfil.


## Candidata I — avanço em22/10UTC (21/10local)

H foi preservada como candidata INCOMPLETA e não aceita em
`c212-em-cloud-editor-incomplete-candidate-20261021.tar.gz`,207arquivos,
SHA4bb4bd3bb437d728b6df89ca1de4e3b34df82332d5154dcd50ff68488e8efac0.
Instalado3.13 foi restaurado/ready e82arquivos+owner conferidos antes de I.
I tem storage próprio e núcleos/workers byteiguais H/G/F. A geometria de
exclusões0.1.1 preservou toda a saída H, exceto identificação do algoritmo,
em66casos com tangência/ULP/aleatórios/128fontes e máscaras independentes.
Sua montagem passou de74–85 para11–17ms; isso sozinho não resolveu o limite
live2s. Fonte inicial I e recusa live preservadas em
`output/em-framing-before-static-sampler-20261021.tar.gz`, SHA
89ad999cd465f665e0d6656ea488afb9cdfe26e768281b6682037a1774cd7ae5.

Novo sampler de leitura de fontes congeladas usa o helper estático ABI1 já
validado na nuvem, sem chamar sua integração. O worker/core0.4 continua
responsável pela fase. Snapshots reais antes/depois de cada lote de até128
posições confirmam pausa, identidade, referencial, revisão, tempo, modelo e
geração. O protocolo de camadas0.3.0 identifica separadamente o fornecedor
dos valores, seus hashes e a política de fronteiras. Não atribui ao worker
as consultas locais. Todas as fontes contribuem; budget2s/33²/128 preservados.

`em-framing-static-sampler-release2-check.json` passou: comparações de E/B/
potencial/escalas/domínio com o escalar original,1.089pontos/128fontes reais,
64registros numéricos e11recusas de cercas/tempo/respostas/budget. Erros
normalizados máximos7,584e-16/2,397e-16/2,865e-16. Cálculo isolado422ms;
no produto, `em-framing-potential-provider2-live-diagnostic.json` mediu453/500ms
numéricos e972/1.059ms na API, sem erro de exibição. Não é perfil formal.

A primeira comparação encontrou uma fronteira de representabilidade: o
escalar0.4 recusa o prefator magnético que transborda mesmo com momento zero.
O adaptador0.1.1 preserva essa recusa e usa a referência original numa faixa
de32ULPs fora da exclusão, identificada nos samples. Fonte/tentativa inicial
foram guardadas, sem reclassificação. A primeira abertura com o sampler
expôs ordem de importação incorreta; fonte/log e antiga prontidão foram
preservados em `em-framing-before-import-order-fix-20261021.tar.gz`.
Importação corrigida, e prontidão agora exige APIrespondendo e appState na
página real CEF, além da cena. Abertura atual passou as três verificações.

I também prepara enquadramento por matéria/camadas na vista efetivamente
aberta, limites SI dos meshes na câmera nativa, ampliação/inclinação do canvas
e trajetória observada destacada e identificada. View3 guarda scope/zoom do
canvas, com validação de versões1/2 e defaults explícitos. A execução CEF está
em andamento; não declarar esses percursos aceitos antes de seus resultados,
inspeção das capturas, reinício e três perfis próprios de I.

## Retomada de 22/10 — perfis próprios I e limite semanal

Ambos os reinícios normais passaram: pequeno e nuvem restauraram fase,
seleções e preferências e reproduziram exatamente 777 passos contra G.
Câmera nativa e canvas_view3 passaram no pequeno; arquivos e owner preservados,
zero erros JS. As capturas da nuvem em100/150% foram inspecionadas: editor
legível e pausa acessível, sem aceitar a cena inteira ou mapas não presentes.

Runners/auditores identificam I com --framing e prefixos/flags estritos.
Os archives pequenos incluem agora o helper estático e sua cadeia de build.
O potencial guarda a camada numérica inteira por rota; auditor stdlib confere
SI por soma Coulomb independente, exclusões, provider,2s,9lotes de até128,
18cercas implícitas no provider validado e hashes medição/geometria/render.
Preparação passou camada real e nove adulterações, inclusive valores resselados,
64combinações de flags/prefixos e três guardas dos runners. Fonte anterior H
preservada em output/em-framing-before-profile-support-20261022.tar.gz.

I128 c212i128a foi aprovado: p95máx17,429399ms, p9919,283020ms,
taxamínima0,999791806,20pausas≤72,2168ms, recursos e conservações passaram.
Potencial c212ipota aprovado: p95máx17,238570ms, p9918,754245ms,
taxamínima0,998438985,20pausas≤43,0574ms; numérico≤421ms/API≤897,8742ms.
1089amostras/128fontes conferidas em cada rota; erro normalizado E≤2,286e-16,
potencial≤5,815e-17 e Bzero. Núcleo0.4/helper/motor e limites inalterados.

Nuvem c212isrca terminou as três capturas, p95máx17,972901ms,
taxamínima0,998488286,zeroquadros>100ms; auditor próprio ainda em execução
quando a telemetria real atingiu65%5h/0%semanal em11:25:54.222Z.
Não declarar esse perfil aceito antes de ler o recibo final.
Trabalho interrompido por cota semanal esgotada; passagem em LEIA-PRIMEIRO.md.
I continua aberta e não congelada/promovida; revisão final de imagem/camadas,
C2-12 completo, campos dos corpos e malha continuam pendentes.

## Continuidade22/10 — I preservada e revisão visual

Cota renovada (100%5h/100%semanal na retomada). O auditor pendente
`native-emcloud-c212isrca-review.json` concluiu com accepted=true: três
rotas, p95máx17,972901ms/p9918,860100ms,taxamínima0,998488286,
20pausas≤106,299ms,RAM1,23283GiB/WDDM2,98187GiB, referênciaDOP853
erro≤3,4745e-5 eenergia≤1,245e-11. Os três perfis própriosI passaram.

Novo percurso capturou20imagens reais: cinco experiências, vistas nativa e
canvas,100/150%,camadas calculadas e65posições observadas. Núcleos/fontesI,
saves eowner preservados; zeroJS. Todas as imagens foram inspecionadas.
A revisão recusou acabamento final:6r/centro da janela deixam matéria pequena;
legenda longa limita canvas150% a~180–194pixels; algumas capturas canvas
rolam o documento e cortam o cabeçalho. As antigas asserções de pausa e
overflowhorizontal não detectavam esse último problema.

I preservada como recorte parcial com três perfis aprovados, sem promoção:
`evidence/c212-em-framing-candidate-20261022.tar.gz`,269arquivos,SHA
`b89c0e48bd452e69df28aa62c711b45b072af18ab589b9264f4eb2e2bd5013e2`.
Próxima cópiaJ: enquadrar na área útil real e reduzir legenda na cena mantendo
detalhes acessíveis; conferir cabeçalho/altura útil/partículas e repetir os
perfis próprios após alterações. C2-12 continua parcial.

Correção da inspeção acima: a suspeita de corte do cabeçalho foi REFUTADA
pela comparação direta dos pixels: os90pixels superiores das cinco duplasI
nativa/canvas150%são byteiguais. Duas sondasJ também mediram scrollTop0 em
janela/html/body/article. Foi interpretação errada da prévia pelo agente;
não foi demonstrado defeito de rolagem do cabeçalho. Recibo
`em-viewport-header-pixel-diagnostic.json`. Os problemas reais de tamanho
da cena/altura do canvas permanecem válidos e foram tratados emJ.

## CandidataJ — área útil nativa e legenda compacta

J separada de I congelada,storage próprio,núcleos/workers/helpersbyteiguais.
`em_viewport.py0.1.1` enquadra os bounds SI no retângulo livre da interface,
com margem7%,projeção planarSGCT do config ativo e yaw/pitchOpenSpace.
640casos contra matrizes independentes e8recusas passaram; erroprojeção
≤9,095e-13px. A pose real foi conferida por conexãoWSindependente.

Legenda curta na cena; faixa/níveis/referência completos continuam acessíveis
no painelPotencialelétrico. O primeiro percurso recusou canvas150%com283px
dealtura. Tentativas/fontes foram preservadas,sem reduzir300px do critério.
Cabeçalho da cena e espaçamento foram compactados; release2 passou20capturas
de5experiências/native/canvas100/150%,forças/faseiguais aH/I,zeroJS.

JUIrelease1 passou save3/legacy2real/guardas/recusasresseladas/falhaIOreal
comsaveparcial. NavegaçãoJrelease1 passou16combosdasquatroforças,Atlas/labs/
nuvem/limpeza e preservação da fase. Polimento posterior aumenta apenas os
raiosGRÁFICOS no enquadramento/retomada,para preservar visibilidade dos centros
SI; sem rebuild a cada snapshot. Framing mínimo3m evita marcador isolado
gigante;Centrarseleçãosóaparece na vista nativa. Release3 está em execução.

PerfisJ exigem `--viewport --framing --cloud-editor --integration
--time-controls --topic-cleanup`,prefixos/sessãoJ explícitos. Auditores
mantêm os limites e conferem a identidade do helper/provedor já validadoI.
Preparação passou160combosflags/prefixos,9adulterações e3guardas dosrunners.
Isso não é desempenhoJ. Arquivo anteriorI em
`output/em-viewport-before-profile-support-20261022.tar.gz`,SHA
821aebc6e65876536309090d07b60da067c3cd790826b4e96053205495796c8e.
Faltam revisão final das novas capturas,save/reinícios e3perfisprópriosJ.

CheckpointREAL6%/85% em21:09:31.222Z: ambos reinicios finaisJ passaram777futuros
exatos;UIrelease4,cloudUIrelease1 e novas20capturas passaram. PerfilJ128
c212j128a iniciado,sem aceite ainda. Passagem plain-text em
PASSAGEM-COTA-20261022-J.txt. Continuar ate esgotamento real.

Renovacao seguinte:100%5h/84%semanal. J128c212j128a concluido e aprovado
pelo auditor: p95max17,060411ms/p9917,729275ms,minrate0,999244431,
20pausas<=76,1949ms,recursos/conservacoes aprovados. PotencialJc212jpota
iniciado. Nenhuma edicao J/config/runners durante capturas.

PotencialJc212jpota:3rotasconcluidas comquadros eSI1089/128aprovados,
masauditorRECUSOUlatenciaAPI>3000ms. Reprovacao preservada,semampliarlimite.
NuvemJc212jsrcainiciada,aceitesindependentes;naoeditarJ/config/runners
durantecaptura.DiagnosticarAPIaposan uvem.
