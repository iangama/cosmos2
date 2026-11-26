# IS5/C2-20 — extensão CNO-II, contrato de 27/10/2026

Nova etapa isolada após pp-III, preservando todos os aceitos. A rede passa a
16 espécies e 18 canais. Somar O-16, F-17 e O-17; N-15(p,γ)O-16,
O-16(p,γ)F-17, F-17→O-17+e⁺+ν e O-17(p,α)N-14. O ramo compete com
N-15(p,α)C-12 pelo mesmo combustível. Sua fração é calculada, sem razão fixa.
A topologia e o fechamento do ramo II estão em
[Solar Fusion II, XI.B e tabela XII](https://arxiv.org/pdf/1004.2318v3).

Dados antes do modelo: quatro fits originais da REACLIB instalada e fixada
pynucastro3.1.0; conservar integralmente os 14 registros anteriores. F-17 usa
NUBASE2020 original (valor, unidade e incerteza arquivados) e wc12 comparativo.
Tratar a meia-vida terrestre como coeficiente do canal β⁺ é uma aproximação
explícita; EC em N13/O15/F17 não é resolvida nesta rede. Não apresentar
esses canais como todas as ramificações fracas do plasma.
Média νF17 fixa 0,9977 MeV de
[Bahcall1997, equação36](https://arxiv.org/pdf/hep-ph/9710491v1), com PDF
original arquivado. Não atribuir esse valor à tabela I de Bahcall2001 nem
recalcular um espectro local. Q dos18 canais por AME2020 atômica original;
incertezas de massas preservadas, sem covariância/Q derivada inventada.

Mesmos modos prescrito e térmico ideal isocórico, domínio estrito10<T6<16,
rho/V fixos, neutrinos escapam e radiação LTE fica confinada. Condições
iniciais15MK/10kyr/H0,34/catalisador0,01; permitir semente C12,N14 ou O16
explícita. Fração catalítica acompanha número de C/N/O/F do ciclo, não inclui
Be/Li/B da cadeia pp. EOS considera todas16 espécies/neutralidade variável.
Capturas radiativas novas dependem forte+EM, F17β só fraca, O17pα só forte.
B8 continua efetivo como contratado, sem populaçãoBe8 resolvida. Sem CNOIII/
hotCNO/pep/hep, screening, transporte, hidrostática ou luminosidade superficial.

Antes de worker/UI:

- Quatro novos fits × quatro temperaturas contra o avaliador original,
  erro≤1e−12rel; F17NUBASE e wc12 separados.18Q e cinco ciclos ppI/II/III,
  CNOI/II fecham Decimal4H−He4. S conservaA eZ+léptons exatamente.
- Todas8atuações×16máscaras dos4novos e independência dos18 controles;
  herdados14 já aceitos são importados sem alterações. Jacobiano de todas
  espécies incluiYe variável da EC;erro de diferença finita≤2e−7rel.
- F17isolado analítico exponencial: O17,e⁺,aniquilação,ν,energia nuclear/ν;
  fixture térmica contra energiaU+inversãoEOS,erroT≤1e−7rel.
- Competição N15pα/N15pγ contra solução analítica de combustível finito,
  H variável e razão determinada pelos fits, sem reação subsequente nofixture.
- Misto prescrito e térmico contra BDF independente (energiaU invertida),
  refinamento e novos4off contra pp-III,≤1e−8porbárion/≤1e−7relT.
- SementeO16/fechamentoCNOII com extents positivos;conservação do pool
  catalítico ampliado. Balanço térmico≤1e−8normalizado,contagem/energiaν
  recontadas≤1e−12rel. Tipos/domínios/semente inválida e saída térmica
  recusados integralmente;sem clamp/encurtar duração. Arquivar fontes antes.

Worker/CEF/visual/perfil terão contratos próprios depois do aceite científico.
