# Testes das quatro forças, com explicações e exemplos

Pedido em 22/10/2026, execução em 23/10 UTC. **As 14 verificações científicas
reexecutadas passaram.** Isso valida os recortes abaixo; a integração geral
Sol–Terra–Lua–Júpiter ainda precisa ser construída e testada.

Recibo: [four-forces-recheck-20261023.json](evidence/four-forces-recheck-20261023.json).
Exemplos calculados: [four-force-examples-20261023.json](evidence/four-force-examples-20261023.json).
Plano: [PLANO-INTEGRACAO-SISTEMA-SOLAR.md](PLANO-INTEGRACAO-SISTEMA-SOLAR.md).

## O que foi realmente verificado

Python Windows do projeto, NumPy 2.5.4, SciPy 1.18.1, REBOUND 5.2.2,
SpiceyPy 8.2.0 e pynucastro 3.1.0. As fontes executadas foram arquivadas,
os recibos anteriores foram copiados antes da reexecução e o ponteiro da
sessão do dono permaneceu idêntico. Os 14 grupos são: forces, em-readings,
fusion, decays, cno, force-persistence, science-contracts, nuclei,
nuclear-energies, igrf, dipole, gravity-probe, atlas e atlas-import.

| Interação | Resultado e interpretação | Limite do aceite |
| --- | --- | --- |
| Gravidade | Campo radial em sete direções 3D, lei 1/r², órbita e limite balístico. Sonda versus −gradiente do potencial: diferença relativa ≤1,88×10⁻¹⁰. Cópia Sol/Terra/Lua por 24 h versus DOP853 independente: diferença máxima de componente de posição 0,244 mm. | O acordo entre integradores vale para o mesmo modelo newtoniano reduzido. Não mede o erro frente ao Sistema Solar real nem inclui Júpiter. |
| Eletromagnetismo | Lorentz com sinais de carga e E/B independentes: erro de posição ≤2,54×10⁻¹¹ em unidades de raio de Larmor. Trabalho elétrico: resíduo relativo ≤1,33×10⁻¹⁵; força magnética sem trabalho. IGRF14: 58 casos contra o Fortran BGS, diferença por componente ≤0,01455 nT. | Campos prescritos, partícula clássica e instrumento geomagnético. Esses resultados não aprovam MHD, tempestades solares ou integração geral com os corpos. |
| Forte/processos nucleares mistos | AME2020: 3.558 estados; Q/limiares por massas e referência NNDC. Sete taxas de reação versus pynucastro: diferença relativa ≤7,07×10⁻¹⁴; composição versus ODE independente ≤1,06×10⁻¹² da densidade inicial; 66 combinações de canais e 48 casos de limite. | Modelos efetivos/tabelas de núcleos e misturas diretas. Não é solução de QCD; energia Q não determina a probabilidade de reação nem sua taxa. |
| Fraca | Dez pais/19 ramos beta−, beta+ e captura eletrônica. Lei exponencial: erro ≤1,12×10⁻¹⁶ da população inicial; rede versus Radau ≤1,43×10⁻¹²; Sr→Y→Zr versus Bateman ≤6,67×10⁻¹⁶. Passaram 102 combinações de canais e 40 limites. | Populações médias e ambiente atômico de referência. Não é previsão de espectros completos, transporte de neutrinos ou taxas de captura no plasma solar. |

Fusão, decaimentos e CNO também verificam composição, contagem de eventos e
balanços. CNO-I conserva bárions e catalisadores no recorte; o refinamento da
composição ficou em 5,99×10⁻¹⁵. pp-I/CNO-I mantêm temperatura e densidade
prescritas; não validam evolução completa de uma estrela.

As 16 combinações iniciais de atuação/visualização e os contratos de
persistência passaram. São provas dos controles e da ciência dessas bancadas.
Esta rodada não refez as jornadas CEF nem os benchmarks gráficos; as
evidências nativas anteriores conservam suas gerações e limites próprios.

## Gravidade: Terra, Lua e a diferença entre atração e maré

Usando GM da referência DE442 já fixada no projeto e a distância ilustrativa
Terra–Lua de 384.400 km, a aceleração causada pela Terra na Lua é
**0,00269756 m/s²**. Para uma sonda isolada ao dobro dessa distância, cai a
um quarto: é o teste da lei do inverso do quadrado. Acima, abaixo e dos lados,
o vetor aponta para a fonte; esconder os vetores não deve alterar a trajetória.

No centro terrestre, usando 1 au e aquela distância lunar, a atração solar é
aproximadamente **0,00593008 m/s²**, e a lunar **0,0000331801 m/s²**.
Mesmo assim, a amplitude linear da maré solar é cerca de **0,459** da lunar:
a maré depende da variação espacial do campo, proporcional a GM/r³ no limite
de corpo pequeno. Essas distâncias são exemplos escolhidos, não uma consulta
da geometria real em uma época específica.

