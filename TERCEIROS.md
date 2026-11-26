# Origem dos componentes

- OpenSpace 0.22.0, commit `8b2778bed19f0c0501eed110c71dd00bd5305c55`.
  Runtime oficial sem modificações de binários; código e licenças preservados
  em `.runtime` e `.upstream/openspace`. A licença principal é MIT; os demais
  componentes têm avisos em `ACKNOWLEDGMENTS.md` do upstream.
- A cena Cosmos2 usa configurações e APIs públicas do OpenSpace. Referências:
  exemplos de globos, `allsky_visible.asset` e atalhos padrão da versão fixada.
- Terra: Blue Marble e luzes noturnas NASA, redistribuídas pelo servidor de
  dados OpenSpace. Lua: mosaico LRO WAC identificado pelo upstream.
- Via Láctea: panorama Mellinger / AMNH Digital Universe, conforme
  `scene/digitaluniverse/allsky_visible.asset`. É imagem de fundo, não uma
  reconstrução volumétrica. Rever termos específicos antes de distribuir.
- Modelo volumétrico adicional: dados de simulação NAOJ distribuídos pelo
  OpenSpace, conforme `scene/milkyway/milkyway/volume.asset` (MIT no asset).
  Catálogo de estrelas AMNH/Hipparcos/Gaia DR3: licença original preservada
  em `data/galaxy/license_stars.lua`. Esta prova é de uso pessoal local.
  A licença restringe redistribuição, uso público e comercial; o catálogo
  não deve integrar pacote público sem autorização específica ou substituição
  por dados com termos adequados. Recibos em `evidence/galaxy-acquisition.json`.
- REBOUND 5.2.2: biblioteca de integração gravitacional; licença GPLv3.
  A distribuição futura precisa preservar suas obrigações. Nesta prova,
  roda em Python nativo, em ambiente isolado.
- Python, websockets 15.0.1 e CMake 4.1.0: ferramentas locais isoladas.
- Microsoft Visual Studio Build Tools 2022: instalação oficial assinada;
  compilador e Windows SDK em `.tooling/vs-buildtools`.

URLs exatas, tamanhos e SHA-256 locais dos dados estão em
`evidence/scene-data.json`. O recibo do runtime é
`evidence/runtime-acquisition.json`. SHA-256 calculado localmente não equivale
a assinatura ou checksum publicado pelo fornecedor.

Nenhum pacote do Cosmos2 foi publicado ou distribuído nesta etapa.

## Bancada das quatro forças — 12/10/2026

- NumPy2.5.4 e SciPy1.18.1: cálculo científico no ambiente Windows isolado;
  avisos de licença das distribuições preservados em .tooling/python.
- pynucastro3.1.0: preparação do recorte de dados nucleares, sem necessidade
  de importar a biblioteca durante cada cálculo da bancada. Pins em
  requirements-science-windows.txt; runtime NumPy/SciPy em requirements-windows.txt.
- Taxa D+T: JINA REACLIB, conjunto de04, Descouvemont et al.,
  *Compilation and R-matrix analysis of Big Bang nuclear reaction rates*,
  Atomic Data and Nuclear Data Tables88,203(2004),
  https://doi.org/10.1016/j.adt.2004.08.001. Recorte original e SHA256 em
  data/science; método de extração em scripts/prepare-forces-data.py.
- Massas e ligações: AME2020, Chinese Physics C45(2021)030002/030003.
  Meias-vidas: NUBASE2020, Chinese Physics C45(2021)030001,
  https://doi.org/10.1088/1674-1137/abddae. Recortes via pynucastro; fontes
  e hashes das tabelas em data/science/nuclear.json. A ausência de incertezas
  nesses recortes é explicitada, sem declarar erro zero.
- Playwright1.58.0 e Edge Windows usados apenas para verificar a interface;
  nenhum resultado headless é benchmark gráfico do motor OpenSpace.

- Rede pp-I: taxas REACLIB bet+/de04/nacr, fontes/hashes por canal em
  data/science/pp1.json e pp1-*-reaclib.txt. nacr: Angulo etal.,
  *A compilation of charged-particle induced thermonuclear reaction rates*,
  Nuclear PhysicsA656(1999)3–183, https://doi.org/10.1016/S0375-9474(99)00030-5.
