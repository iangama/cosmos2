# Decaimentos, ramificações e cadeias — contrato prévio

C2-19,13/10/2026. Ampliar os quatro casos iniciais com uma bancada avaliada
para n, H3, C14, Be7, N13, O15, F18, Na22, Sr90 e Y90. Sr90 alimenta Y90,
que alimenta Zr90. Filtrar rigorosamente estado inicial fundamental e ausência
de deslocamento de energia desconhecido. Não incluir por acidente as linhas
do isômero Y90(682keV). As outras cadeias terminam no filho declarado.

Fonte operacional única: CSV LiveChart/ENSDF fixado, com época de extração,
autores e cutoff da avaliação por linha. Meia-vida em segundos fornecida pela
API e sua incerteza são preservadas; não são atualizadas silenciosamente por
NUBASE2020. O original NUBASE2020 é comparação explícita, não substituição
de alguns campos. Diferenças reais: n613,9s ENSDF versus609,8s NUBASE; N13,
O15 e F18 também divergem. NUBASE adota ano tropical365,2422d; preservar a
conversão e o texto original. Ano de modelo/extração não é data de medição.

Os ramos beta−, beta+ e EC são canais separados por nível filho tabulado.
Para EC+B+, usar intensity_beta e intensity_ec, não interpretar B+ como
positrões100%. Na22 soma99,996% nos valores impressos; Y90 tem um desvio
minúsculo de soma. Normalizar os pesos completos de cada pai pela soma
impressa somente se estiver em99,5–100,5%; preservar percentual original,
fator e percentual operacional. Mostrar essa convenção. Nenhuma probabilidade
ausente é transformada emzero nem um conjunto incompleto ganha100%por padrão.
NUBASE Na22(90,57% e+/9,43%EC) difere da avaliação ENSDF usada: mostrar ambos
como avaliações distintas, sem misturar totais com níveis de outra versão.

Processo linear de populações esperadas: lambda_j=ln2/T_half * b_j;
dN/dt=S*(lambda_j*N_pai). Gates removem larguras parciais sem renormalizar
os ramos restantes. Portanto desligar um ramo aumenta a meia-vida efetiva,
e desligar todos preserva a população inicial. Fonte/material/referência
completa permanecem. Atuação global, efeitos por canal e visualização são
independentes. É intervenção contrafactual, não alteração consistente das
constantes fundamentais. O campo magnético/Atlas não altera meias-vidas.

Usar exponencial de matriz de dimensão pequena, com integrais dos pais em
tempo adimensional, para calcular população e número esperado de eventos
por canal, incluindo alimentação Sr→Y. Amostrar241instantes. Duração editável
em meias-vidas de referência do pai inicial (0,001–20), população1–1e12,
fração inicial do filho0–1 apenas na cadeia Sr/Y. Tempo exportado emsegundos
decorridos; nunca tempo próprio de neutrino nem época do Atlas. Curvas de
população/inicial, atividade por espécie e contagem acumulada de leptões.

Produtos por ramo: beta− emite e− e antinu_e; beta+ emite e+ e nu_e; EC
consome um elétron do reservatório atômico e emite nu_e. Conservar A e carga
incluindo leptões/reservatório. Filhos agregados por A/Z; energia de excitação
identificada por ramo, sem resolver sua relaxação ou inventar linhas gamma
temporais. EC usa o ambiente atômico da avaliação, não plasma totalmente
ionizado. Espectros completos, oscilação, transporte e detector ficam fora
deste modelo e seguem C2-22. Não oferecer botão EM para um operador de
relaxação/aniquilação que esta bancada não resolve.

Energia disponível por evento: Q atômico da mesma linha ENSDF; inclui
excitação dos filhos e a convenção atômica/possível aniquilação de pósitrons,
sem simular fótons ou assumir deposição. Energia de neutrinos usa a média
tabulada anti_nu_mean_energy/nu_mean_energy para beta; energy_ec é energia
nominal aproximada por ramo EC, sem captura por camadas resolvida. Expor
essa aproximação. Não forçar a soma das médias independentes de elétron,
neutrino e Q: C14/neutron apresentam resíduos reais no recorte. O modelo
contabiliza Q, energiaν e o restante disponível Q−Eν; este restante não é
calor medido nem energia cinética do elétron isolado. Preservar médias de
elétron como referência e registrar discrepâncias, sem adulterar dados.
Covariâncias não disponíveis; não propagar barras de erro dinâmicas fictícias.

UI: escolher caso, inspecionar cadeia/ramos e fontes, selecionar curvas,
linha do tempo para população/atividade/produtos/energia, gates por canal,
comparação com referência, salvar/retomar geração e JSON real no CEF.
NUBASE e ENSDF devem aparecer identificados nas leituras e exportação.

Critérios anteriores à implementação: dezpais/ramificações contra CSVoriginal
e NUBASE independente; meias-vidas analíticas (<1e-12 da população inicial),
cadeia Sr/Y contra Bateman e ODE Radau independente (<1e-9 da população
inicial), limites de gates/população/tempo, A/carga/leptões e Q=Eν+restante
(1e-11rel na cadeia), nenhuma população negativa além de1e-12numérico.
Testar alimentações/canais desligados e quatro combinações atuação/referência.
Sem mutação de cena por entradas inválidas; persistência/exportação reais,
Edge720/CEF, zeroJS e imagens revistas. Preservar discrepâncias de fonte.

Referências: [LiveChart API](https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html),
[NDLab, radiações e neutrinos](https://iaea-nds.github.io/ndlab/code.html),
[Kondev et al., NUBASE2020, CPC45,030001(2021)](https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf),
seção2.3 para ano tropical. Aquisição preliminar e respostas integrais em
output/research-decays/acquisition.json; promover apenas os arquivos usados
ao pacote científico, preservando hashes/URLs e sem refazer fontes já fixadas.

Implementado em app/decays.py/UI/decays.js e aprovado localmente em
C2-19-DECISAO.md após verificações científicas, Edge/CEF e revisão visual.
Doze contratos e12pacotes/64arquivos registrados nesta geração. Mantidos os
quatro casos antigos NUBASE na bancada inicial como geração distinta; não
substituir seus dados pelos do novo modelo ENSDF. A consulta de incertezas
dos ramos conserva campos brutos e explica a ausência de propagação dinâmica.