**Teste integrado proposto:** mostrar contribuições do Sol, Terra, Lua e
Júpiter; comparar ramos com a contribuição de Júpiter atuante e suprimida,
mantendo as mesmas condições iniciais. A maré será medida como diferença
entre aceleração local e central. Prever altura da água numa costa exige
resposta oceânica e geografia adicionais, conforme a
[explicação da NOAA](https://www.nesdis.noaa.gov/about/k-12-education/oceans-coasts/what-causes-tides).

## Eletromagnetismo: uma carga no campo próximo de um planeta

Em um exemplo **uniforme** de B=50 µT, um próton com velocidade perpendicular
de 100 km/s descreve um círculo de raio **20,88 m** e período **1,312 ms**:
r=m·v⊥/(|q|·B). Com velocidade paralela adicional, a trajetória é helicoidal.
Esse B foi escolhido para o exemplo; não é um valor IGRF consultado em uma
posição terrestre. A bancada testada separadamente usa seus próprios parâmetros.

O campo magnético muda a direção da velocidade; a potência q(v×B)·v é zero.
Um campo elétrico pode alterar a energia cinética. Trocar o sinal da carga
inverte o sentido da deflexão. Os testes confrontam essas trajetórias com
uma integração independente, além de conferir o balanço de trabalho.

**Teste integrado proposto:** selecionar Terra ou Júpiter, consultar B na
sonda e propagar cargas nos campos adotados e na gravidade. Para um corpo
neutro no modelo pontual, não aplicar a força de Lorentz como se todo planeta
tivesse a carga de um próton. A Lua tem campos locais, sem o mesmo dipolo
global terrestre, como descreve a [NASA](https://science.nasa.gov/moon/solar-wind/).

## Forte: ligação nuclear, energia e fusão

Na reação **D + T → He-4 + n**, as massas avaliadas adotadas resultam em
**Q=17,589299865 MeV**. O teste calcula Q por caminhos independentes e compara
com a referência NNDC. Depois, testes distintos confrontam as taxas e a
quantidade de reagentes/produtos com outra biblioteca e uma ODE independente.
São perguntas diferentes: liberar energia não significa reagir rapidamente.

A ligação nuclear está associada à interação forte residual, enquanto a
aproximação de dois núcleos carregados enfrenta a barreira eletrostática.
Logo, uma reação pode depender de mais de uma interação. Tabelas de massa
e taxas são modelos avaliados, com fontes e domínios, e não uma simulação
de todos os quarks/glúons. Referência das avaliações:
[AMDC/IAEA, AME2020 e NUBASE2020](https://www-nds.iaea.org/amdc/).

**No Sol:** a demonstração D+T é uma bancada didática; não representa a
principal cadeia solar. A integração deve abrir a zona pp-I/CNO-I ligada ao
Sol e mostrar canais, composição, energia e neutrinos do modelo declarado.

## Fraca: meia-vida e neutrinos

Para uma amostra com **1.000 núcleos de carbono-14**, o backend executado
produziu as populações médias esperadas:

| Tempo | C-14 restante | Antineutrinos eletrônicos produzidos |
| --- | --- | --- |
| Inicial | 1.000 | 0 |
| 1 meia-vida | 500 | 500 |
| 2 meias-vidas | 250 | 750 |
| 4 meias-vidas | 62,5 | 937,5 |

O canal é C-14→N-14+e⁻+antineutrino. A lei é N(t)=N₀·2^(−t/T½).
Uma população média fracionária é válida nesse modelo estatístico; uma amostra
individual tem contagens inteiras aleatórias. No mesmo exemplo, ocultar a
camada preservou exatamente a saída; desligar atuação manteve o pai intacto.

Há uma diferença de fontes que precisa continuar visível: a bancada inicial
usa 609,8 s para a meia-vida do nêutron, fixada em NUBASE2020; o laboratório
estendido usa 613,9 s da entrada ENSDF adotada e conserva a comparação.
Os testes passam com cada fonte declarada. Isso não torna os dois números
iguais nem prova que qualquer um seja a melhor avaliação experimental atual.
Não substituir silenciosamente dados para forçar concordância.

**No Sol**, o primeiro canal pp, p+p→D+e⁺+νe, depende da interação fraca.
A ligação/reação nuclear e a barreira EM também entram no processo. O
[DOE descreve esse papel da interação fraca](https://www.energy.gov/science/np/articles/proton-proton-fusion-powering-sun).
Suprimir um canal no modelo registra uma intervenção hipotética; não significa
desligar uma constante fundamental de forma autoconsistente. Também não se
deve apagar instantaneamente a luz solar: geração, transporte e reservatório
térmico precisam ser distinguidos. Nem toda radioatividade é fraca; emissão
alfa e decaimentos beta exigem classificações próprias.

## Pendências de integração e retomada

Um exemplo adicional já foi preparado com os quatro centros na mesma época,
11/10/2026 12hUTC. Na condição inicial candidata, as magnitudes das
contribuições sobre a Terra são: Sol0,00594947m/s²,
Lua0,0000320906m/s² e Júpiter0,000000168811m/s². A soma física é vetorial;
não se somam essas magnitudes como se as direções fossem iguais. A fixture
`output/solar-integration-staging/four-body-initial-si.json` guarda vetores,
estados e procedência. É um exemplo inicial calculado; ainda não comprova
a propagação conjunta nem a interface integrada.

A prioridade agora está descrita em sete fatias no plano: cadastro/estados
dos quatro corpos, gravidade conjunta, campos de cada corpo, partículas e
ambiente solar, processos do núcleo e jornada completa. As camadas e a malha
relativística continuam obrigatórias nos marcos correspondentes.

A candidata visual J continua parcial. O potencial A e a nuvem A foram
recusados nos critérios vigentes. A repetição potencial B terminou incompleta
antes da segunda rota por falta de confirmação do cenário nativo no coletor
GPU. Não há captura formal em andamento e não foi demonstrada a causa exata.
Essas pendências de desempenho/integração permanecem separadas dos 14 grupos
científicos aprovados nesta rodada.
