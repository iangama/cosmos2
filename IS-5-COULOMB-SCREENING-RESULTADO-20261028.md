# IS5/C2-20 — screening termodinâmico, resultado28/10/2026

**Screening numérico aceito; evolução ainda em verificação.** Recibo
`evidence/is5-coulomb-screening-20261028a.json`, fontes exatas no ZIP
`output/is5-coulomb-screening-20261028a.zip`. Modelo em
`output/is5-coulomb-network-staging/is5_coulomb_network.py` preservado.

Foram52 verificações de pares:13 canais de duas partículas em4 estados
T/ρ/composição, com sementes N14/O16. A referência insere um composto
virtual com a massa e carga corretas e diferencia a mesma energia livre,
conservando bárions e carga na direção de fusão. Máximo erro8,951e−15 na
escala de h contra mpmath50dps; diferenças finitas8,315e−11.

Elétron–elétron cancela exatamente na fusão virtual de carga conservada.
Sua contribuição permanece na EOS/reservatório. Isótopos de mesma carga
produzem o mesmo screening clássico; p+p usa composto Z=2 e não o
dêuteron beta final. Os quatro decaimentos e EC mantêm fator adicional1;
taxas nuas, lei SFII de EC, prefatores idênticos e8 conjuntos de gates
foram conferidos. Seis entradas inválidas foram recusadas.

No fixture padrão15MK/1,5e5kg/m³, fator p+p≈1,04631 e p+O≈1,28683.
São previsões deste modelo estático clássico no fixture, não calibração
solar ou medida observacional. Não há screening dinâmico, correções
quânticas iônicas nem precisão física estabelecida por esses resíduos.

Próximo ativo: `verify-is5-coulomb-evolution.py --label20261028a`, comparando
Radau com BDF em energia U e inversão da EOS, controles e realimentação.
Só após esse aceite avançar para o trabalhador, cujo contrato foi preparado.
