# IS5/C2-20 — Coulomb e screening: contrato de fundação, 28/10/2026

Construção isolada em `output/is5-coulomb-staging`. Preservar a EOS ideal,
redes, trabalhadores, candidatas e evidências aceitas, incluindo 0.14.0.
Este contrato antecede código e execução. Não promove o produto instalado.

## Decisão científica

Começar pela resposta eletrônica FD e pelo limite clássico Debye–Hückel (DH).
Isso é uma fundação com domínio estreito, não uma correção geral do núcleo
solar. Não concluir C2-20 nem atribuir o desvio anterior de pressão a Coulomb.

Fontes primárias consultadas nesta data:

- Potekhin e Chabrier (2012), arXiv:1201.2133v3,
  https://arxiv.org/html/1201.2133, equações 9 e 14–17: energia livre,
  limite DH e susceptibilidade eletrônica. O texto após a equação 17 alerta
  que a aproximação de Yukawa não determina o potencial de contato em
  degenerescência arbitrária. Portanto substituir `ne` por `kT χe` no
  comprimento de Debye NÃO valida automaticamente uma EOS ou taxa de fusão.
- Chabrier e Potekhin (1998), https://arxiv.org/html/physics/9807042,
  equações 1–2, 6, 29–36: parâmetros de acoplamento, decomposição das
  interações e limites da mistura linear. Modelo mais amplo é etapa seguinte;
  seus ajustes não estão implementados por este contrato.
- NIST DLMF 25.12.14/16, https://dlmf.nist.gov/25.12#iii: normalização
  dos integrais FD e referência independente por polilogaritmos.

## Resposta eletrônica

Reutilizar por mérito a EOS ideal aceita, sem editar suas fontes.
Com `C=2/λe³`, `ne=C F1/2(η)`,
`χe=(∂ne/∂μe)T=C F−1/2(η)/(kT)`.
Calcular também derivadas de `q=kT χe` em lnT a ne fixo e em ne a T fixo.
Integrar a ocupação FD e suas derivadas diretamente; não integrar
`x^(-3/2)/(exp(x−η)+1)`, cuja integral diverge. Ordem negativa extra
de polilogaritmo serve como referência analítica independente.
Essas quantidades são diagnósticos exatos do gás ideal não relativístico,
não uma demonstração de precisão física de correções quânticas de Coulomb.

## Fechamento DH clássico

Neutralidade: `ne=ΣZi ni`; `nb=ρ/mu`, `ni=nb Yi`.
Em SI: `B=κ²=e²/(ε0 kT) [ne+Σni Zi²]`.
`fC=FC/V=−kT B^(3/2)/(12π)` (J/m³).
Derivar todas as quantidades da MESMA energia livre, mantendo números de
partículas nas derivadas de volume e de temperatura:

- `uC=3fC/2`; `PC=fC/2`; `CvC=−3fC/(4T)`.
- Gradiente neutro `∂uC/∂Yi=(9/4)fC nb (Zi²+Zi)/(ne+Σni Zi²)`.
- Potencial químico neutro `μCi=(3/2)fC (Zi²+Zi)/(ne+Σni Zi²)`.
- Correção de entropia `sC=(uC−fC)/T`.

Somar P/U/Cv e gradientes à EOS ideal FD + íons clássicos + radiação LTE
confinada. Usar elétrons clássicos apenas no termo de interação é uma
aproximação assintótica explícita, limitada abaixo; não chamar isso de
EOS Coulomb para degenerescência arbitrária. A resposta FD fica disponível
como diagnóstico e verifica o erro da aproximação clássica no comprimento
de screening, sem alterar silenciosamente a energia livre.

Screening clássico binário: `h=Z1 Z2 e²κ/(4π ε0 kT)`, `fsc=exp(h)`.
Verificar também `h=(μC1+μC2−μC,Z1+Z2)/(kT)` no mesmo banho.
O terceiro termo é o composto de entrada, não automaticamente o produto
final de uma reação beta. Não aplicar esse fator a decaimentos ou EC de Be7
(a lei SFII já fixada inclui física do plasma). Não alterar Q atômico;
correlação armazenada entra em U e em seu gradiente, evitando dupla energia.
Esta fundação expõe pares de cargas, ainda sem conectar taxas/solver/UI.

## Domínio e recusas

T=10–30 MK; ρ=1e4–3e5 kg/m³, totalmente ionizado, clássico para íons.
Vetores explícitos A/Z/Y, tipos finitos estritos (bool recusado), A e Z
inteiros 1≤Z≤A≤300, Z≤26; 1–64 espécies; Yi≥0; |ΣAiYi−1|≤1e−10.
Nenhum clamp de abundância, ajuste de densidade ou remoção de traço positivo.
Espécie exatamente ausente não limita o banho; qualquer Yi>0 limita.

Guardas conservadoras de engenharia, NÃO fronteiras físicas exatas nem
garantias de erro estatístico:

- `max Γi≤0.1` para todas as espécies presentes;
- `ne λe³/2≤0.05`;
- `κ λe≤0.3` e `max(ni λi³)≤0.01`;
- `kT/(me c²)≤0.01`, `pF/(me c)≤0.1`;
- `max[Zi e²κ/(4π ε0 kT)]≤0.1` no banho.

Para um par solicitado, verificar também as cargas de teste Z1, Z2 e
Z1+Z2 nas guardas Γ e linearização; `h≤0.1`. Usar as mesmas regras mesmo
quando o composto não existe na lista. Isso recusa explicitamente casos
CNO solares e parte dos pares He; não usar a pequenez de um traço para
dispensar a verificação. `assess` explica o domínio sem publicar P/U/Cv
Coulomb fora dele; `evaluate` e `screening` recusam fora do domínio.

## Aceites anteriores à evolução ou ao produto

Fixar estes limites antes de executar:

1. Resposta FD em 9 η de −20 a 20: χe e primeira/segunda derivadas de q
   vs polilogaritmos mpmath 50 dígitos ≤2e−9 relativo (com escala explícita
   quando a derivada tende a zero); checagem por diferenças finitas ≤2e−6.
2. EOS DH em pelo menos 12 estados válidos: f/P/U/Cv/μ e gradiente contra
   montagem independente ≤2e−10 relativo; derivadas por diferenças finitas
   ≤2e−6 (inclusive coordenadas de composição sem impor renormalização).
3. Maxwell `P−ρ² ∂(u/ρ)/∂ρ−T ∂P/∂T` ≤2e−6 relativo ao P total;
   identidade da correção testada separadamente, sem diluí-la no ideal.
   P/U/Cv totais finitos positivos; sinal negativo de fC/uC/PC preservado.
4. Screening de pares válidos vs diferença química ≤2e−10 relativo;
   limite clássico da resposta FD e redução da correção com menor ρ/maior T.
5. Recusas de tipos, forma, neutralidade/conservação, domínio térmico,
   degenerescência/acoplamento/difração e par composto; imutabilidade de
   fontes próprias e de bases aceitas. Preservar falhas e novas etiquetas.

Depois da fundação, escolher o próximo fechamento para mistura solar
baseado nas fontes, antes de conectar uma evolução térmica. Toda evolução
futura exige Radau vs BDF em U com inversão independente, energia,
conservação, tolerâncias refinadas e recusa integral de saída do domínio.
Trabalhador, persistência, CEF, visual e perfil próprios vêm depois da ciência.
