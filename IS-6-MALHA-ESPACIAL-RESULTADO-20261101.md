# IS6/C2-14 — base científica da malha espacial,01/11/2026

CiênciaC ACEITA em evidence/is6-spatial-20261101c.json:
5grupos,1900comparações e31recusas. Modelo0.1.1 em
output/is6-spatial-staging-b/is6_spatial.py. Congelar modelo,contrato,fixtures,
referências e verificadorv3 ligados ao recibo; versõesA/B recusadas preservadas.

Corte espacial tconstante/equatorial de Schwarzschild exterior,fonte única.
Métrica,embeddingFlamm,comprimentos/excesso,relógios estáticos e K por Riemann
independente conferidos. Referência80dps com40dígitos de guarda para tensor;
controle adicional160dps. Sem óptica incorporada à métrica espacial,sem
somar campos de fontes ou modificar órbitas.

| Grandeza | Erro relativo máximoC | Limite prévio |
| --- | ---: | ---: |
| Métrica | 9,93e-15 | 3e-13 |
| Razão de relógio estático | 4,92e-15 | 3e-13 |
| Déficit pequeno do relógio | 5,00e-16 | 3e-12 |
| Deslocamento fracionário de frequência | 4,52e-15 | 3e-12 |
| Comprimento próprio / quadratura | 2,01e-15 | 3e-12 |
| Excesso de comprimento / quadratura | 2,23e-15 | 3e-12 |
| K / tensor independente | 2,58e-16 | 3e-11 |
| Inversão vetorial de rotação | 1,05e-17 | 3e-13 |

Refinamento33/65/129/257anéis×96setores fechados convergiu. Pior erro radial
final6,663e-7,limite2e-4. Três planos/rotação,centro separado,ampliação0/1/1000
e limiteGM0 exato passaram; leitura intrínseca não depende da ampliação.
Tipos,domínio,esquemas,orientação,resolução e geração imutável conferidos.

TentativaA:falhou o controleRicci do avaliador80dps no campo mais fraco;
aumentar precisão mostrou queda sistemática do resíduo. B usou80+40dígitos
de guarda, mantendo limites, e revelou falha real de avaliação dos relógios
próximos:subtração de logaritmos perdia precisão no deslocamento pequeno.
Revisão isoladaC usou log1p de diferença racionalizada e repetiu todos os grupos.
Contratos de mudança IS-6-MALHA-ESPACIAL-REFERENCIA-B.md e
IS-6-MALHA-ESPACIAL-RELOGIOS-C.md foram escritos antes dessas execuções.

Este aceite é só científico:sem associação a corpos,artefato persistente,
ponte,HTTP,CEF,cena nativa,inspeção visual ou perfil. C2-14/IS6 continuam
parciais. Próximo:contrato próprio de fontes/raio material e binding aos
quatro centros pausados,sem presumir raio físico de um marcador gráfico.
