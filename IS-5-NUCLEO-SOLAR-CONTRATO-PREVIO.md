# IS5 — zona solar pp-I/CNO-I acoplada, contrato prévio26/10/2026

Implementar primeiro em output/is5-solar-core-staging, preservando0.9.1,
instalado e sessões. Associar instrumento ao Sol10 de uma cópia solar pausada,
com identidade/revisão/época/referencial/GM explícitos. O relógio da rede é
independente da órbita; nenhuma reação altera silenciosamente os quatro centros.
Não usar o campo de massa pontual dentro do núcleo ou afirmar hidrostática.

Reutilizar por mérito as taxas/dados fixados pp1.json e cno1.json, suas fontes
REACLIB/pynucastro3.1.0 e avaliações beta identificadas. Não atualizar taxas
porque a documentação pública mudou. Corrigir ROOT somente nas novas cópias
isoladas: módulos legados em app funcionam na raiz original, mas suas cópias
em output assumem pais[1] inadequadamente. Preservar originais e hashes.

Fontes primárias consultadas: documentação pynucastro sobre forma/unidades das
taxas https://pynucastro.github.io/pynucastro/rate_types.html;
Adelberger et al.,SolarFusionII,https://arxiv.org/abs/1004.2318;
médiasν já fixadas https://arxiv.org/abs/hep-ph/0108148,tableI.
Reutilizarcoeficientesavaliados;SolarFusionII é contexto/referência,sem trocar
os fits locais por recomendações diferentes sem contrato e validação próprios.

Uma zona homogênea: dez núcleos p,d,He3,He4,C12,N13,C13,N14,O15,N15 e nove
canais pp,dp,He3He3,C12pg,N13beta,C13pg,N14pg,O15beta,N15pa. Compartilhar
p/He4; não somar duas zonas que consumam o mesmo hidrogênio separadamente.
Abundâncias Yi=ni/nb,nb=rho/mu convencional; frações mássicas AiYi. Massa
defeituosa pertence ao balançoQ, não a essa normalização convencional.

Para reação binária: Fj=nb*(lambda_molar*1e−6/NA)*prod(Yi)/prod(mi!);
para beta: Fj=lambda_s*Ypai. Usar cada fator idêntico1/2 uma única vez.
dY/dt=S F; dxi/dt=F. Integrar composição e extensões com Radau/Jacobiano
analítico; não reconstruir traços minúsculos por subtração de extensões grandes.

Domínio: T10–30MK,rho1e4–3e5kg/m³,H0,05–0,75,CNO0–0,05,
sementeC12ouN14,He4 restante,D/He3/N13/C13/O15/N15 inicialmente zero.
Tempo1s–5e9anosJulianos,volume1e−6–1e18m³,ambos prescritos. Condições-padrão
didáticas:15MK,1,5e5kg/m³,H0,34,CNO0,01,N14,1m³; sem ajuste a um perfil
solar observado. Exigir números finitos e recusarbool/campos extras.

Gates de atuação forte/fraca/EM e de cada canal, separados da visualização.
pp exige forte+fraca,dp e capturas CNO exigem forte+EM,He3He3/N15pa forte,
N13/O15beta fraca. Suprimir operador preserva referência e parâmetros
avaliados; não recalcular um universo sem constante fundamental.

Q atômicos dos fits incluem aniquilação local dos pósitrons. Contar eventos
pp/N13beta/O15beta, produção de e+/ν e consumo de elétrons na hipótese de
aniquilação. Verificar ΔZnúcleos+Nbeta+=0. Energia disponível=sum(Qj xij),
energiaν com médias fixas0,2668/0,706/0,996MeV. Restante nãoν é energia
disponível localmente sob hipótese de retenção; não é temperatura evoluída
ou luminosidade superficial. Reservatório térmico/EOS e transporte não
modelados devem aparecer indisponíveis, sem converter potência nuclear
instantaneamente em luz do Sol ou fluxo espacial de neutrinos.

Critérios antes de implementar/medir:

- Nove taxas em10/15/20/30MK contra referências locais/avaliador independente,
  ≤1e−12rel; unidades/binários/betas e fatores idênticos explícitos.
- Estequiometria conserva bárions e catalisadores exatamente; cargas fecham
  com leptões por canal. Evolução: erro bariônico≤1e−8,erro relativo do número
  de catalisadores≤1e−8,fechamentoZ+beta≤1e−10 por bárion; sem abundâncias
  abaixo−1e−20 ou valores nãofinitos. Não fazer clamp.
- Limites pp-only e CNO-only contra provedores legados preservados:
  composição/extensões≤1e−8 por bárion; casos mistos contra BDF independente
  com RHS montado dos canais,≤1e−8 por bárion e refinamento de tolerância.
- Energia eν recontadas das extensões≤1e−12rel; não negatividade e energiaν
  ≤disponível. Exposições pequenas mantêm extensões/energia não nulas;
  duração/volume não alterados automaticamente por T/gates.
- Gates e tipos/limites,imutabilidade de fontes,identidadeSolar,arquivos e
  geração científica. Arquivar receitas/fontes/brutos antes executar.

Depois da ciência: artefato/worker e UI próprios,controles,sonda,save/load/
ramos/export/restart e jornadasCEF/capturas/perfil adequados. Esta primeira
zona não conclui IS5 nem C2-20: pp-II/III,screening,resposta térmica,perfis
estelares,transporte e emissão espacial continuam com contratos próprios.
