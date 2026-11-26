# IS6 — deslocamento pequeno entre relógios estáticos

01/11/2026, após B recusada, antes da execuçãoC. Preservar estágioA, tentativas
A/B, fixtures, contratos e referências. O tensor com guarda passou; K teve erro
máximo2,58e−16 e seu controle contra160dps deu5,99e−81.

B encontrou uma falha de produção: a diferença de dois logaritmos próximos
perdia precisão no deslocamento fracionário de frequência de observadores
em raios próximos. Erro relativo2,4355e−8, acima do limite prévio3e−12;
a razão próxima1 sozinha não detectava esse erro. Não relaxar esse limite.

Revisão isolada em `output/is6-spatial-staging-b/is6_spatial.py`, versão0.1.1.
Para f(r)=1−Rs/r e raios emissor a/receptor b:

    f(a)/f(b)−1 = Rs(a−b)/(a b f(b))
    ln(νrecebida/νemitida) = 0,5 log1p[Rs(a−b)/(a b f(b))]

Calcular a pequena diferença por essa forma e então usar exp/expm1 para razão
e deslocamento, respectivamente. Isso evita subtrair dois logaritmos próximos.
A derivação, o sentido emissor/receptor e o modelo físico permanecem os mesmos.
Somente essa avaliação e a geração científica mudam; repetir todos os grupos,
com as mesmas fixtures/tolerâncias e a referênciaB de80+40dígitos de guarda.
