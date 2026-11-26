# IS5 — derivadas cruzadas da EOS,29/10/2026

Wrapper de derivadas aprovado numericamente sobre a EOS Coulomb já aceita,
sem alteração do modelo pai. O recorte ainda não inclui evolução com volume
variável nem produto. Licenças e documentação de procedência preservadas.

is5-eos-cross-20261029a ACEITO:12 estados interiores,sementesN14/O16,
T12/14/15MK eρ1e5/1,5e5kgm⁻³.240derivadas verificadas com mpmath50dps,
720 por diferenças finitas em três passos. Oito recusas herdadas de tipo,
composição/domínio, incluindo traçoFe26 positivo que não pode ser descartado.
102fontes/inputs conferidos e ZIP próprio preservado.

| Verificação | Maior erro | Limite prévio |
| --- | ---: | ---: |
| Derivadas mpmath50dps | 6,460974e−14 | 1e−8 |
| Diferenças finitas, três passos | 1,390493e−7 | 2e−6 |
| Maxwell total | 3,281771e−16 | 1e−10 |

Componentes ideais usam Cv eletrônico e derivada de energia em número de
elétrons já aceitos; correlações ii/ie/ee/mistura usam Hessiana da mesma
energia livre. A identidade de Maxwell é verificação de consistência;
mpmath/diferenças finitas fornecem as comparações numéricas independentes.
Esses erros não estimam incertezas físicas das aproximações da EOS.

Contrato e derivação:IS-5-COMPRESSAO-CONTRATO-PREVIO.md e
IS-5-COMPRESSAO-DERIVADAS.md. Módulo output/is5-compression-staging/
is5_eos_cross.py e teste verify-is5-eos-cross.py ficam congelados após aceite.
Documentação MESA primária arquivada comURL/data/SHA, sem executar/copiar
seu código nesta etapa. Próximo:solver separado conforme contrato de evolução.
