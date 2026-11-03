# IS5/C2-20 — zona térmica isocórica, contrato26/10/2026

Integração produtal segue depois do perfil103; pesquisa/EOS isoladas podem
avançar enquanto o coletor mede, sem testes CPU concorrentes. Construção em
output/is5-thermal-staging,sem editar103,stagingprescrito ou sessões.
Reutilizar nove taxas fixadas/estequiometria pp-I/CNO-I por mérito, sem
atualizar bases nucleares. Este recorte acrescenta EOS/reservatório; não
conclui C2-20,redes pp-II/III,screening ou evolução estelar completa.

Fontes primárias consultadas26/10/2026:

- MESA EOS overview, https://docs.mesastar.org/en/stable/eos/overview.html:
  distingue P,E,Cv,composição e regimes. Versão vista26.4.1 é referência,
  não solver instalado nem base nuclear substituída.
- F.X.Timmes, https://cococubed.com/code_pages/eos.shtml:
  primeira lei/identidades termodinâmicas; EOS completa possui ingredientes
  além desta mistura ideal. Não copiar código/tabelas nem chamar istoHELM.
- NIST DLMF25.12.14/16, https://dlmf.nist.gov/25.12#iii:
  F_s(eta)=integral x^s/(exp(x-eta)+1)dx/Gamma(s+1)
  =−Li_(s+1)(−exp(eta)). A referência numérica será polylog mpmath50dps.

EOS candidata: mistura totalmente ionizada. Íons clássicos ideais; elétrons
ideais Fermi–Dirac não relativísticos com spin2 e neutralidade ne=nb*sum(ZiYi);
radiação LTE confinada. Não incluir pares térmicos,ionização parcial,Coulomb,
screening,transporte/hidrostática ou campo de massa pontual interior.
Identificar omissões e parâmetros kT/(mec²),pF/(mec),degenerescência eGamma.
Resíduo numérico não é incerteza da aproximação física nem equivalênciaMESA.

lambda_e=h/sqrt(2*pi*me*kT),C=2/lambda³,ne=C*F_1/2(eta).
Pe=C*kT*F_3/2;ue=3Pe/2;ui=3nb*kT*sum(Yi)/2;ur=a*T^4.
P=nb*kT*sum(Yi)+Pe+ur/3;u=ui+ue+ur(emJ/m³,sem massas de repouso).
dF_s/deta=F_(s−1). Derivar Cv_e|ne=(3/2)ne*k[(5/2)F3/2/F1/2−
(3/2)F1/2/F−1/2] e due/dne|T=(3/2)kT*F1/2/F−1/2.
du/dYi|T=nb[(3/2)kT+Zi*due/dne]. Cvtotal inclui4aT³.

Densidade/volume fixos: nenhuma expansão nem trabalhoPdV. Neutralidade e
contageme−mudam com a rede/aniquilação já contabilizada noQatômico fixado.
dY/dt=S*F(T,Y);dxi/dt=F. Energia nuclear disponível=P_Q; neutrinos escapam
na hipótese local,P_nu. Todo restante fica no reservatório gás+radiação:
Cv*dT/dt=P_Q−P_nu−sum(du/dYi*dYi/dt). Sem perda fotônica ouluminosidade
superficial; radiaçãoLTE confinada é energia armazenada, não emissão.

Condições iniciais do contrato prescrito; T deve permanecer10–30MK e rho
1e4–3e5kg/m³ em todos os estados avaliados. Cálculo que sai do domínio é
recusado integralmente, semclamp,extrapolarfit ouencurtarduração emsegredo.
Podem ocorrer recusas conservadoras emestágios implícitos do solver; não
apresentar instante de parada como evento físico precisamente localizado.
Referência completa e gates têmsemânticaigualprescrito;ocultarindependente.

Antes de integrarUI:

- F−1/2,F1/2,F3/2 emeta−20..20 vs−polylog50dps ≤2e−10rel.
- EOS emgradeT/rho/composição: raizne≤1e−10rel; Pe,ue,Cv,du/dYi
  contra montagem independente/polylog e diferenças centrais≤2e−6rel.
  Cv>0,P/u finitos; Maxwell P−rho²*de/drho−T*dP/dT≤2e−6rel aYfixo.
  Limite clássico viaeta−20,termos radiação e unidades explicitados.
- Evolução Radau vsBDF independente com energiaU como variável e inversão
  EOS→T,estado máximo≤1e−7relT/1e−8porbárion; refinar tolerâncias.
- Bárions≤1e−8,catalisadores≤1e−8,carga+beta≤1e−10porbárion;
  energia |U−U0−(Edisp−Enu)|/max(U0,Edisp)≤1e−8.
  Para exposiçõescurtas,contarEpelasextensões: não inferirenergiazero pela
  subtraçãodeUgrandes. Não clamp abundâncias nem tempo/T.
- Todosoff mantém T/composição/U; supressõesfraca/EM preservam canais
  permitidos. Inicial15MK,misto/pp-only/CNO-only/quente-curto/cold1s,
  recusas de tipos/domínio/orçamento,fonteimutável e geraçãoarquivada.

Só depoisciência:worker/persistência/controles próprios,cenaSolararquivada,
testesCEF/capturas/perfil. Perfis/trilhas estelares de referência permanecem
pendentes; não inferir umperfil doSol ouevolução deestrela real desta zona.
