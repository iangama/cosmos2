# Próxima fatia C2-12 — fontes editáveis e intervenções

Contrato de implementação18/10. Editor0.2 implementado e validado localmente
nos recibos em-editor-check.json, em-editor-worker-check.json e
em-editor-native-ui-check.json. Produto instalado3.13 preservado. Integração
à cena/navegação nativa e perfis continuam pendentes.

## Operações e domínio

Fontes prescritas: criar, selecionar, editar e remover carga pontual ou dipolo;
editar posiçãoSI, cargaC, momentoAm² e raio de exclusão; editar os fundos E/B
com componentes SI. IDs únicos permanecem estáveis durante uma edição.
Modelos criados recebem origem `user_model`, com parâmetros explícitos. Nome
“Terra”, por exemplo, não transforma um dipolo inventado em dado terrestre.
Ligação a dados/corpos reais pertence ao registro de capacidades de C2-13.

Modo mútuo: editar carga, massa, raio, posição e velocidade das cargas ativas;
criar/remover respeitando1..128 e as exclusões. Fontes prescritas e massas
ativas não compartilham papel implícito. Neste modo não adicionar B próprio,
gravidade, Maxwell, radiação ou órbitas atômicas.

Todo comando usa pausa, system_id, edit_token, revisão, tempo confirmado e
FRAME de EM. Construir e validar um experimento candidato completo antes de
trocar o atual. Rejeitar estado antigo, singularidade, velocidade fora do
regime, duplicação de IDs ou exclusão violada sem alterar fase/configuração.
Aplicar não inicia evolução automaticamente. Preservar posição/velocidade
quando o usuário altera somente uma propriedade da fonte/campo.

## Registro físico obrigatório

Cada intervenção guarda comando, instante, revisão anterior/posterior,
IDs afetados e valores anteriores/novos com unidades e referencial. Registrar
diferenças de carga total, momento linear/angular e energia mecânica no
modelo. Congelar referências de conservação novamente após a intervenção;
não comparar a energia nova com a condição anterior como erro de integração.

No modo mútuo a energia mecânica é K+U de pares quando atuação está ligada,
K quando suprimida. No modo prescrito é K+qΦ aplicado; usar a mesma convenção
de zero do potencial antes/depois. Trocar o campo B não representa uma evolução
física de fontes: o modelo omite E induzido, energia do campo e trabalho dos
reservatórios. Nomear a diferença como **Δenergia mecânica do modelo**, nunca
como balanço completo campo+matéria nem como energia total nula.

Visualização não é intervenção física. Camadas E/B e parâmetros do mapa são
persistidos separadamente da atuação, sem alterar estado ou referências de
conservação. Mapa anterior fica identificado como congelado após edição
física; seleção por ID só permanece se a fonte ainda existir.

## Persistência e migração

Preparar versão0.2 do protótipo com esquema para intervenções limitadas,
metadados e configuração visual. Arquivar fontes/recibos/checkpoints0.1 antes
de alterar a geração. Criar migrador explícito para o esquema EM anterior,
preservando o arquivo original e conferindo a continuação sem edição. Não
remover a verificação de geração para fazer saves antigos passarem.
Nenhum arquivo do Session gravitacional3.13 será convertido implicitamente.

## Provas da fatia

1. Carga± e duas fontes não simétricas: editar muda campo/força conforme as
   referências já verificadas; mover/girar dipolo muda B em três dimensões.
2. Preservar x/v/t em edição somente de fontes; comparar deltas mecânicos
   com cálculo independente do estado anterior/novo no referencial fixo.
3. Quatro combinações atuação/visualização; E e B separados. Visualização
   preserva fase e invariantes; atuação preserva as propriedades da matéria.
4. IDs/tempos/revisões inválidos e estados proibidos recusados sem mutação.
   Excluir uma fonte invalida a seleção do seu ID sem selecionar outra.
5. Salvar/retomar modelo editado, histórico e escolhas visuais; futuro exato
   por777passos; migração EM0.1 sem mudança científica e backup preservado.
6. Percurso CEF real com criação/edição/remoção, sonda e exportação das fontes
   e leituras SI do mesmo instante. Manter produto3.13 e owner intactos.

O perfil inicial do worker128 avançou apenas0,103s do modelo, com taxa mínima
observada~0,160s/s. Isso demonstra evolução/pausa/conservação nesta fixture;
não satisfaz um perfil formal de taxa solicitada/frames do produto. Otimização,
cena nativa e perfis continuam pendentes.

## Evidência executada nesta fatia

17intervenções confrontadas com balanços independentes,26recusas atômicas,
16combinações atuação/visualização,doisfuturos editados777passos exatos.
Migração dos checkpoints helix/coulomb0.1 confere777passos comprocesso legado
extraído do arquivo congelado ehashverificado. Limite64 com6anteriores
explicitamentecontadas no teste;referências/histórico persistidos.
Workerreal:guardas deinstante/revisão/identidade/frame,edição recusada durante
evolução,visibilidade sempausar,exportação ecriar/editar/remover nos2regimes.
CEFreal:fontes±assimétricas,dipolo3D,fundosE/B,carga/massa/x/v,remoção limpa
seleção,save/evolve/restore completo eJSONSI servido ehashconferido. Captura
evidence/cosmos2-em-source-editor.png;zeroJS,82arquivos instalados eownerintactos.
Exporta fontes,sonda eforça instantânea da partícula quando aplicável;linhas
integrais eexportações de mapas inteiros ainda não fazem parte deste aceite.
Os controles visuais podem mudar duranteevolução usandoidentidade/revisão
atuais e instante confirmado anterior≤atual;ediçõesfísicas exigempausa e
instanteexato. Uma ediçãoverifica também um passo candidato semcommit.
