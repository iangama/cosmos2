# Preparação do perfil até10mil partículas de teste

Pesquisa16/10/2026, sem implementação instalada. C2-11 exige um perfil próprio,
separado de256 massas mutuamente ativas e dos perfis128 anteriores.

Contrato candidato: fontes ativas mutuamente newtonianas; população adicional
com massa exatamente zero, N_active explícito e testparticle_type=0. Partículas
de teste recebem as fontes ativas e não reagem nelas nem entre si. Não chamar
essa população de10mil massas ativas. Não reutilizar o validador atual de Session,
que exige todas as partículas ativas e massa positiva, sem ampliar o contrato.

Fontes primárias consultadas:
- https://rebound.hanno-rein.de/simulation/variables/
- https://rebound.hanno-rein.de/ipython_examples/Testparticles/
- https://raw.githubusercontent.com/hannorein/rebound/5.2.2/src/gravity.c
A documentação atual e o exemplo com tipo1 não são a prova do tipo0 instalado.
Verificar na5.2.2 os dois limites do laço de forças, comparar com solução Kepler,
mostrar ausência de reação e de interação mútua, e testar checkpoint/futuro.
Não configurar silenciosamente massas não nulas como tipo0.

Arquitetura pendente: separar identidades, papéis físicos, conservação das fontes,
energia específica das partículas, serialização e transmissão. Evitar40mil nós
de cena individuais. Avaliar buffer de pontos com confirmação de instante e
assinatura de população, desenhando todos os10mil pontos e preservando seleção
individual e exportaçãoSI. Redução visual precisa ser declarada se usada; não
representa o aceite do perfil completo. Medir solver, IPC, cena, CEF, pausas e
memória no mesmo perfil real. Camadas e instrumentos não devem incluir partículas
sem massa como fontes de campo nem impor a elas massas mínimas do editor ativo.

Próximo após256 aprovado: protótipo científico e caminho de renderização agregado,
então integração, migração e perfil formal próprio. Nenhum aceite10mil estabelecido.


Avanço: scripts/verify-test-particles-prototype.py passou10000 partículas com
massa exatamentezero e1fonte, até10períodosKepler internos. Erros máximos
posição8.303e-14/velocidade8.295e-14/energia específica1.669e-15/L8.353e-16.
Fonte central fica exatamente imóvel, comparação2fontes não observou reação
nem efeito do vizinho semmassa; checkpoint+2futuros exatos. Recibo próprio.
cloud_snapshot.py serializa todas10000posiçõesSI em240554bytes, float64,
sem alterarbinário do solver;17domínios/corrupções recusados, gravaçãoatômica.
Tempoisolado de encode1.379ms é observaçãoúnica, nãoaceite de desempenho.
verify-cloud-native-prototype.py preparado para desenhoagregado ESTÁTICO,
ainda nãoexecutado; aguardar fim da medição256 antes de abrirWS adicional.
O motor atual carregaSPECK/CSV emRenderablePointCloud duranteinitialize();
File não é propriedade mutável. InterpolatedPoints usa trajetória carregada,
não é receptor ao vivo. Investigação aponta necessidade de atualizarbuffer
agregado explicitamente; não substituir evoluçãoIAS15 por simples animação.

Arquitetura candidata refinada (não implementada): manter Session/registry das
fontes ativas e acrescentar um driver IAS15 com fontes+partículas de teste no
MESMOsimulador. A Session principal será somente espelho confirmado das fontes
enquanto esse modo estiver ativo, como já ocorre com o driver material.
Assim não se enfraquece o validador legado de massas positivas. Um perfil inicial
pode limitar-se a uma fonte central e até10mil partículas, com impedimento explícito
deJ2/maré/edição de fontes durante o modo. Não executar dois integradores para
as mesmas fontes. Ao desligar, reconstruir derivados do IAS15 principal.

O driver terá checkpoint binário IAS15 completo, selado e referido por sidecar,
mais declaração determinística da nuvem. Preservar futuro exato; nunca embutir
esse binário de váriosMB no estado público30Hz. Fases/atributos/fontes dos
instrumentos e conservação continuam só nas fontes; energia eL específicos
podem ser consultados por partícula. Não calcular energia com um laço10k².
IDs de teste são índice estável dentro de system_id+origem selada, separados
de IDs de fontes, com seleção por índice e um único nó âncora de seguimento.
Posições nativas agregadas virão do pacote confirmado float64; nenhum nó por
partícula. A seleção deve consultar faseSI do instante confirmado e não inventar
massa mínima nem fonte observada para uma partícula semmassa.

