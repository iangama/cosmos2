# Fontes oficiais — Cosmos2

Consultadas em 11/10/2026. Lista de referências, não uma lista de dependências
instaladas. Páginas `latest` e `master` podem mudar. A implementação deve fixar
versões e conferir os termos de cada componente e conjunto de dados utilizado.

| ID | Fonte | Decisão sustentada |
| --- | --- | --- |
| F01 | [SpaceEngine — apresentação](https://spaceengine.org/) | Experiência de exploração, catálogos e geração procedural |
| F02 | [SpaceEngine — FAQ](https://spaceengine.org/manual/faq/) | Código fechado; referência de produto |
| F03 | [Universe Sandbox — FAQ](https://universesandbox.com/faq/) | Física N-corpos e simplificações |
| F04 | [Universe Sandbox — explicação histórica N-corpos](https://universesandbox.com/blog/2016/02/n-body-problem/) | Relação entre passo, custo e erro; não descreve necessariamente o solver atual |
| F05 | [Universe Sandbox — roteiro 2026](https://universesandbox.com/blog/2026/03/universe-sandbox-roadmap-2026/) | Ambição de produto; separar pesquisa e recursos entregues |
| F06 | [Universe Sandbox — Update 36](https://universesandbox.com/blog/2026/03/pale-blue-dots-update-36/) | Anúncio distinto do roteiro |
| F07 | [Celestia — repositório](https://github.com/CelestiaProject/Celestia) | Controles, catálogos, extensão e GPL-2.0-or-later |
| F08 | [Celestia — coordenadas universais](https://github.com/CelestiaProject/Celestia/blob/master/src/celengine/univcoord.h) | Alta precisão e diferenças locais |
| F09 | [Celestia — instalação por código](https://github.com/CelestiaProject/Celestia/blob/master/INSTALL.md) | Alternativa técnica a investigar na prova |
| F10 | [OpenSpace — repositório](https://github.com/OpenSpace/OpenSpace) | Base de astrovisualização |
| F11 | [OpenSpace — licença da v0.22.0](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/LICENSE.md) | Termos do código principal e referência a terceiros |
| F12 | [OpenSpace — release v0.22.0](https://github.com/OpenSpace/OpenSpace/releases/tag/releases/v0.22.0) | Candidata observada em 11/10/2026 |
| F13 | [OpenSpace — compilação](https://docs.openspaceproject.com/latest/contribute/development/compiling/index.html) | Requisito OpenGL e risco AMD |
| F14 | [OpenSpace — instalação v0.22](https://docs.openspaceproject.com/releases-v0.22/getting-started/install/index.html) | Requisitos e perfil padrão dependente de rede |
| F15 | [OpenSpace — camadas de terreno](https://docs.openspaceproject.com/releases-v0.22/building-content/globebrowsing/working-with-layers.html) | Cor, relevo, iluminação e níveis de detalhe |
| F16 | [OpenSpace — controles de globos](https://docs.openspaceproject.com/latest/using-openspace/users/7-menus-globebrowsing.html) | Iluminação, eclipses e atmosferas |
| F17 | [OpenSpace — interface personalizada](https://docs.openspaceproject.com/latest/building-content/custom-web-ui/index.html) | Ponto de partida da interface própria |
| F18 | [OpenSpace WebGui — manifesto](https://github.com/OpenSpace/OpenSpace-WebGui/blob/master/package.json) | Stack atual da interface; compatibilidade por fixar |
| F19 | [OpenSpace — Translation](https://github.com/OpenSpace/OpenSpace/blob/master/include/openspace/scene/translation.h) | Possível adaptador de posições em double |
| F20 | [OpenSpace — build da release](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/CMakeLists.txt) | CMake e CEF |
| F21 | [OpenSpace — submódulos da release](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/.gitmodules) | Versões coordenadas de dependências |
| F22 | [Unreal — Large World Coordinates](https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-in-unreal-engine-5) | Alternativa de motor e precisão |
| F23 | [Unreal — renderização LWC](https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-rendering-in-unreal-engine-5) | Posição relativa à câmera e custo de precisão |
| F24 | [Unreal — licenciamento](https://www.unrealengine.com/license) | Dependência dos termos à modalidade de uso |
| F25 | [wgpu](https://github.com/gfx-rs/wgpu) | Alternativa de API gráfica própria |
| F26 | [REBOUND](https://github.com/hannorein/rebound) | Worker gravitacional candidato, plataformas e licença |
| F27 | [REBOUND — integradores](https://rebound.hanno-rein.de/integrators/) | Escolha de método por regime |
| F28 | [NAIF — SPICE](https://naif.jpl.nasa.gov/naif/aboutspice.html) | Efemérides, referenciais e geometria |
| F29 | [JPL — manual Horizons](https://ssd.jpl.nasa.gov/horizons/manual.html) | Referencial, centro, tempo e correção de luz na comparação |
| F30 | [Gaia DR3 — dados](https://www.cosmos.esa.int/web/gaia/data-release-3) | Catálogo, acesso e créditos |
| F31 | [Gaia DR3 — conteúdo](https://www.cosmos.esa.int/web/gaia/dr3) | Tamanho do conjunto completo; extrair recortes |
| F32 | [NASA Exoplanet Archive — TAP](https://exoplanetarchive.ipac.caltech.edu/docs/API_resources.html) | Consultas reproduzíveis e tabelas |
| F33 | [NASA Exoplanet Archive — créditos](https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html) | Atribuição ao arquivo e artigos de origem |
| F34 | [NASA SVS — CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/) | Candidato a mapas lunares com procedência |
| F35 | [Bruneton — dispersão atmosférica](https://ebruneton.github.io/precomputed_atmospheric_scattering/) | Referência técnica de renderização, se a base exigir extensão |
| F36 | [Geant4 — escopo](https://geant4.web.cern.ch/about/) | Extensão futura de partículas e matéria |
| F37 | [pynucastro — visão geral](https://pynucastro.github.io/pynucastro/intro.html) | Extensão futura de redes nucleares |
| F38 | [pynucastro — dados de terceiros](https://pynucastro.github.io/pynucastro/sources.html) | Fontes de taxas e cuidado com extrapolação |
| F39 | [AMD — Radeon RX 7600](https://www.amd.com/en/products/graphics/desktops/radeon/7000-series/amd-radeon-rx-7600.html) | Especificação nominal de 8 GB; não é benchmark desta máquina |

## Limites da investigação

Na investigação inicial não houve acesso ao código proprietário, benchmark
comparativo, download de catálogos ou validação executável de bibliotecas.
A implementação posterior e suas evidências estão em LEIA-PRIMEIRO.md.
O site principal do Celestia
negou acesso automatizado; o repositório oficial foi suficiente para esta
pesquisa. Caminhos presumidos inexistentes no OpenSpace foram descartados;
foram conferidos os arquivos efetivamente presentes na tag candidata.

Não tratar páginas promocionais como comprovação de precisão científica.
Metas de desempenho, fórmulas de aceite, sequência, arquitetura de integração
e estimativas de esforço são propostas do Cosmos2 descritas nos outros
documentos. Não foram anunciadas pelos projetos de referência.

## Ampliação científica — consulta de 12/10/2026

| ID | Fonte primária | Uso no plano 2.0 |
| --- | --- | --- |
| F40 | [REBOUNDx — efeitos](https://reboundx.readthedocs.io/en/latest/effects.html) | Candidato a marés, harmônicos gravitacionais e correções; validar compatibilidade com REBOUND fixado |
| F41 | [PlasmaPy — Boris](https://docs.plasmapy.org/en/stable/api/plasmapy.simulation.particle_integrators.BorisIntegrator.html) | Convenções SI, atualização de partículas e domínio não relativístico |
| F42 | [NOAA/IAGA — IGRF](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field) | Campo principal terrestre, coeficientes e referência de comparação |
| F43 | [EinsteinPy — artigo dos autores](https://arxiv.org/abs/2005.11288) | Geodésicas em métricas fixas; candidato a protótipo/referência, sem promessa de renderer em tempo real |
| F44 | [EinsteinPy — implementação geodésica](https://github.com/einsteinpy/einsteinpy/blob/main/src/einsteinpy/geodesic/geodesic.py) | Inspeção do escopo do código; fixar versão antes de adoção |
| F45 | [NASA Exoplanet Archive — consultas](https://exoplanetarchive.ipac.caltech.edu/docs/API_queries.html) | Recortes reproduzíveis do conteúdo exoplanetário |

As páginas de documentação EinsteinPy consultadas retornaram 502; o artigo e
repositório foram acessíveis. A página Gaia DR3 retornou 451 nesta consulta;
nenhuma nova cobertura ou quantidade disponível foi inferida dessa falha.
Quantidades, tolerâncias e sequência novas são decisões de planejamento do
Cosmos2, não resultados publicados por essas fontes. Não foram instaladas
novas dependências nem executados novos benchmarks nesta revisão documental.

## Quatro forças — revisão3.0,12/10/2026

F46: CERN, https://home.cern/science/physics/standard-model/ — interações
fundamentais e distinção do modelo gravitacional.
F47: DOE, https://www.energy.gov/science/np/articles/proton-proton-fusion-powering-sun
— participação de múltiplas interações no processo pp.
F48: https://pynucastro.github.io/pynucastro/rate_types.html — taxas e convenções.
F49: https://www-nds.iaea.org/amdc/ — AME2020/NUBASE2020.
F50: https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html — dados nucleares.
F51: https://iauarchive.eso.org/static/resolutions/IAU2015_English.pdf — parâmetro
gravitacional solar nominal. O endereço antigo www.iau.org retornou404.
A revisão3.0 já implementou e testou quatro casos iniciais; consultar evidências
atualizadas, sem estender esse aceite às quatro teorias físicas completas.

F52: Bahcall, *The luminosity constraint on solar neutrino fluxes*,
Phys.Rev.C65(2002)025801, https://arxiv.org/abs/hep-ph/0108148 — tabelaI,
média solar pp0.2668MeV. Usada como aproximação fixa na zona pp-I.
F53: Microsoft, https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/nf-dxgi1_4-idxgiadapter3-queryvideomemoryinfo
— orçamento e uso de memória de vídeo do processo, por adaptador/segmento.
F54: Microsoft, https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo
— leituras de memória de cada processo; distinguir working set de commit privado.
F55: Microsoft, https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32w
— enumeração dos filhos dos PIDs conhecidos do produto para somar memória.

- F56: [Carroll, Lecture Notes on General Relativity, seção7](https://ned.ipac.caltech.edu/level5/March01/Carroll3/Carroll7.html), gr-qc/9712019. Métrica Schwarzschild, geodésicas nulas, esfera de fótons e relógios estáticos; base do palco Luz e relógios.
- F57: [libcurl URL API](https://curl.se/libcurl/c/curl_url_get.html) e [Chromium Network Settings](https://www.chromium.org/developers/design-documents/network-settings/): interpretação do host e proxy restrito ao processo para ensaio offline.
- F58: [pynucastro, exemplo pp/CNO](https://pynucastro.github.io/pynucastro/examples/pp-cno.html): seis canais CNO-I e comparação independente das derivadas; as escolhas da bancada são registradas por canal.
- F59: [Li et al., determinação de ¹²C(p,γ)¹³N](https://link.springer.com/article/10.1007/s11433-010-0128-8), Science China Physics, Mechanics & Astronomy53,658–663(2010): citação corrigida do conjunto REACLIBls09, cujo HTML estava malformado.
- F60: [Imbriani et al., ¹⁴N(p,γ)¹⁵O](https://epja.epj.org/articles/epja/abs/2005/12/10050_2005_Article_2503/10050_2005_Article_2503.html), Eur.Phys.J.A25,455–466(2005), DOI10.1140/epja/i2005-10138-7: conjuntoim05, mediçãoLUNA e extrapolação dependente do modelo. Incerteza não é tomada como zero.
- F61: [Fitzpatrick, problema circular restrito](https://farside.ph.utexas.edu/teaching/celestial/Celestial/node80.html), material do autor na UT Austin: fontes circulares, unidades/referencial e equações espaciais. [Abad et al., CMDA135:7(2023)](https://link.springer.com/article/10.1007/s10569-022-10118-z), DOI10.1007/s10569-022-10118-z: formulação girante, Jacobi, L1–L5 e critério linear de estabilidade triangular. Usados na bancada binária delimitada.
- F62: [NIST/CODATA2022, tabela oficial](https://physics.nist.gov/cuu/pdf/wall_2022.pdf): G=6.67430e-11m³kg⁻¹s⁻², incerteza padrão1.5e-15. Conversão da massa nominal do laboratório; GM0continua definido pela resoluçãoIAU2015, sem chamar a massa resultante de medida observacional solar.
- F63: [Microsoft, GPUs in the Task Manager](https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/): métricas WDDM/VidMm, diferença entre memória dedicada e RAM compartilhada; por processo inclui alocações compartilhadas entre processos, cuja soma repete recursos. O total por adaptador inclui todos os aplicativos.
- F64: [Microsoft, contadores de memóriaGPU incorretos](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value), KB4490156: defeito documentado para Windows10, com comparação WPR/WPA. Limitação considerada no diagnóstico; não extrapolada como defeito confirmado no Windows11 deste computador.
- F65: [Unicode Consortium, UTF e BOM](https://www.unicode.org/faq/utf_bom.html): distinção entre bytes UTF8, unidades UTF16 e escalares Unicode. O patchGhoul decodifica antes de consultar glifos; sua API wchar_tWindows mantém fallback explícito fora doBMP.
- F66: [Microsoft, from_chars](https://learn.microsoft.com/en-us/cpp/standard-library/charconv-functions?view=msvc-170): conversão numérica sem locale e sem alocação por valor. O leitorCOFF valida contagem, fim do token e valores finitos, comparados bit a bit ao leitor original.
- F67: [Fitzpatrick, campo dipolar](https://farside.ph.utexas.edu/teaching/jk1/Electromagnetism/node52.html), equação660; [espelhamento em dipolo](https://farside.ph.utexas.edu/teaching/plasma/lectures/node24.html), equações2.92–2.100. Fundamento da bancada ideal prescrita DIPOLO.md; implementação conferida em dipole-check.json, sem atribuir campo real terrestre ao dipolo ideal.
- F68: [NOAA/NCEI IGRF14](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field), [coeficientes IAGA](https://www.ngdc.noaa.gov/IAGA/vmod/coeffs/igrf14coeffs.txt), [Fortran de referência](https://www.ngdc.noaa.gov/IAGA/vmod/igrf14.f) e [BGS](https://geomag.bgs.ac.uk/research/modelling/IGRF.html): época 1900–2030, harmônicos até grau13, variação secular até8. Arquivos fixados e comparação em58casos; não inferir que a declaração de domínio público do código NOAA Geomag7 licencia o Fortran BGS.
- F69: [NGA WGS84](https://earth-info.nga.mil/?action=wgs84&dir=wgs84): elipsoide a=6378137m, 1/f=298.257223563; conversão precisa, distinta das constantes arredondadas do Fortran de referência.
- F70: [NCEI limitações do IGRF](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field/health-warning): campo principal não descreve todos os campos externos/locais. Estatísticas históricas BGS não são barras de erro locais exatas nem precisão garantida em2030. Resíduos numéricos do Cosmos2 não equivalem a erro observacional.
- F71: [JPL DE442 comentários](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442_tech-comments.txt), [recorte DE442s](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442s.mrg), [checksums publicados](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/aa_checksums.txt): modelo fixado para Sol/Terra/Lua, recorte1849–2150 e MD5conferido. SHA256local e cobertura efetiva em recibos; não é assinatura ou incerteza de posição.
- F72: [NAIF spkezr](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkezr_c.html), [LSKnaif0012](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls), [PCK00011](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc): estado geométrico, conversão de tempo e orientações gerais. [SpiceyPy8.2](https://spiceypy.readthedocs.io/en/stable/installation.html) no PythonWindows isolado, CSPICEN0067.
- F73: [Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html): consultasVECTORS/ICRF/FRAME/NONE/SSB/KM-S/JDTDB preservadas em evidence/horizons-atlas-*.json. Respostas identificamDE441, distinto do nossoDE442s; não exigir igualdade de modelos diferentes nem chamar diferenças de precisão observacional.
- F74: Huang et al., *The AME2020 atomic mass evaluation (I)*, Chinese Physics C45,030002(2021), [DOI](https://doi.org/10.1088/1674-1137/abddb0), [PDFAMDC](https://www-nds.iaea.org/amdc/ame2020/AME2020-a.pdf); Wang et al., *The AME2020 atomic mass evaluation (II)*, C45,030003(2021), [DOI](https://doi.org/10.1088/1674-1137/abddaf), [PDFAMDC](https://www-nds.iaea.org/amdc/ame2020/AME2020-b.pdf). Arquivo original [mass_1.mas20](https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt) fixado e conferido em13/10. Cabeçalho especifica formato Fortran, estimativa# e ausência*. ArtigoI,página4, fixa u·c²=931494.10242keV usado no cheque independente. Citados os artigos como solicitado peloAMDC; DOI recusado pelo crawler, PDFs oficiais acessíveis.
- F75: [pynucastro — propriedades nucleares](https://pynucastro.github.io/pynucastro/nucleus.html): o recorte instalado vem deNUBASE2020/CODATA2018; é uma comparação adicional de valores centrais, não autoridade para incertezas/flags da tabelaAME original. O16 difere7e-5keV no último dígito; evidência conserva essa diferença.
- F76: [NNDC QCalc2020](https://www.nndc.bnl.gov/qcalc/), consultado13/10: serviço público usaAME2020 e declara não incluir covariâncias. Noveconsultas/respostas eSHA em evidence/nndc-qcalc-reference.json. ValorescentraisQ comparados pela resolução publicada; incertezas/limiares divergentes permanecem no relatório, sem forçar equivalência. HTML/JS preservados apenas para pesquisa, não incorporados ao produto.
- F77: [UCSD Física200A, capítulo15 §15.7.3](https://courses.physics.ucsd.edu/2009/Fall/physics200a/LECTURES/CH15.pdf), equações15.177–180: alvofixo, invariante relativístico e energia mínima total do projétil; subtrairrepouso para cinética. [LBL, reaçõesnucleares](https://www2.lbl.gov/abc/wallchart/chapters/07/0.html): conservaçãoA/Z/energia/momento. Limiares energéticos não substituem taxa/barreira/tunelamento.
- F78: [Gómez Iñesta, Iliadis e Coc, D+D (2017)](https://arxiv.org/abs/1710.01647), ApJ849,134, DOI10.3847/1538-4357/aa9025: dois canais D(d,n)He3 e D(d,p)T; fits REACLIB gi17/go17 preservados na bancada. Não impor proporção50/50 nem transformar erro numérico em incerteza experimental.
- F79: [pynucastro, código Rate](https://pynucastro.github.io/pynucastro/_modules/pynucastro/rates/rate.html): fator estatístico1/2 para pares idênticos, produto de abundâncias e estequiometria. [REACLIB nac2](https://reaclib.jinaweb.org/labels.php?action=viewLabel&label=nac2) confirma Xu et al., NACRE2, Nucl.Phys.A918,61(2013), fonte C12(alpha,gamma)O16. Sete textos/coefs/Q/referências extraídos da versão3.1.0instalada em data/science/fusion*; domínio e hipóteses em FUSAO-CANAIS.md.
- F80: [IAEA LiveChart API](https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html), [notebook oficial](https://iaea-nds.github.io/lc_api_notebook/) e [NDLab](https://iaea-nds.github.io/ndlab/code.html): CSV ENSDF, seleção de estado fundamental, radiações beta−/beta+/EC, médias de neutrinos e cutoff/autores por linha. ExtraçãoUTC14/10/2026 em21arquivos usados; recibo evidence/decay-data.json. Soma de ramos Na22=99,996% e médias de energia não completamente coerentes são preservadas; não modificar fonte para impor conservação. DECAIMENTOS.md especifica a contabilidade separada.
- F81: Kondev et al., [NUBASE2020](https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf), Chinese Physics C45,030001(2021), DOI10.1088/1674-1137/abddae; [tabela original](https://www-nds.iaea.org/amdc/ame2020/nubase_4.mas20.txt). Seção2.3: ano tropical365,2422d/31556926s, larguras parciais e meia-vida/vida média distintas. Mantido como comparação explícita da bancada ENSDF: n609,8s versus613,9s e ramos Na22 diferentes, sem mistura silenciosa de versões.

F82 · NAIF SAT459 (SAT441/SAT441xl para699), BSP/merge/comentários/checksum oficiais. https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat459.mrg . Recorte699 por CSPICE spksub, sem refit; original/MD5/SHA e segmentos preservados em evidence/saturn-*.json. DE442s continua autoridade do centro6 e corpos anteriores.
F83 · NASA3D Resources Saturn: https://science.nasa.gov/3d-resources/saturn/ . A página classifica o mapa como ficcional, gerado JPL/Caltech. JPEG local não representa nuvens observadas ou evolução atmosférica.

F84 · OpenSpace0.22 fixado: assets/scene/solarsystem/planets/saturn/globe.asset, RingsComponent e shaders advanced_rings_fs/globe. Manifesto saturn_textures/v4 obtido em https://liu-se.bigbang.openspaceproject.com/request?identifier=saturn_textures&file_version=4&application_version=1 ; URLs/bytes/SHA preservados. Perfil visual, sem origem observacional/época confirmadas.

F85 · NAIF [oscelt](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/oscelt_c.html)
e REBOUND [elementos orbitais](https://rebound.readthedocs.io/en/latest/orbitalelements/):
cônicas osculadoras, parâmetros relativos e singularidades. Conferência
independente em orbital-diagnostics-check.json; referências de dois corpos
não garantem escape/captura em N-corpos.

F86 · Stephen L. W. McMillan e Piet Hut, *Binary–single-star scattering VI.
Automatic Determination of Interaction Cross Sections* (1996),
[arXiv astro-ph/9604015](https://arxiv.org/abs/astro-ph/9604015).
Referência conceitual de encontros, troca e ejeção. Os números iniciais do
catálogo Cosmos2 são modelos próprios selecionados por integração local,
sem atribuí-los ao artigo ou a observações. Comparação DOP853/IAS15 em
gravity-experiment-candidates-check.json; domínio em ENCONTROS.md.

F87 · Microsoft, [status dos dados de contadoresPDH](https://learn.microsoft.com/en-us/windows/win32/perfctrs/checking-pdh-interface-return-values)
e [Get-Counter](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-counter).
Consulta14/10/2026. Sucesso da consulta e validade de cada amostra são distintos;
não usar valores de dados inválidos. Coletor preserva path/status/erro e recusa
qualquer erro/inválido, sem preencher zero ou descartar silenciosamente.
Contrato sintético e leitura real em gpu-collector-error-contract-check.json.
