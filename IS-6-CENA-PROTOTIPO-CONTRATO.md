# IS6 — protótipo nativo da malha, contrato prévio01/11/2026

Depois de artefatoA aceito, construir renderer isolado em
output/is6-spatial-scene-staging. Não editar runtime.is4-stream,upstream aceito,
produto0.17.2 ou modelos. Usar o caminho estático SPECK existente de
RenderableConstellationLines; não relabelar o protocolo de trajetóriaIS4,
que possui semântica de tempo e limite129pontos.

Representar cada anel e cada meridiano como uma linha separada;65+96linhas
no default,257+96na resolução máxima. Não acrescentar diagonais ou emendas
entre linhas. Dois índices de cor com legenda. Normalizar vértices exibidos
por Rref e aplicar escala uniforme Rref no nó pai, cuja translação é o centro
arquivadoGALACTIC. Ampliação afeta só altura já explícita no artefato.

Conversão prevista para GL_FLOAT:auditar cada componente normalizado contra
float32 a partir da forma textual17dígitos entregue ao parser. Limite de erro
vetorial≤2e−6Rref na configuração default/max com ampliação200; outras opções
devem trazer seu limite calculado,sem alegar mesma resolução. Isto é orçamento
de quantização previsto pelo código do renderer, não readbackGPU medido.
Sondas continuam no artefato double e não são lidas dos pixels.

Escrever SPECK e nomes em pasta nova,binding/source/artifactSHA e manifesto,
sem arquivos de entrada arbitrários. Verificação headless independente lê
SPECK de volta,confere contagem/ordem de todas as linhas,vértices completos e
fechamento,cor/unit/quantização contra artefato original; nenhuma coordenada
global grande é serializada como float32. Arquivar fontes/fixtures antes do
teste. Não alterar renderer/fontes enquanto testes próprios estiverem rodando.

Protótipo nativo pode usar0.17.2 como host de diagnóstico,com cópia solar
pausada e nós temporários próprios; isso não aceita produto0.18 nem redefine
o aceite0.17.2. Guardar câmera/flags de cena antes de anexar,ocultar marcadores
orbitais que poderiam ser confundidos com raios materiais,restaurar tudo ao
fechar. Não desenhar interior esférico como solução do corte. Legenda informa
corpo,época,plano,Rref,GM,ampliação e referência exterior isolada.

Verificar nativo com Sol/Terra/Lua/Júpiter,alternância show/hide e limpeza;
translação/escala/propriedades confirmadas,instalação CPU completa e imagens
da malha real. Fonte/fase/artefato/owner inalterados. Imagens passam por
inspeção separada,sem inferir visual apenas de DOM. Limite cena pronta15s;
falhas preservadas,sem mutação da cena anterior confirmada.

Produto/ponte/controles persistentes,journeyCEF100/150%,malhas/camadas juntas
e perfil próprio são etapas futuras,com contratos e aceites separados.