- Energia média de neutrinos pp: Bahcall2002, Phys.Rev.C65,025801, tabelaI,
  https://doi.org/10.1103/PhysRevC.65.025801. Não reproduzimos o artigo;
  o parâmetro/tabulação é identificado como aproximação solar fixa.
- Modificação local do OpenSpace: patches/frame-capture.patch adiciona captura
  limitada de intervalos SGCT e memória Windows/DXGI, sem alterar física ou
  shaders. Originais emoutput/upstream-original; fonte-base e hashes do build
  em evidence/built-runtime.json. Runtime oficial preservado separadamente.

- Perfil offline local: patches/offline-profile.patch altera HttpRequest,
  DownloadManager e switchesCEF; header Cosmos2 local emutil/cosmos2offline.h.
  Originais mantidos, distribuição oficial intacta. scripts/bootstrap-native-ui.py
  reemite somente aURL local após inicialização. Recibo updated built-runtime.json.
- CNO-I: seis recortes REACLIBls09/wc12/nacr/im05 emdata/science/cno1-*;
  hashes e fontes individuais emevidence/cno-data.json. Citação de ls09
  corrigida pela publicação primária Li etal., DOI10.1007/s11433-010-0128-8,
  preservando os campos brutos do pacote. im05: Imbriani etal.,
  DOI10.1140/epja/i2005-10138-7. NUBASE2020 fornece o beta+ padrão; comparação
  com wc12 legado disponível por escolha explícita. Médias de neutrinosCNO
  são os dois parâmetros da TabelaI deBahcall2002, com hipótese solar fixa;
  não reproduzimos o artigo. Núcleos, Q e dados sem incerteza extraída são
  identificados, sem alegar precisão absoluta.
- patches/galaxy-point-reader.patch adapta o leitorCOFF do OpenSpace: parsing
  numérico sem locale, contagem exata e recusa de linhas inválidas. Coordenadas,
  cores e conversão de escala upstream preservadas bit a bit na comparação
  dos22.885.870valores do arquivo local. Não altera o conteúdoNAOJ nem sua licença.
- patches/ghoul-utf8-font.patch aplica-se dentro deext/ghoul (commit
  668586014d24c2aa79b4ebe77f166bd959007155, MIT): decodificaUTF8 antes de
  medir/renderizar texto e guarda a referência de glifos ausentes uma vez.
  APIwchar_t existenteWindows éBMP; fora doBMP usa um glifo de substituição.
  Cabeçalhos/licenças originais preservados; helper novo é adaptaçãoCosmos2.

### IGRF14 e referência local — 13/10/2026

Coeficientes IAGA/NOAA em data/science/igrf14coeffs.txt, URL/SHA registrados
em evidence/igrf-acquisition.json. Crédito às equipes IAGA/IGRF14. Síntese
harmônica própria em app/geomagnetism.py, sem portar algoritmo Fortran BGS.
O original BGS igrf14.f fica em .upstream/igrf14 só como referência local de
comparação. A declaração NOAA de domínio público para Geomag7 não foi aplicada
ao código BGS. Não há nova autorização/licença de redistribuição inferida;
publicação futura exige conferir termos de cada componente.

GNU Fortran13.3 e pacote libgfortran-dev de repositórios oficiais Ubuntu foram
extraídos em .tooling/fortran para compilar a referência Linux, sem instalação
de sistema. Recibo igrf-reference-build.json guarda pacotes/hashes/flags; o
binário comparativo não é dependência Windows do produto. Avisos/licenças GNU
ficam nos pacotes locais, sem atribuir sua licença à nossa síntese independente.
Mapa usa a textura NASA já adquirida/creditada, por endpoint local fixo.

### Atlas solar —13/10

Kernels JPL/NAIF DE442s, naif0012 e PCK00011 emdata/spice, fontes/bytes/SHA
e MD5publicado conferido ematlas-kernels-acquisition.json. Comentários originais
preservados. Código SPICE do motor upstream intacto; bindingSpiceyPy8.2.0 instalado
no ambienteWindows, licençaMIT/avisos do pacote preservados. CréditoJPL/NAIF;
estado geométrico e modelos de orientação explicitados, sem garantia do Cosmos2
em nome dos fornecedores. Nenhuma publicação realizada.
Quatro fixturesHorizons preservam resposta/header/query/modelo/URL/hashes,
com créditoNASA/JPL e procedência independente do kernel local. Texturas e
catálogo continuam com seus próprios créditos/termos; não atribuir licença do
kernel ao catálogoAMNH nem ao conteúdo visual de origem diferente.
### Decaimentos avaliados ·13/10/2026

