# IS5/C2-20 — screening e evolução com EOS Coulomb, contrato28/10/2026

Construção própria em `output/is5-coulomb-network-staging`; preservar a EOS
de mistura B, auditoria de composição e toda rede CNO-II aceita. Não alterar
taxas nuas, Q/ν, trabalhadores ou candidatas anteriores. Sem promoção.

## Screening de entrada

Do MESMO fC da mistura aceita, calcular
`h12=(μC1+μC2−μC,Z1+Z2)/(kT)` e `fsc=exp(h12)`.
Potenciais são derivadas NEUTRAS (ne acompanha as cargas). O termo
proporcional à variação de ne cancela para esta fusão virtual de carga
conservada. Elétron–elétron deve cancelar nesse h, embora participe de U.
Médias da mistura precisam variar na derivada; não usar somente LMR.

Aplicar somente a canais com dois núcleos na entrada, incluindo p+p fraco.
O composto de p+p tem Z=2 para o screening; não substituí-lo pelo dêuteron
final após a conversão beta. Os 16 núcleos da rede já contêm representantes
de todas as cargas compostas necessárias (2..9). No modelo clássico a
energia de correlação depende da carga, e não do isótopo; pode-se obter o
potencial por um representante de mesma carga, mas verificar o parâmetro
Tp/T com a massa de entrada A1+A2 do composto virtual.

β de N13/O15/B8/F17 e EC de Be7 mantêm fator1. A captura EC mantém a lei
SFII de plasma já aceita e sua dependência de Ye; não aplicar outro fator.
Preservar o prefator de partículas idênticas das taxas nuas.

Para cada par, além dos limites da EOS, exigir Γcomposto≤20 e Tp/T≤0,1;
`0≤h≤2` e `3Γ12/τ≤0,1`, com a1/a2 no mesmo ne, a12=(a1+a2)/2,
Γ12=Z1Z2 e²/(4π ε0 a12 kT),
`τ=3[π² (Z1Z2 e²/(4π ε0))² mred/(2 hbar² kT)]^(1/3)`.
Esta é a aproximação de screening termodinâmico estático; não resolve
tunelamento no plasma, correções quânticas dos íons ou screening dinâmico.
Referência primária: https://arxiv.org/html/1201.2133, equações2/5/7–9.

## Evolução e atuação

Reutilizar S, Q, Qν, taxas nuas, prefatores e gates da rede CNO-II por mérito.
Atuação forte/fraca/EM e controles por canal continuam com a mesma semântica.
A EOS é a propriedade declarada do reservatório; desligar um canal de reação
não transforma automaticamente o material num gás sem correlações.

T prescrita ou evolução isocórica, ne neutra atualizada pela composição,
radiação LTE confinada, ν escapa, rho/V fixos. Variantes explícitas
`include_coulomb` e `include_screening` permitem controles científicos;
screening=True com Coulomb=False é recusado (não há fC declarado).

`dT/dt = [nb(Q−Qν)·F − (∂u/∂Y)·dY/dt]/Cv`.
u e gradiente incluem a MESMA correlação; não adicionar Δμ como novo Q.
Energia nuclear medida pelas extensões evita subtrair U grandes para
exposições curtas. Preservar resíduos raw e recusar integralmente qualquer
estado fora do domínio; não clamp, extrapolar, encurtar duração ou publicar
uma trajetória parcial como resultado completo. Be7EC exige10<T/MK<16.

## Aceites antes de trabalhador/UI

- Screening nos13 canais binários contra diferença finita de energia livre
  em uma fusão virtual, com composto de A/Z corretos: ≤2e−6 na escala
  max(|h|,1e−4); contra derivada mpmath independente ≤2e−9. Testar pares
  idênticos, invariância por isótopo, cancelamento ee e erro de usar o produto
  beta em p+p. EC e quatro decaimentos sem fator; taxas/gates intactos.
- Evolução Radau contra BDF independente com U como variável e inversão
  EOS→T: T≤1e−7 relativo, composição≤1e−8 por bárion; refinar tolerâncias.
  Pelo menos um caso misto N14 e um com semente O16, em modos prescrito e
  térmico; adicionar fixture longa com realimentação térmica resolvida.
- Bárions e catalisadores≤1e−8, carga+leptons≤1e−10 por bárion;
  energia |U−U0−(Edisp−Eν)|/max(U0,Edisp)≤1e−8.
- Controle Coulomb=False/screening=False contra a rede ideal aceita,
  screening=False/Coulomb=True separado, todosoff e supressões fraca/EM,
  tipos/domínios/orçamento, recusa de saída integral, fontes intactas.
- Identificar explicitamente aproximações físicas e geração científica.
  Só depois criar trabalhador/persistência, controles, CEF/visual e perfil.
