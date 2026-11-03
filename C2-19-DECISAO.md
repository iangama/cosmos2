# C2-19 — decisão local de aceite

13/10/2026, Windows / RX7600, CEF nativo e build próprio preservado.
**Aprovado localmente o recorte C2-19:** dez pais avaliados,19canais,
beta−/beta+/captura eletrônica e alimentação Sr90→Y90→Zr90. J13 e a parte
de decaimentos de J14 foram exercitados. O aceite usa DECAIMENTOS.md como
contrato anterior; a integração estelar e a v1 continuam com seus próprios
marcos. Espectros completos/oscilação/transporte seguem C2-22.

## Experiência entregue

Selecionar n/H3/C14/Be7/N13/O15/F18/Na22/Sr90/Y90, população e intervalo;
na cadeia Sr/Y, alterar também a fração inicial de Y90. A linha do tempo
consulta populações, atividades em Bq, taxas/eventos por ramo, elétrons,
pósitrons, captura de elétrons, neutrinos/antineutrinos e energia.

Suprimir beta+ de F18 conserva sua largura EC, reduzindo a atividade total
e mantendo neutrinos sem produzir pósitrons. Suprimir todos os ramos Y90
mantém a alimentação Sr90: Y90 acumula e Zr90 deixa de ser produzido. Não
renormalizar os canais restantes é parte central da semântica. Referência
completa, matéria e fontes permanecem; visibilidade não muda a física.

Salvar/retomar conserva caso, condições, canais e geração científica.
Exportação no CEF escreve um arquivo local igual à saída do backend,
incluindo fontes completas, campos brutos/incertezas, matrizes de leituras e
limitações. Testes restauram o arquivo salvo original do usuário. Entradas
inválidas não alteram resultado aceito, Atlas ou worker.

## Fonte, energia e incerteza

O modelo operacional usa ENSDF/LiveChart fixado; NUBASE2020 original aparece
como comparação explícita. Não misturar as meias-vidas de gerações distintas:
o nêutron, por exemplo, é613,9s no recorte ENSDF e609,8s no NUBASE. Totais
de Na22 também divergem. Datas/cutoff/autoria da avaliação e data de extração
ficam identificados. Foram excluídas as linhas do isômero Y90.

Na22 tem99,996% e Y90 tem100,0000014% nos ramos impressos; a normalização
operacional e seu fator são explícitos. Percentuais e incertezas originais
permanecem consultáveis. Meias-vidas trazem incerteza emsegundos. Campos de
incerteza Q/radiações são preservados na notação original; esta bancada não
os transforma em barras dinâmicas nem lhes atribui incerteza zero.

Q vem da mesma avaliação ENSDF dos ramos; energiaν usa médias tabuladas para
beta e o campo energy_ec como energia nominal aproximada para captura, sem
resolver camadas atômicas. O restante Q−Eν é energia disponível, sem afirmar
calor depositado ou energia somente do elétron. Médias e/ν/Q independentes
que não fecham exatamente ficam expostas, sem adulterar fonte. Filhos são
agregados por A/Z com nível de excitação identificado por ramo; relaxação
gamma/aniquilação não são evoluídas. Ambiente EC é o atômico da avaliação.

## Evidências

verify-decays: dez pais/19canais conferidos contra os21originais,102gates e
40limites. Meia-vida1,12e-16N0, composição e contagens contra Radau
1,43e-12/1,41e-12N0, cadeia contra Bateman6,67e-16N0. Maior resíduo de
bárions/carga/energia2,99e-14rel. População não negativa nos limites testados;
captura e leptões têm balanços explícitos, sem espectro inventado.

verify-decays-ui Edge e --native passaram os dez casos, intervenção F18,
alimentação/fração inicial/supressão Y90, curvas e fontes, save/load/export,
recusa sem mutação, zeroJS e720semoverflow. Capturas reais representativas
revistas em evidence/decays-visual-review.json, incluindo ramos e incertezas.
Doze contratos/persistência e12pacotes/64arquivos passaram; regressões da
bancada inicial e fusão também passaram. Nenhum executável do renderer mudou;
neste marco foram acrescentados gráficos e cálculo linear de pequena dimensão,
sem atribuir ao novo cenário um benchmark gráfico G0 não executado.

Próximo: C2-02, navegar/selecionar no Atlas e percorrer Terra→Lua→Saturno→favorito,
com fonte/cobertura, modos de câmera, tempo, foco e escala de interface.