RenderablePointCloud suporta desenhoagregado estático, porém seu File não é
mutável. Receptorbinário pode ser extensão dedicada do mesmo bufferGPU, com
seq/instante/identidade publicados como propriedades somenteleitura. Validar
contagem, dimensão,finito,escala eidentidades antes de substituir buffer, sem
fase parcial. PrecisãoGPUfloat32 precisa de limite visual declarado, separado
 da fase científica float64. Atualização nativa deve confirmar qual pacote foi
consumido; não assumir que a última fase do worker já apareceu na tela.

Problema de formato encontrado na prova estática: o leitorSPECK0.22 testa
stringstream.good() após o terceiro número, considerando EOF imediatamente
após z uma falha. O arquivo candidato agora declara datavar0cloud_index e
inclui índice comoquarta coluna; preserva3posições. Ainda repetir prova nativa.

ProvaESTÁTICA nativa passou apósformatoSPECKcorrigido:10000pontos carregados
numRenderablePointCloud. Reciboevidence/cloud-native-prototype-check.json,
capturacosmos2-cloud-static-prototype.png. Isso não éfluxodinâmico/performance.

## Candidata integrada em17/10 — ainda não instalada

output/c211-cloud-product/app contém Session3.13 com driver conjunto,
IDs tp:cloud_id:index, seleção SI e sidecar IAS15. Controle de ativação e
desativação é intervenção explícita sem energia/momento injetados nas fontes.
Fonte espelhada não é integrada em paralelo. Desativar reinicia os derivados
do integrador das fontes; reset/load simples limpam a propriedade da nuvem.
Maré/J2/edição de fonte/topologia são recusados enquanto a nuvem estiver ativa.
Instrumentos e conservação continuam somente nas fontes.

verify-cloud-session-prototype passou10mil/10períodosKepler, erro7.723e-14,
3futuros exatos,22guards/14corrupções, ramos, seleçõesSI e histórico sófonte.
Regressões J2/maré/ressonâncias e13migrações reais passaram nesta candidata.
Primeiras variantes do worker foram recusadas por taxa0.0406 e0.6453. O
REBOUND5.2.2 restaura a proposta inicial dt ao retornar cedo com
exact_finish_time=1 (src/simulation.c). Proposta inicial da nuvem agora é
min(0.1,0.1/sqrt(M)) para r_min=1; IAS15 continua adaptativo epsilon1e-9.
O worker mantém alvo de publicação30Hz e segue tempo solicitado com recuperação
limitada a0.25s solicitados por chamada e heartbeat40ms; não fixa dt a1/30.
Worker sem transporte passou rate0.97734/20pausas≤24ms/40sequências em~2s,
compute máximo56.744ms e estadoJSON≤16002bytes. Alvo30Hz não é cadência real.

Novo cloud_transport.py v2: float64SI,system/edit/cloud/source/frame/contagem/
seq/instante vinculados, SHA256+CRC32.30recusas e publicação atômica passaram;
10000posições exatas em240626bytes. Worker agora tem --cloud-output para
publicar pacote separado; esse caminho ainda precisa de reexecução isolada.

Receptor opt-in ConfirmedCloud adicionado ao RenderablePointCloud upstream;
compila em build-cloud-receiver-pass2 (pass1 recusou tipo unsigned no codegen,
corrigido para int). Ainda não instalado/testado nativamente. Receptor usa
CRC32 nativo e declara SHA256 de origem, validado pelo produtor/decoderPython;
não alegar SHA256 nativo. Float32GPU tem erro de quantização publicado.
Estágio previsto .runtime-cloud por scripts/stage-cloud-runtime.py após
buildconcluído; launcher apenas -Built -RuntimeVariant cloud explícito,
seleção auto continua query aprovado. Nunca substituir .runtime-perf-query
ou .runtime-built. Próximo: concluir build, estágio, prova nativa sequencial
com pacotes válidos/obsoletos/corrompidos e seleção, depois integrar Laboratory/
CEF. Perfil real10mil ainda pendente; C2-11 permanece parcial.
