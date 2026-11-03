# IS5 — trabalho mecânico prescrito,contrato29/10/2026

Próximo ciclo científico após concluir o perfil da consulta0160. Preservar
EOS/rede/worker0150,consulta0160,dados e todos os recibos aceitos. Começar
em estágio científico novo,sem produto ou substituição de fontes aceitas.

O instrumento atual tem densidade/volume constantes. A próxima extensão
deve separar aquecimento nuclear e trabalho sobre uma zona fechada de
número bariônico fixo. Densidade será uma história prescrita,identificada
como intervenção externa; não é gravidade dinâmica nem solução hidrostática.
Sem adicionar transporte fotônico,luminosidade ou calibraçãoSolar por hipótese.

Referência de formulação: [documentação MESA sobre a equação de energia](https://docs.mesastar.org/en/latest/reference/controls.html#eps-grav-form),
consultada29/10/2026. Ela distingue derivada de energia interna,trabalho de
pressão e termo de composição. Pequenos resíduos numéricos não provam
completude física ou convergência. Não copiar código MESA nesta etapa.

Derivação própria nas convenções já aceitas: n_b=ρ/m_u,N_b constante,
V=N_b/n_b,U densidade de energia,Cv=(∂U/∂T)ρ,Y. Para cada amostra,
E=V U e dE/dt=V q_nuc,retida−P dV/dt. Q atômico/neutrinos e derivadas de
composição seguem exatamente o modelo aceito; não somar aniquilação novamente.

A identidade de Maxwell a conferir é

    ∂U/∂lnρ|T,Y = U + P − T ∂P/∂T|ρ,Y.

Assim,a temperatura deve satisfazer

    Cv dT/dt = q_nuc,retida − Σj(∂U/∂Yj) dYj/dt
               + T (∂P/∂T)ρ,Y dlnρ/dt.

Essas fórmulas usam neutralidade e composição por bárion; não confundir
densidade de energia com energia total quando V varia. O ledger mecânico
acumula W=−∫P dV em joules,e a primeira lei compara Δ(VU) com Qretido+W.
Pressão/radiação/eletrocorrelação pertencem à mesma EOS do reservatório.

Primeira entrega antes de integrar: derivadas cruzadas dP/dT e dU/dlnρ
da EOSidealFD+radiação e Coulomb,sem diferenças finitas no cálculo de produção.
Usar wrapper novo sobre funções aceitas; nunca editar o modelo0150 para
obter novos campos. Parte Coulomb vem da energia livre e de sua Hessiana.
Parte ideal usa a respostaFD já aceita e a contribuição analítica de fótons.

Pré-fixar12estados interiores:T=12/14/15MK×ρ=1e5/1,5e5kgm⁻³×sementesN14/O16,
mesma composição0,34H/0,01catalisador da rede. Validar derivadas com mpmath50dps
e diferenças centrais emT/ρ,passos relativos1e−4,5e−5,2,5e−5. Limites prévios:
mp≤1e−8,FD≤2e−6; escala relativa por componente max(|referência|,1e−14n_bk_B)
para dP/dT e max(|referência|,1e−14n_bk_BT) para dU/dlnρ.
Conferir Maxwell total em≤1e−10rel,sem usar isso como único teste independente.
Domínio e resíduos negativos são os guardas aceitos; não descartar traços.

Depois desse aceite,contratar integração com densidadeconstante como controle,
compressão/expansão suaves e balanço de energia total. Antes do solver fixar
histórias/tolerâncias/Radau vs BDF emenergia invertida/refinamento,controles
com reações congeladas e recusas em toda a trajetória. Gás clássico não
relativístico e radiação têm limites adiabáticos diferentes; só comparar
limites que correspondam aos componentes efetivamente presentes.
