# IS-2 — critérios prévios para propagar os quatro corpos

Contrato da próxima verificação numérica, registrado antes de executá-la.
Não há resultado de propagação de quatro corpos neste ciclo. Referência
inicial: `output/solar-integration-staging/four-body-initial-si.json`, com
Sol10, Terra399, Lua301 e Júpiter599, em 11/10/2026 12h UTC.

## Perguntas que o teste precisa responder

1. As quatro fontes exercem atração recíproca no modelo pontual escolhido?
2. A conversão entre SSB/SI e o baricentro/unidades do experimento conserva
   posições e velocidades, com as origens devidamente guardadas?
3. Duas implementações distintas das mesmas equações concordam em 30 dias?
4. O refinamento confirma o erro numérico sem confundi-lo com forças omitidas?
5. A cena, quando conectada, mostra e mede exatamente a fase do solver?

## Ensaio numérico proposto

Congelar fixture, hashes de fontes, runtime e critérios antes da execução.
Usar REBOUND/IAS15 e uma implementação SI independente por somatório de pares
com SciPy/DOP853. A ODE de referência não chama o avaliador de aceleração do
produto; calcula aᵢ=Σⱼ GMⱼ(rⱼ−rᵢ)/|rⱼ−rᵢ|³, sem termo próprio, softening ou
reposição de posições por efemérides. A unidade canônica continua separada de
metros/segundos e GM não é rotulado como massa em kg.

Propagar de 0 a 30 dias, com leituras comuns a cada 6 horas. IAS15 usa a
tolerância de produção vigente 10⁻⁹ e comparação refinada a 10⁻¹². Na ODE
independente: rtol=2×10⁻¹³, atol de posição=10⁻³m e de velocidade=10⁻⁹m/s,
passo máximo de 3.600s. Resolver num referencial inercial explicitamente
compartilhado, guardando a translação/velocidade da origem para as comparações.

Limites prévios desta fatia, em todos os corpos/instantes amostrados:

| Grandeza | Limite |
| --- | --- |
| Diferença de posição IAS15 versus DOP853 | 10m por componente |
| Diferença de velocidade | 10⁻⁵m/s por componente |
| Refinamento IAS15: diferença de posição | 1m por componente |
| Deriva relativa de energia no modelo conservativo | 10⁻⁹ |
| Deriva normalizada de momento linear e angular | 10⁻¹⁰ |

Normalizar momento e momento angular por escalas físicas não nulas
declaradas, como Σm|v| e Σm|r×v| na condição inicial; não dividir por um
momento total quase zero. Usar uma só convenção de energia e aplicar a mesma
origem aos balanços. Registrar deriva do baricentro contra o movimento inercial
esperado. Os limites acima não substituem os perfis e limites anteriores;
definem o novo ensaio de 30 dias. Uma falha fica registrada antes de decidir
entre correção do código, da receita ou revisão justificada do contrato.

Antes da propagação, conferir ida/volta SI/canônicas, aceleração de cada fonte
e unidade de tempo. Capturar estados iniciais/finais, erros em toda a série,
passos e tempo de execução. Evitar usar só a última amostra, que pode esconder
picos. Se o solver ou a referência falhar, a captura é incompleta, sem aceite.

## Comparações e intervenções

Uma comparação entre o subconjunto Sol/Terra/Lua e o de quatro corpos pode
mostrar a contribuição de Júpiter usando condições iniciais comuns no mesmo
referencial. É comparação entre modelos reduzidos, não prova de um controle
geral de atuação. Não zerar a massa do planeta para fingir que um botão foi
implementado. Controles físicos precisam suprimir o operador declarado,
preservar fontes e registrar a intervenção segundo QUATRO-FORCAS.md.

Confrontar a evolução com efemérides JPL é uma avaliação adicional de erro
de modelo. O sistema reduzido omite outros planetas, luas jovianas, multipolos,
marés e relatividade. Não aplicar à diferença para a JPL o mesmo critério de
concordância entre integradores. Preservar a comparação e explicar sua origem.

## Integração do produto ainda exigida

Aceitar a conta não aceita a interface. A candidata terá que comprovar
IDs/época/frames, rótulos e leitura por fonte, câmera e sondas coerentes,
pausa/avanço/retomada, persistência/ramificações, recusas transacionais e
compatibilidade com o importador legado. Depois, fazer capturas revistas e
perfis próprios. As bancadas EM e nucleares só entram no aceite conjunto
quando sua ligação com corpo, época e solução estiver demonstrada.

Próxima implementação: criar uma candidata isolada para o cadastro dos quatro
corpos e um executável de referência para este contrato. Reusar as entradas
verificadas, sem baixar novamente kernels ou reexecutar 14 testes imutáveis.
