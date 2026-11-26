# Revisão B do adaptador de serviço — 13/11/2026

O ensaio A recusou a criação da primeira partícula. O executor entregou
diretamente a leitura de LayerLaboratory.magnetic_reading. Essa leitura é
a referência independente das camadas e não contém scientific_generation.
O caminho real da interface usa Session.earth_field/jupiter_field, que
acrescenta a geração da fase antes da criação de uma partícula.

Na revisão B, consultar essas duas rotas pelo worker orbital real. Exigir
igualdade exata de todos os campos científicos entre a leitura independente
e a do worker, excetuando apenas o campo adicional de geração. Exigir que
essa geração seja exatamente a da fase comum. Entregar a leitura completa
ao método real ParticleLaboratory._initial e ao worker de partículas.
As camadas continuam usando sua referência original sem geração orbital.

Nenhuma fonte ou regra de admissão do produto muda. O ensaio A, seu ZIP,
contrato e executor permanecem preservados. Repetir em namespace novo,
mantendo receita, limites e todos os demais testes. A recusa A é uma falha
do adaptador de teste, sem evidência de defeito na rota real do produto.