CSV LiveChart/ENSDF para dez pais fundamentais,19ramos, obtidos daAPIIAEA
com cutoff/autoria/extração por linha. Dez arquivos ground_states e dez
decay_rads beta são preservados em data/science/decays-*.csv. Original
NUBASE2020 (Kondev et al., CPC45,030001) conservado como comparação distinta,
não mesclado na avaliação operacional. Compilado decays.json e recibo
evidence/decay-data.json fixam origem/hashes; pacote science:decays.
Não foram incorporados códigos de solver ou PDFs de terceiros. Dados para
uso local com citação por fonte; revisão de distribuição continua C2-09/17.

### Misturas de fusão ·13/10/2026

Fusão em seis misturas: sete textos REACLIB originais preservados em
data/science/fusion-*-reaclib.txt, com coeficientes, fonte, Q, prefator e
SHA256 em fusion.json. Extração local pynucastro3.1.0; mesmos avisos/licença
da preparação científica existente. D+T/D+p/Li7+p usam Descouvemont2004;
D+D usa Gómez Iñesta/Iliadis/Coc2017 (gi17/go17); He3+He3 usa NACRE1999;
C12+alpha usa Xu et al.2013/NACRE2. Artigos não incorporados ao produto.
Referências F78/F79, aquisição em evidence/fusion-data.json; pacote
science:fusion fixa expectativas sem atualizar hashes durante verificação.

### Acervo nuclear original ·13/10/2026

Tabela mass_1.mas20 da colaboraçãoAMDC/IAEA, AME2020. Artigos deHuang et al.
CPC45,030002 eWang et al.CPC45,030003(2021), DOIs e fonte original emF74.
Arquivo472.648bytes/SHAe8599c6d…3307, preservado sem edição. Parser e instrumento
próprios; nenhum código de parser externo portado. O recortopynucastro/NUBASE
é usado só como verificação adicional e não substitui as incertezas/flags.
A orientação doAMDC pede citar os artigos e é atendida na interface/export.
Aquisição para uso local; termos da tabelaASCII não foram inferidos da licença
doPDF. Revisão do pacote distribuível permanece emC2-09/17; não houve publicação.

Saturno C2-02: kernel original SAT459 JPL/NAIF, fonte699 SAT441/SAT441xl. Apenas segmentos699 recortados por CSPICE spksub; original em output/saturn-acquisition, recibos em evidence. Não ajustamos órbita nem redistribuímos o kernel original nesta etapa. Mapa Saturn.jpg de NASA3D/JPL-Caltech, explicitamente ficcional na fonte https://science.nasa.gov/3d-resources/saturn/ ; crédito preservado por propriedade/pacote. Mapa ilustrativo, não imagem observada em época conhecida. Uso local; publicação segue sem autorização.

C2-03: mapa ativo de Saturno2880×1440 distribuído pelo OpenSpace em saturn_textures/v1, e cinco perfis radiais1500×1 emv4. URLs/SHA/tamanhos em evidence/saturn-openspace-map.json e saturn-rings-acquisition.json. Origem observacional/época e licença específica das imagens não confirmadas; não atribuir NASA/Cassini por suposição. Uso local; mapa NASA ficcional anterior permanece como alternativa inativa. RingsComponent/ShadowsComponent são códigoOpenSpace MIT; dimensões e perfil não implicam simulação de partículas, fotometria aparente ou transporte radiativo.

C2-06, 14/10: gravity-experiments.json contém três condições iniciais definidas
localmente, sem dataset observacional. Pesquisa numérica própria; a referência
McMillan/Hut (1996), astro-ph/9604015, fornece o contexto de espalhamento e
não os números deste catálogo. Nenhum texto/código do artigo foi incorporado.
IAS15/REBOUND e DOP853/SciPy foram usados com suas licenças já registradas.
Prévia de cônicas usa RenderableConstellationLines do OpenSpace, código MIT;
SPECK/NamesFile/recibos em output/orbit-previews são derivados locais.
A correção camera-relative-label.patch modifica RenderableLabel OpenSpace
para montar glifos perto da câmera antes da conversão para float32. Preserva
copyright/licença upstream; não altera posições científicas nem efemérides.
