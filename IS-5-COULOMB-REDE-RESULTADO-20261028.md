# IS5/C2-20 — rede com Coulomb e screening, resultado28/10/2026

**Ciência local aceita**, por agregação `is5-coulomb-science-20261028a`.
Os91 arquivos da cadeia foram conferidos por hash e arquivados. Isso não
é aceite de trabalhador, produto nativo, desempenho ou estrutura estelar.

Evidências de evolução: `is5-coulomb-evolution-20261028a` e auditoria
complementar `is5-coulomb-evolution-controls-20261028b`. Os cinco casos de A
foram reutilizados após conferir fontes e15 JSONs; nenhuma integração
aceita foi repetida na auditoria.

| Caso | Condição | Maior diferença T Radau/BDF |
|---|---|---:|
| N14 | T prescrita,1.000 anos | 0 |
| N14 | Isocórico,1.000 anos | 5,340e−15 relativa |
| O16 | T prescrita,1.000 anos | 0 |
| O16 | Isocórico,1.000 anos | 2,807e−14 relativa |
| N14 | Isocórico,100.000 anos | 6,534e−13 relativa |

BDF usa U como variável e inverte a EOS numericamente; Radau evolui T com
Cv e o gradiente de composição. As tolerâncias também foram refinadas.
Maior erro normalizado de energia dos cinco casos:2,591e−15. A trajetória
longa aquece de15 para15,154163713 MK. Isso é uma zona de volume/densidade
fixos e radiação confinada, não a evolução observada do Sol.

Passaram os limites sem Coulomb/screening contra a rede ideal aceita,
todosoff, weakoff com esquema explícito, EMoff permitindo p+p, e Coulomb
no reservatório sem screening. Foram sete recusas complementares, incluindo
trajetória inicialmente válida que sai do domínio e é recusada integralmente.

## Reprovação A preservada

A concluiu os cinco casos, os dois controles ideais e todosoff. Depois
**reprovou no próprio pedido de teste**: weakoff enviava um mapa parcial,
mas a API exige forte/fraca/EM explícitos. Uma segunda expectativa errada,
de que EMoff congelaria toda a rede, foi identificada antes de sua execução:
o contrato aceito permite p+p com forte+fraca. B corrige os pedidos e a
expectativa, sem mudar o modelo, e registra separadamente os controles
complementares. O recibo A continua `accepted=false`.

## Próximo passo

O Radau levou aproximadamente41–65 s por caso completo nestas medições de
ciência. Isso não é perfil de quadros da interface. O trabalhador novo deve
ter isolamento e prazos compatíveis, sem falha aparente seguida de publicação
tardia; o cliente anterior de35 s não pode ser reutilizado sem adaptação.
Seguir `IS-5-COULOMB-WORKER-CONTRATO.md` em pasta própria, depois candidato
0.15.0, CEF, visual e perfil próprios. Instalação3.13 e candidata0.14.0 intactas.
