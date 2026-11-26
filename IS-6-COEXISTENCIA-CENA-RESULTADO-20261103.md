# K1C — coexistência nativa de referências independentes

O protótipo K1C foi aceito para Terra/IGRF14 e Júpiter/JRM33 grau 13 na
candidata 0.18.5 isolada. Malha espacial e referência magnética compartilham
um proprietário de câmera/flags. As oito combinações de visibilidade não
alteraram a fase orbital pausada; a remoção da camada magnética preservou
a malha e recusou tentativa de mostrar a camada já removida.

Quatro falhas reais foram exercitadas com nós do motor: preparação magnética,
perda de ACK depois do commit, falha na leitura posterior e rollback sem
conexão. As três primeiras conservaram o estado publicado anterior; a última
bloqueou alterações até recuperar e remover todos os nós próprios. Câmera
e flags foram restaurados, com tolerância de 10⁻¹² apenas em Up.

As quatro capturas 1920×1080, em 100/150%, foram inspecionadas em pares de
cada corpo e tiveram hashes e pixels RGB conferidos. Malha, graticulado,
seta e ponto da amostra estão visíveis juntos. A legenda ampliada cobre
uma borda esquerda da malha em 150%, sem esconder a amostra ou o centro;
é uma legenda experimental e não constitui aceite da interface de produto.
Não houve erro JavaScript. App e servidor encerraram com código 0; a
auditoria confirmou ausência dos PIDs próprios e preservação da sessão do dono.

K1A/B permanecem recusadas. O diagnóstico de 03/11 confirmou arredondamento
float da StaticRotation: erro do ponto sob a transformação gráfica até
0,449 m na Terra e 2,844 m em Júpiter. A revisão C confere a posição
científica por translação double relativa, com ≤1 mm local e limites ULP
globais, e confere a transformação gráfica separadamente contra o orçamento
de exibição já declarado. Não alterou a ciência, a geometria ou a 0.18.5.

Recibos: evidence/is6-native-layer-pair-20261103c.json,
is6-layer-pair-visual-20261103c.json e
is6-layer-pair-native-process-20261103c.json. Fontes executadas ficam
congeladas; a cópia ZIP consta em output/is6-native-layer-pair-20261103c.

K2 mede as duas camadas simultâneas em perfil próprio. K3 prepara serviço
e interface coordenados na candidata 0.19.0. Persistência composta, migração,
perfil da interface final, expansão de catálogo e GR adicional continuam
pendentes; K1C não encerra IS6 nem qualquer novo marco completo da v1.
