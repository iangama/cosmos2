# C2-14 — contrato anterior aos dados de órbitas e relógios

Primeira fatia: referência CPU de uma partícula-teste no exterior esférico
estático de Schwarzschild, comparada ao modelo Newtoniano. Não altera a
candidata0.27.0, suas quatro forças ou os16corpos. Não encerra C2-14/15.

## Modelo, coordenadas e escalas

Coordenadas de Schwarzschild, raio areal r, plano equatorial e assinatura
(-,+,+,+). Tempo coordenado t é o relógio normalizado no infinito; τ é tempo
próprio da partícula. A fonte é idealizada, sem rotação, carga ou reação à
partícula. O domínio é exterior à fronteira esférica declarada. Não incluir
radiação, auto-força, J2, outros planetas, plasma ou emissividade.

Base: [Carroll, equações7.39–7.48](https://arxiv.org/pdf/gr-qc/9712019),
PDFp180/numeração174. A parametrização ligada e a referência por anomalia
vêm de [Hopper, Kavanagh e Ottewill, seçãoIIA/eqs2.4–2.9](https://arxiv.org/pdf/1512.01556v2).
Usar somente a geodésica de fundo dessa seção, sem termos de auto-força.

Escala L é o semilatus rectum relativístico; r_s=2μ/c², μ=GM, κ=r_s/L,
R=r/L e s=τ/√(L³/μ). T=t/√(L³/μ), A=1-κ/R. c=299792458m/s.
O momento angular específico em unidades √(μL) é H, e a energia específica
em unidades c² é E. Com e a excentricidade de Darwin:

```
D = 1 - (3 + e²)κ/2
H² = 1/D
E² = ((1-κ)² - e²κ²)/D
I = -(1-e²)(1-2κ)/(2D) = (E²-1)/κ
R_peri = 1/(1+e); R_apo = 1/(1-e)
```

A implementação integra em tempo próprio a forma adimensional derivada
da primeira integral, preservando I sem subtrair números quase iguais:

```
dR/ds = U
dU/ds = -1/R² + H²/R³ - (3κH²)/(2R⁴)
dφ/ds = H/R²
dT/ds = E/A
I_amostra = U²/2 + H²/(2R²) - 1/R - κH²/(2R³)
```

Para não perder o atraso muito pequeno de relógio por cancelamento,
integrar J=T-s com J'=κ·[I/(E+1)+1/R]/A e reconstruir T=s+J.
É a mesma equação de T; guardar J diretamente, além dos dois tempos.

Início: R=R_peri, U=0, φ=T=0. O sinal de H é a orientação escolhida.
Nenhuma velocidade angular é confundida com velocidade local medida.

## Comparação e relógios

Definição de estado inicial comum: a mesma posição em raio areal e as
mesmas velocidades **coordenadas em t**. No periastro, a referência Newton
recebe v_r=0 e v_φ=H·A/(E·R), em unidades √(μ/L). Sua elipse e seu período
são calculados a partir desse estado, não impondo os mesmos apoastro/e.
Isso não afirma igualdade de velocidades locais entre métricas diferentes.

As trajetórias são expostas em uma grade comum de T. A inversão T(s)
usa a solução densa interna, com resíduo≤2e-11·max(1,T_final). Não derivar
medidas de tempo/apsides apenas dos pontos de exibição. O produto guarda
τ/T, dτ/dt=A/E e velocidades no tetrad estático. O tempo absoluto Newtoniano
é identificado como tempo do modelo Newton, sem chamá-lo de τ Schwarzschild.

Caso circular e=0: solução analítica, Ω_coord=√(μ/r³), dτ/dt=√(1-3r_s/(2r)).
Periastro/precessão não são definidos para o círculo; não retornar zero como
uma medição de um apside inexistente. Órbitas excêntricas são medidas pelos
retornos reais U=0 com direção positiva. Guardar eventos e estados internos.
No círculo, a contagem de ciclos indica voltas azimutais e os campos de
período radial ficam ausentes; não confundir com o limite epicíclico e→0.

## Domínio e orçamento fixados antes dos dados

μ∈[1e5,1e32]m³/s²; L/r_s∈[1e3,1e8]; e=0 ou e∈[0,05,0,8].
Nesta primeira fatia a direção apsidal de e muito pequeno fica fora do domínio.
Fronteira da fonte≥r_s e periastro≥1,001·fronteira. Orientação±1.
1–16ciclos radiais;257–4097pontos de exibição. Rejeitar bool como número,
NaN/Inf, campos desconhecidos e parâmetros fora desses limites.

DOP853 com rtol2e-12/atol2e-14 e passo máximo P_Newton/128. Limites:
300mil chamadas RHS e15s por execução; resultado incompleto recusa, sem
truncamento silencioso. Refinamento independente:rtol2e-13/atol2e-15,
passo máximo P_Newton/256. Esses limites não são desempenho já medido.

## Verificação independente e critérios

O auditor não importa RHS/constantes calculadas do solver. Reconstrói E/H
pelas equações originais em p=Lc²/μ e integra as equações2.6 em χ por
quadratura. Para precessão, integra o excesso dφ/dχ-1 com log1p/expm1,
conservando precisão quando κ é pequeno. Compara períodos em t e τ e avanço
apsidal. O termo fraco3πκ por ciclo é referência assintótica, não a solução exata.

Fixar os critérios para a matriz e∈{0,05;0,2;0,6;0,8},
κ∈{1e-3;1e-4;1e-6;1e-8}, com1ciclo e casos longos de8/16ciclos:

- Erro de precessão por ciclo≤5e-10rad+5e-7·|Δφ_exata|.
- Períodos coordenado/próprio:erro relativo≤2e-9; refinamento muda≤2e-9.
- Resíduo máximo de I≤2e-10; norma métrica≤2e-12, incluindo nós internos.
- Periastro/apoastro:erro relativo≤2e-9; sinal/orientação e número de ciclos corretos.
- Estado inicial coordenado Newton/GR:erro adimensional≤2e-13.
- Referência Newton por equação de Kepler, conservação de energia/momento e
  retorno fechado; não reutilizar a trajetória relativística como referência.
- Escala de μ em×10, com L/r_s fixo:geometria adimensional/razões de relógio
  invariantes e comprimentos/tempos físicos em×10, tolerância relativa2e-12.
- Circular:raio constante, fase/relógio analíticos e precessão explicitamente ausente.
- Preservar recusas de domínio/limite e fontes/receitas antes de qualquer coleta formal.

Depois do aceite CPU: serviço isolado com edição/versão/cancelamento,
interface nativa, atuação/visibilidade separadas, sondas/legendas, persistência
e perfil próprio. Não apresentar renderização ou integração ainda não medidas.
