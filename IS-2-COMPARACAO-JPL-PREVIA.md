# IS-2 — comparação de modelo com a referência JPL

Receita registrada antes da execução. Reutilizar as 121 fases IAS15 já
auditadas em `output/is12-solar-check-20261023b/30-day-series.json`, sem
propagar de novo. Instantes TDB exatos: ET inicial da cópia mais a duração
em segundos de cada amostra. Consultar estados geométricos SSB/J2000/NONE
dos mesmos IDs físicos 10/399/301/599, usando DE442s e somente o subset599/5.

Inverter a transformação para o referencial SSB: posição = fase canônica
vezes unidade de comprimento + origem inicial + velocidade da origem vezes
duração; velocidade = velocidade canônica vezes unidade + velocidade da
origem. Guardar todos os estados de referência e os resíduos em SI. Medir
módulo e componentes por corpo, máximos na série e valores finais. Guardar
também os resíduos relativos Terra–Lua, Terra–Sol e Júpiter–Sol: a diferença
relativa não inclui a translação comum entre as origens.

A comparação mede a divergência do modelo reduzido de quatro centros para
essas efemérides. Não se estabelece uma tolerância de precisão observacional
nem se usa o limite de 10 m entre integradores para julgar essa divergência.
Os termos omitidos estão no contrato científico; esta execução não identifica
isoladamente a contribuição de cada termo. A posição inicial precisa
reproduzir a fixture no limite já fixado de 1 mm por componente, e a
velocidade no de 10⁻⁸ m/s. Confirme os hashes da série auditada, dos kernels,
da receita e das fontes antes de calcular; mantenha a série original intacta.

Separadamente, testar invariância por translação e velocidade comum do
mesmo modelo newtoniano em candidata na memória, usando as mesmas quatro
condições iniciais. Não alterar os arquivos de sessão. Transformações
declaradas e limites numéricos próprios precisam existir antes desse ensaio.
