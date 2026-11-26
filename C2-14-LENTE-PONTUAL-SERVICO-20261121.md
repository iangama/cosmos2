# Lente pontual — adaptação da bancada e proveniência

O núcleoCPU em point_lens.py está separado do produto aberto. Os recibos
offline21a/21b e geometry21a registram90comparações de alta precisão,
48permutações/reflexões,22recusas, escala/translação,12geometrias oblíquas
e o limite assintótico de três geodésicas nulas. O teste de escala21a usou
uma configuração além de1e25m; foi corretamente recusado. Somente essa
fixture foi corrigida em21b, sem mudar núcleo, contrato ou tolerâncias.

A adaptação acrescenta um palco `point-lens` ao serviço de forças. Mantém
um cálculo estático por pedido, sob o limite de concorrência já existente;
não cria uma trajetória temporal ou um botão de cancelamento sem trabalho
assíncrono. Salvar/retomar/exportar conservam configuração e geração,
usando os mecanismos existentes em namespace isolado durante os testes.

A interface usa massa em unidades do GM solar nominal, X/Y em au e Z em
kpc, todos no mesmo referencial cartesiano idealizado. São posições dos
três objetos, não distâncias cosmológicas. O adaptador registra a conversão
para metros e entrega o GM em SI ao núcleo. Converter unidades em float
não acrescenta precisão aos parâmetros informados.

Constantes verificadas em fontes primárias:

- `au=149597870700m`, exata, na definição IAU2012, também registrada pelo
  [USNO](https://aa.usno.navy.mil/faq/asa_glossary).
- `pc=(648000/pi)au`, [IAU2015 B2, nota4](https://arxiv.org/pdf/1510.06262).
- `GM_solar_nominal=1.3271244e20m³/s²`, constante de conversão da
  [IAU2015 B3](https://arxiv.org/pdf/1510.07674), sem tratar isso como uma
  medição do Sol atual.

Atuação e efeito de desvio alteram a imagem aplicada. Visualização só
controla a referência na tela. No alinhamento, a amplificação da fonte
pontual é indefinida; o JSON usa null com estado explícito, jamais um
número finito ou Infinity. A intervenção sem desvio pode continuar tendo
amplificação1 enquanto sua referência alinhada é singular.

O contrato científico identifica coordenadas, unidades, ângulos paraxiais,
construção de raios, paridade, domínio, constantes e hashes do núcleo e do
adaptador. Não altera dados nucleares, importações espaciais ou dinâmica
dos corpos. O estado científico dos outros palcos deve continuar igual,
considerando separadamente a nova geração de código declarada.

Antes da interface: conferir conversões, movimento dos três objetos,
efeitos/visibilidade, alinhamento, recusa/repetição, exportação/retomada e
dois servidores isolados. Não usar a sessão4700 para comandos de teste.
Depois: candidato novo, controles e medições em100/150%, retorno e sessão
preservada pelo mesmo lançador do dono. Nenhum desses aceites foi concedido
por este documento.
