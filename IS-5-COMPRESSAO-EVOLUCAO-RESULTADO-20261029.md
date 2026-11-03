# IS5 — compressão e trabalho externo,29/10/2026

A evolução local com densidade prescrita foi aceita em
[evidence/is5-compression-20261029b.json](evidence/is5-compression-20261029b.json):
3casos,4controles,13recusas,241pontos por trajetória. Conserva número
bariônico fixo e volume inverso à densidade; balanço Δ(VU)=Qretido+W.
Compressão aquece, expansão esfria, ciclo sem reações retorna ao estado inicial.
Não inclui hidrodinâmica, evolução gravitacional, transporte ou calibração solar.

Radau em temperatura foi confrontado com BDF em energia total e inversão
independente da EOS, e com Radau refinado. Erros máximos dos3casos:

- Caso0, n14, {'kind': 'exponential', 'ratio': 1.05}: erros{'BDF': {'Y_absolute': 5.551115123125783e-16, 'T_relative': 8.421244310006818e-15, 'W_over_E0_absolute': 6.921255537198898e-16}, 'refined': {'Y_absolute': 8.326672684688674e-16, 'T_relative': 7.411491798405557e-15, 'W_over_E0_absolute': 9.878000691139636e-16}}; balanço6.68664018e-15.

- Caso1, o16, {'kind': 'exponential', 'ratio': 0.95}: erros{'BDF': {'Y_absolute': 3.885780586188048e-16, 'T_relative': 4.231304588776099e-15, 'W_over_E0_absolute': 1.7001184396558425e-15}, 'refined': {'Y_absolute': 1.9984014443252818e-15, 'T_relative': 6.4038280844678424e-15, 'W_over_E0_absolute': 1.848450920968097e-15}}; balanço9.09011873e-16.

- Caso2, n14, {'kind': 'cycle', 'ratio': 1.05}: erros{'BDF': {'Y_absolute': 0.0, 'T_relative': 5.571861500220927e-10, 'W_over_E0_absolute': 5.742317886862661e-10}, 'refined': {'Y_absolute': 0.0, 'T_relative': 4.431931905295553e-11, 'W_over_E0_absolute': 4.65848450909323e-11}}; balanço4.53366464e-13.

Quatro controles: limite de densidade constante contra trajetória Coulomb
isocórica anteriormente aceita, limite ideal, fraca desligada e EM desligado.
pp permanece ativo com EM desligado quando forte/fraca estão ativas.
A trajetória inicialmente válida que cruza limite superior de temperatura
foi recusada com a mesma guarda das taxas aceitas. Nenhum resultado parcial
fora de domínio é publicado.

ExecuçãoA permanece false: adaptador do teste usou escalar NumPy em API que
exige Python numérico. B converte somente rho/rate/V no adaptador referencial
e repete o conjunto completo sem alterar EOS, ODE ou tolerâncias. A/ZIP/caso0
preservados. Contrato IS-5-COMPRESSAO-REFERENCIA-B.md registra a correção.

Figura [PNG](output/is5-compression-figure-20261029a/prescribed-density-work.png)
e [SVG](output/is5-compression-figure-20261029a/prescribed-density-work.svg)
gerados somente dos dados aceitos. PNG inspecionado diretamente e aprovado,
recibo visual separado; nenhuma reintegração para desenhar.

Otimização em estágio próprio mantém as mesmas funções Helmholtz e guardas,
propagando gradiente completo e somente a linha térmica da Hessiana.
Avaliador aceito:12fixtures+21estados interiores, 7029 comparações escalares, erro máximo7.17852574e-14,6recusas.
Evolução otimizada em execução, sessão85185: três casos contra todos os
oráculos completos arquivados e quatro controles. Ainda sem aceite até
receipt is5-compression-fast-20261029a acceptedtrue. Meta caso0≤60s avaliada
separadamente da equivalência numérica. Fontes congeladas durante execução.

Nenhum trabalhador compressão construído ou produto novo aceito. Produtos
0.15.0 e0.16.0 aceitos permanecem preservados, sem promoção.

Fechamento: evolução otimizada ACEITA3casos/4controles/8recusas,
recibo is5-compression-fast-20261029a.json. Meta atingida:caso0
50.7114723s contra172.586711s, aproximadamente3.40vezes mais rápido.
Casos1/2:49.4450772s/21.9830302s. Sem aceite automático de trabalhador.
