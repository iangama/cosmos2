# IS5/C2-20 — extensão pp-II, contrato26/10/2026

Recorte independente em output/is5-pp2-staging. Preservar011/103/ciência
aceitos. Ampliar compartilhamento de combustível para12espécies/12canais:
dez anteriores+Be7/Li7;acrescentar He3+He4→Be7+γ,Be7+e−→Li7+ν,
Li7+p→2He4. pp-III/pep/hep/CNO-II permanecem identificados como pendentes.
Não duplicar H,He3 ou He4 entre ramos. Mesma composição inicial existente,
Be7/Li7 inicialmente zero;fixturesdeisolamentoseparadas podem conter traços.

Fontes/dados antes do código:

- Novos dois canais binários do pynucastro3.1.0 já instalado,REACLIB original
  congelado,hash/coeficientes/Qfit/avaliações independentes arquivados. Nove
  taxas anteriores continuam byteiguais. Sem atualização de dependências.
- CapturaBe7 do [SolarFusionII,eq40](https://arxiv.org/abs/1004.2318),
  R=5,60e−9*(rho_g_cm3*Ye)*T6^(−1/2)*[1+0,004*(T6−16)] s−1.
  Ye=sumZiYi;rhoSI/1000. Não aplicar n_b/NA ou outro fator de elétrons aR.
  O ajuste incorpora a aproximação solar de captura ligada+contínua e relata
  2% de incerteza. Não é meia-vida atômica de53dias nem lei geral de plasma.
- O domínio publicado é estrito10<T6<16. Esta extensão usa esse domínio
  paraTODOS os estados/coeficientes quandoBeEC estiver ligado;se estiver
  desligado,manter mesmo domínio explícito do modelo,sem ampliá-lo escondido.
  Produto01110–30MK fica preservado;este é outro modelo com limites próprios.
- MédiaνBe7 fixa0,814MeV,[Bahcall2001,TableI](https://arxiv.org/abs/hep-ph/0108148).
  Inclui média solar de efeitos térmicos; não recalcular espectro/ionização.
  TaxaBeEC solar eEOS ideal de bulk não evoluem estados atômicos doBe-traço;
  esta aproximação/omissões devem constar de saída,sem alegar precisãoSolar.

Nova geraçãoQ: derivar TODOS12Q de excessos de massa atômica AME2020
originais,usandoDecimal/cancelamento deA,emMeV. Mantêm-se Qfit antigos para
comparação/procedência,sem alterarredes aceitas. AtomicQβ+ inclui aniquilação
local;eEC usa diferençaBe7−Li7. Não tratar discrepânciaQfit/AME como erro
numérico ou ajustar coeficientes para ocultá-la. Preservar incertezas originais
de massa;covariâncias ausentes não geram barrasQ fictícias.

Atuação:He3α exige forte+EM,BeECfraca,Li7pforte;dependências antigas iguais.
Contarβ+ eEC separadamente:ν=β++EC;e+somenteβ+;e− consumidos=aniquilaçãoβ++EC.
ΔZnúcleos+Nβ++NEC=0. Qν/Eretida por extensão;aniquilação não é somada2vezes.

Primeiro rede prescritaT/rho/V e referênciacompleta. Depois modo térmico
comEOSideal aceita,usando soma12espécies e mesmo gradienteU(T,ni,ne),rho/V
fixos. Defaultnovo15MK/10kyr explícito;T que atinge16MK recusa integralmente,
sem cortar duração ou usar a leiEC fora do domínio. Não reutilizar1Myr de011
automaticamente. Novos layouts/arquivos não podem migrar silenciosamente.

Critérios antesworker/UI:

- Dois fits binários em10,1/12/15/15,9MK vsavaliadorpynucastro≤1e−12rel;
  EC emgradeT/rho/Ye vsDecimal50≤1e−12rel,linearidadeρYe,derivadacomposição
  presente noJac(seusada). Tipos/limites e gates4096 combinações conferidos.
- EstequiometriaA eZ+léptons exata;Qtotal pp-I/pp-II/CNO-I fecha na mesma
  diferença4H−He4 por construçãoDecimal. Dados primitvos/hashverificados.
- EC isolada comYeevoluindo: dBe/dt=−k*Ye*Be,Ye=Ye0−(Be0−Be),
  soluçãoanalítica logística,Li/e−/ν eausênciae+conferidos. Li7p isolado contra
  soluçãoanalítica2reagentes/2α,fator1/2nãoaplicadoaosprodutos.
- Rede mista vsBDFindep≤1e−8porbárion;refinar tolerância. Quando3novoscanais
  off,comparar composiçãoprescrita àredelegada,explicitando nova baseQ.
- Bárions≤1e−8,CNOcatalisadores≤1e−8,Z+leptões≤1e−10porbárion,energia
  recontada≤1e−12rel,abundâncias≥−1e−20,semclamp. Compararνporcanalcontado.
- Térmica futura contraBDFenergiaUinversa;|U−U0−Eretida|/max(U0,Edisp)≤1e−8.
  Nenhumaceiteintegrado atétestespróprios deworker/CEF/visual/perfil.
