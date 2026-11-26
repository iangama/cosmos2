# IS6/C2-14 — contrato científico prévio da malha espacial

01/11/2026, antes de implementação e medições desta fatia. Executar após os
aceites próprios da compressão. Preparação e fontes:
`IS-6-MALHA-ESPACIAL-PREPARACAO-20261101.md`. Primeiro apenas ciência isolada
em `output/is6-spatial-staging`; não substituir produtos, sessões ou fontes
aceitos. Sem inferir aceite nativo, visual, de desempenho ou de todo C2-14.

## Modelo e saída

Uma fonte esférica estática, exterior de Schwarzschild. Entradas SI: GM,
raio material adotado, raio areal e orientação ortonormal do corte. c exato
299792458m/s. Coordenadas da métrica de Schwarzschild; corte t constante,
equatorial. Mostrar separadamente geometria intrínseca, embedding e ampliação.
Não usar a geometria óptica do exemplo EinsteinPy como corte espacial.

Componentes espaço-temporais usam ct em metros como coordenada temporal:
g_ctct=−(1−Rs/r); a leitura de relógio continua dτ/dt com t em segundos.
Métrica espacial dl²=dr²/(1−Rs/r)+r²dφ², com Rs=2GM/c². Embedding de Flamm
em um único ramo: z=2√[Rs(r−Rs)] até constante aditiva. A cena pode deslocar
z para zero no raio externo. A altura é uma coordenada do embedding, não tempo
ou uma direção física adicional. Ampliação vertical0–1000 é só exibição;
sondas medem sempre a métrica original. Não medir distâncias físicas sobre
vértices ampliados.

Retornar r,Rs,Rs/r,componentes da métrica, comprimento radial próprio entre
dois raios, excesso sobre Δr,circunferência2πr,razão dτ/dt de relógio estático,
déficit1−dτ/dt e Kretschmann K=12Rs²/r⁶(m⁻⁴). Comparação entre observadores
estáticos informa o sentido emissor/receptor e o deslocamento fracionário de
frequência; não substituir observador estático por um planeta em órbita.

Representar déficits pequenos com formas estáveis, incluindo
1−√(1−u)=u/[1+√(1−u)],u=Rs/r. Distância própria e seu excesso devem continuar
úteis no campo fraco; não obter todo excesso pela subtração de dois comprimentos
quase iguais. Relógios de razão próxima1 conservam também a diferença pequena.

## Domínio e tipos

GM=0 é o controle plano; caso contrário1≤GM≤1e26m³/s². Raios finitos
1≤r≤1e20m,raio material0–1e20m. Todo ponto, inclusive limites da malha,
deve estar em r≥raio material e r≥1,01Rs; exigir raio externo>interno.
É um limite numérico/modelo adotado, não acesso ao horizonte ou interior.
Recusar bool,NaN,infinito,strings,campos extras,orientação não ortonormal,
resoluções fora do orçamento e inputs fora do domínio. Sem clamp silencioso.
GM0 retorna relógios1,déficits0,K0,z0 e comprimento próprio=Δr exatamente.
Orientação: base de três vetores unitários ortogonais, determinante+1,
resíduo máximo1e−13, sem renormalização. Centro finito por componente em
±1e20m é metadado separado. Intervalo de comprimento com extremos iguais
retorna0; extremos invertidos são recusados. Resoluções aceitas nesta fatia:
33/65/129/257anéis e96setores, incluindo um vértice de fechamento por anel.

## Fixtures fixadas antes da execução

Conservar um arquivoJSON das fixtures e fontes antes de calcular resultados:

- Família adimensional Rs1m, GM=c²/2, raios1/u para a lista exata
  `u=[1e-18,1e-12,1e-9,1e-6,1e-3,0.1,0.5,0.9,0.99]`.
- Escalas físicas com GM∈{1,3.986004354360959e14,1.3271244004193938e20,1e26};
  os dois valores intermediários são fixtures numéricas, não nova adoção de
  constantes observacionais. Escolher raios1000Rs,1e6Rs quando no domínio.
- Intervalos radiais [1.01Rs,2Rs],[2Rs,8Rs],[1e6Rs,8e6Rs] e intervalos curtos
  com raio externo=r_interno(1+1e−9), mantendo entradas representáveis.
- Massa nula; translação {0,0,0}→{1e9,−2e9,3e9}; três planos coordenados e
  uma rotação ortonormal não trivial. Translação/rotação não mudam as sondas.
  Manter vértices relativos à fonte e translação em metadado separado; não
  subtrair coordenadas globais grandes para recuperar um detalhe pequeno.

## Verificação independente e limites prévios

Referência mpmath80dps, montada da métrica e integrada por quadratura direta
para comprimentos e excesso. Não aceitar a integral apenas contra sua própria
primitiva. Para K, construir Christoffel/Riemann independentemente da fórmula
de produção; conferir também o vácuo Ricci0 e K positivo para GM>0.
Ricci na base ortonormal: resíduo≤1e−50×max(Rs/r³,1e−300), avaliado80dps.
Transformações são verificadas em vetores relativos e seus incrementos;
não usar cancelamento de coordenadas globais grandes como erro geométrico.

Limites relativos: componentes da métrica/relógios/circunferência≤3e−13;
déficits e deslocamentos pequenos≤3e−12; comprimento e excesso≤3e−12;
K contra tensor independente≤3e−11. Comparação de zero tem tolerância absoluta
1e−30 na unidade da saída; controles planos exigem zeros exatos. Comparar
valores calculados a partir das entradas double efetivas, sem imputar ao modelo
o arredondamento decimal inicial das fixtures.

Conferir g_rr=1+(dz/dr)² em≤3e−13rel. Malhas radiais logarítmicas de
33/65/129/257anéis e96azimutes: comprimentos de polilinhas convergem para a
métrica; no último refinamento erro relativo radial≤2e−4. Verificar redução
de erro quando acima do piso1e−12, fechamento azimutal e circunferências
analíticas. Orçamento de produção inicial≤257×97vértices. Transformações
ortogonais preservam distâncias em≤3e−13rel, separado da discretização.

Arquivar código/contrato/fixtures/fontes antes da execução, testar recusas sem
mutação e geração imutável. Falhas ficam preservadas com sua causa investigada;
não ajustar tolerâncias para obter aceite. Interface e binding de corpos terão
contratos próprios depois da ciência, com época/raio material/procedência e
limite da aproximação isolada explícitos.
