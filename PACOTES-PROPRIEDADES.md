# Pacotes locais e propriedades do Atlas — contrato prévio

FatiaC2-01,13/10/2026. Manifestos fixados para os dados já adquiridos,
separando efemérides/modelos, imagens, catálogo estelar e tabelas científicas.
Não executar arquivos de dados nem alterar instalação pela consulta.

Manifesto: ID/versão, arquivos/caminhos relativos/tamanhos/SHA256 esperados,
URL/crédito/termos por recorte, unidade/referencial/época/cobertura e ausências.
Hashes esperados vêm dos recibos preservados; nunca recalcular a expectativa
durante a verificação. Dados de criação própria são fixados como versão local.
SHA256 é integridade local, não assinatura do fornecedor nem licença geral.

Consulta informa presença/tamanho e última verificação de conteúdo deste
processo. Verificação explícita relê arquivos em blocos, detecta ausentes,
diferença de tamanho/hash ou modificação durante a leitura. Cache identifica
data/tamanho/mtime; não alegar monitoramento contínuo. Caminhos saindo de data/
ou symlinks externos são recusados. Nenhum download/exclusão/promover dados
faz parte desta fatia; aquisição já possui scripts/recibos. Instalação e
recuperação gerais pertencem ao trabalho posterior do produto.

Atlas Sol/Terra/Lua: posição/velocidade, GM deDE442, massaGM/G, forma adotada,
orientaçãoIAU geral e textura possuem registros independentes. Cada registro
tem unidade/status/origem/fonte/referencial/época ou ausência explícita.
Vetores/GM são resultados/parâmetros de modelo, textura é imagem de superfície
e esfera/elipsoide são formas adotadas. Massa calculada não é massa observada.
Ausência de erro da fonte permanece null, separada da contribuição conhecida
deG. Não inventar época da imagem ou precisão local da efeméride.

Observador atual: origem coordenadaSSB/NAIF0, estado geométrico simultâneo
emTDB, aberrationNONE. Câmera não vira observador físico. Tempos de emissão e
recepção ficam null porque não há propagação de luz aplicada. UI explica
isso; não oferecer observação aparente ou comparação de relógios inexistente.

Cópia para experimento preserva esses registros e a declaração geométrica
no estado inicial selado. O modelo do worker continua reduzido/newtoniano;
fontes não mudam por câmera/intervenção. Não acoplar tabelaAME/IGRF aoAtlas.

Critérios prévios:
- Todos os arquivos fixados presentes e SHA256 igual aos recibos; origem de
  hashes/termos explícita. Falta/diferença/caminho inválido identificados em
  fixtures isolados, sem reparar ou substituir silenciosamente.
- Consulta/verificação inválida não muda cena/worker/dados; concorrência de
  leitura limitada. Exportação, se oferecida, grava artefato local íntegro.
- Três corpos × propriedades: valores coerentes com vetores/GM/forma doAtlas,
  ausência/erro não vira zero. Época/ref/fontes preservadas na cópia/checkpoint.
- UI de propriedades e pacotes noCEFreal, cliques/filtros/retorno funcionando,
  zeroJS/overflow e revisão visual; regressão relevante da cópia/época.

Estado13/10: implementado/verificado. app/packages.py e catálogo fixado em
data/packages/catalog.json: dez pacotes,34arquivos,894541883bytes; cobertura
inclui todos os arquivos científicos atuais e os dados visuais adquiridos.
EXPECTATIVAS preservadas por recibo ou hash local fixado da extração/definição,
sem recalcular durante a verificação. Recortes D+T/pp-I/CNO-I separados do
originalAME. Symlink externo testado emLinux; não alegar testeWindows de criação
de symlink. Corrupção de mesmo tamanho/ausência/tamanho/IDs/caminhos passaram.

app/atlas_properties.py entrega21registros com origem própria; estado geométrico
e pacote/hash declarados. Cópia preserva propriedades/observador e checkpoint
foi movido a outra pasta com espaços. Quatro metadados inconsistentes recusados
sem mutação. Checkpoint valida também matriz gráfica e identidade inicial;
save() agora devolve o SHA256 do binário como texto, sem sombra por função.

UIcontent.html/CSS/JS ligada aoAtlas: consulta, fontes, filtros, termos, SHA256,
verificação eJSONreal emuser/exports pelo helperartifacts.py. CEFreal/Edge
passaram,720px semoverflow e zeroJS. Busca/eixos/datas/tamanhos pequenos
corrigidos após revisar imagens. Campo de massa editado mantém valor durante
polling após perder foco; abrir dados pausa o experimento e preserva a cópia.
Evidênciaspackages-properties-check/packages-symlink-check/content-ui-check/
native-content-check/native-atlas-import-check. Aceite localC2-01 documentado
emC2-01-DECISAO.md, sem fechar outros marcos ou produto final.
