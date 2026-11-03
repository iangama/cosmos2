# Cosmos2 — quatro forças, cenários e controles científicos

Atualização do pedido de22/10/2026: testes com exemplos e integração dos
corpos principais em um plano geral. Consultar
[relatório da reexecução de14grupos](RELATORIO-TESTES-FORCAS-20261023.md) e
[plano Sol/Terra/Lua/Júpiter](PLANO-INTEGRACAO-SISTEMA-SOLAR.md).
Todos passaram nos recortes declarados; integração geral continua pendente.

Revisão 3.0, 12/10/2026. Este requisito do dono substitui a decisão 2.0 de
adiar forte/fraca. As quatro interações e suas consequências são prioridade
inicial. O exemplo do Sol aplica-se ao sistema de controles inteiro.

## 1. Escopo obrigatório

Pedido adicional de18/10/2026: malha espaço-temporal com controle próprio e
camadas equivalentes de investigação para todas as forças, incluindo campos
EM dos corpos com modelos/dados disponíveis. Requisito obrigatório da v1,
distribuído por etapa e com aceite em [CAMADAS-QUATRO-FORCAS.md](CAMADAS-QUATRO-FORCAS.md).

Gravidade: campo vetorial 3D, potencial, marés e relatividade conforme regime.
Eletromagnetismo: campos E/B, partículas, radiação e respostas da matéria.
Forte: ligação nuclear e reações entre núcleos com dados avaliados; distinguir
interação residual nuclear de QCD entre quarks/glúons.
Fraca: decaimentos beta, captura eletrônica, transformação de espécies,
neutrinos e contribuição às cadeias estelares.

Cada uma precisa de cenário interativo, medição, alteração de parâmetros,
comparação, persistência e evidência de precisão. Nenhuma fica apenas numa
ficha informativa ou numa animação. Modelos efetivos são identificados com
domínio/erro; não alegar resolver QCD ou teoria quântica de campos completa.

## 2. Controles independentes para todas

Cada interação possui **Atuação física** e **Visualização de referência**.
Os controles de efeitos específicos aparecem dentro de cada cenário:
trajetórias, luz/relógios, aceleração de cargas, canais nucleares, decaimentos,
energia depositada e neutrinos, conforme capacidades reais do modelo.
Ocultar nunca muda a física. Desligar atuação preserva massa/carga/estado,
remove a contribuição selecionada e registra intervenção/ramificação.
Visualização ligada continua calculada das fontes e identificada como
referência se a atuação correspondente estiver desligada.

| Atuação | Visualização | Resultado |
| --- | --- | --- |
| ligada | ligada | Evolução e campo/processo visíveis |
| ligada | desligada | Mesma evolução, sem a camada visual |
| desligada | ligada | Evolução sem a contribuição; referência física mantida e identificada |
| desligada | desligada | Contribuição suprimida e camada escondida |

Os dois botões não significam modificar livremente constantes fundamentais.
Suprimir operadores/canais mantendo a matéria é um experimento hipotético;
é possível calculá-lo no modelo declarado, mas ele não é um universo alternativo
fisicamente autoconsistente. Desligar forte de verdade alteraria os próprios
hádrons/núcleos; desligar EM afetaria matéria e taxas. Não manter tabelas do
nosso universo e chamar esse resultado de nova teoria validada.
Canais mistos declaram todas as dependências; não rotular toda fusão como forte.

## 3. Gravidade omnidirecional e espaço-tempo

A vista principal é um volume 3D explorável com amostras do campo, sondas e
superfícies equipotenciais; vetores apontam nas direções calculadas em cada
posição. Em torno de fonte esférica isolada, o campo é radial em todas as
direções. Várias fontes, rotação e multipolos quebram essa simetria.
Não usar uma folha elástica 2D como representação principal.

O campo newtoniano não é a métrica do espaço-tempo. O modo relativístico
mostra grandezas do modelo escolhido: geodésicas, marés e relógios locais,
com observador e coordenadas definidos. Espaço-tempo 4D é inspecionado por
cortes/observadores 3D; não existe uma malha material universal observável.

Exemplo obrigatório: campo do Sol visível, ação orbital desligada, sondas
continuam lendo campo de referência e corpo-teste segue trajetória balística.
Gravidade ligada/campo oculto reproduz a órbita anterior. Não apagar o Sol,
não zerar sua massa, não congelar o corpo para simular ausência de força.
Em relatividade, manter métrica curva e desligar seu efeito nas geodésicas
é uma comparação hipotética, não solução das mesmas equações de Einstein.

## 4. Palcos científicos

| Palco | Interações e leituras |
| --- | --- |
| Região orbital 3D | Gravidade/EM, vetores, trajetórias e força total nos regimes compatíveis |
| Ambiente planetário | Gravidade, campo magnético, partículas e processos radiativos suportados |
| Núcleo/plasma termonuclear | Reações, taxas, barreira eletrostática, energia de ligação/Q e composição |
| Decaimento beta | Meia-vida, população, produtos, carga/número bariônico e neutrinos |
| Região estelar | Rede pp/CNO, energia nuclear, perdas por neutrinos e resposta térmica com escalas explícitas |
| Campo relativístico | Espaço-tempo, observadores, raios, marés e comparação Newton/GR |

Modelos de núcleo/estrela preservam a distinção entre fonte de energia,
transporte de fótons, reservatório térmico e luminosidade da superfície.
Desligar uma reação não apaga instantaneamente a luz do Sol. Um modelo de
zona com T/densidade prescritas não prevê sozinho a resposta estrutural solar.

## 5. Primeira entrega implementável

Uma bancada de forças na interface local, com os quatro controles, cálculo
no backend e gráficos/volume 3D ligados aos resultados. Começar por gravidade
radial, Lorentz em campos uniformes, fusão D+T por taxa REACLIB e decaimento
beta por meia-vida avaliada. Comparar tudo ligado e processos suprimidos.
Esses são casos iniciais executáveis; não equivalem ao aceite de toda a física.

A seguir: ligação/espalhamento nuclear e rede pp/CNO, captura eletrônica e
neutrinos, gravidade/EM acopladas nos perfis compatíveis e geodésicas com
relógios. A prioridade é provar cada força e os controles antes de expandir
o acervo. C2-00 permanece aberto; testes de modelo podem avançar sobre o runtime
oficial enquanto o linker próprio é corrigido, sem aprovar G0 antecipadamente.

## 6. Validação e fontes

Implementado até12/10: a bancada tem efeitos separados E/B, ligação nuclear
AME2020 e fusão D+T; decaimentos n/³H/¹⁴C e captura eletrônica de⁷Be; rede
pp-I com três canais, composição, neutrinos e energia. A captura usa a
meia-vida do estado de referência, não a taxa de um plasma totalmente ionizado.
Na zona estelar, T/densidade são prescritas, não evoluídas; deposição assume
retenção local da energia exceto neutrinos, com média solar pp fixa deBahcall.
EM suprime o canal radiativo D+p; a barreira embutida nas taxas fica fixa.
Faltam pp-II/III, extensões CNO, transporte, resposta térmica/hidrostática e luminosidade,
além de GR com rotação/imagem completa, outras fontes/grupos de campo e ligação/espalhamento completos.

Gravidade: simetria 3D, superposição, órbita e limite balístico; EM: hélice,
trabalho elétrico, energia magnética e carga com sinal. Forte: taxa contra
biblioteca independente, estequiometria, energia Q e convergência/solução
analítica no caso reduzido. Fraca: meia-vida, lei exponencial, ramificações,
carga e número bariônico; energia dos neutrinos só onde houver dados/modelo.

Testar as quatro combinações dos botões por interação. A camada escondida
não altera resultado. Atuação desligada não altera leitura de referência.
Edições ficam no histórico; salvar/restaurar preserva escolhas e unidades.
As incertezas das fontes não são o erro numérico do integrador.

Fontes primárias consultadas em 12/10/2026:
- [CERN: Modelo Padrão](https://home.cern/science/physics/standard-model/).
- [DOE: fusão próton–próton](https://www.energy.gov/science/np/articles/proton-proton-fusion-powering-sun).
- [pynucastro: tipos de taxas](https://pynucastro.github.io/pynucastro/rate_types.html).
- [JINA REACLIB](https://reaclib.jinaweb.org/index.php).
- [IAEA: API de dados nucleares](https://www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html).

### Geodésicas e relógios: fatia implementada12/10

app/relativity.py resolve raios nulos Schwarzschild exteriores (DOP853),
impacto no infinito, escape/captura e relógios estáticos. Massa define rₛ;
sondas em cascas3D medem ritmo e escalar de Kretschmann. Referência permanece
ao desligar desvio ou relógios; suprimir curvatura é hipótese contrafactual.
Integração termina em1.001rₛ ou limites declarados; faixa crítica10⁻⁸ não
recebe destino falso. Parâmetro afim é identificado, sem chamar tempo próprio
da luz. Não há Kerr/disco/imagem de buraco negro nesta fatia.
Quadratura independente passou (erro máximo7.45e-10rad), limite fraco,
conservação e oito combinações; Edge verificou sonda/captura/enquadramento.
Fonte primária: Carroll, seção7, gr-qc/9712019. Evidências:relativity-check.json
e relativity-ui-check.json. Aceite dos marcos GR ainda pendente.

### CNO-I e instrumentos de rede: fatia implementada12/10

app/cno.py resolve seis canais/oito espécies em zona prescrita com Radau:
¹²C(p,γ)¹³N, beta+¹³N,¹³C(p,γ)¹⁴N,¹⁴N(p,γ)¹⁵O, beta+¹⁵O e¹⁵N(p,α)¹²C.
Cada canal tem gate próprio; capturas radiativas exigem forte+EM, beta exige
fraca. Barreiras eletrostáticas/estrutura inicial ficam fixas nesta hipótese.
T10–30MK, densidade1e4–3e5kg/m³; catalisador inicialC12/N14. Não é hotCNO,
CNO-II/III, evolução estelar ou previsão de luminosidade.

REACLIB fixa as taxas; por padrão beta+ usa NUBASE2020 (N13=597.9s,
O15=122.266s). Há comparação explícita com o fitwc12 legado, sem substituir
uma avaliação silenciosamente. Q atômico soma26.7304MeV/ciclo; médias de
neutrino solares fixas .706/.996MeV, BahcallTabelaI. Energia nãoν retida
localmente é hipótese, não transporte radiativo. Fontes/recortes/hashes em
data/science/cno1.json e evidence/cno-data.json; incertezas ausentes declaradas.

Interface pp/CNO alterna composição e rede, com taxa por instante, Q de
referência e sondas de fração mássica/densidade por núcleo. A disposição dos
nós é um diagrama de reações, sem posições nucleares inventadas. O usuário
seleciona oito curvasCNO; vista e seleção não alteram a física. Visibilidade
da referência e supressão de canais continuam independentes.

verify-cno.py passou comparação com taxas/derivadas upstream, meias-vidas
analíticas, seis canaisoff, oito combinações globais, cantos do domínio,
refinamento e balanços de bárions/catalisadores/carga+positrons/energia.
UI Edge e CEF nativo passaram probes/canais/vistas. Evidências cno-check,
cno-ui-check,networks-ui-check,native-networks-check; nenhum aceite geral de
estrela completa ou marco científico foi atribuído por esses testes.

### Fontes binárias e marés: fatia implementada12/10

app/binary_gravity.py integra o problema circular restrito espacial. Fontes
em órbita circular prescrita e partícula sem retroação; superposiçãoNewton,
potencial zero no infinito e tensor de gradiente de aceleração. Casca3D de
96sondas mais sonda posicionável; L1–L5 do modelo completo como referência.
Controle próprio de atração por fonte, além de atuação/referência globais.
Fontes e campo completo permanecem ao suprimir termos. A vista girante inclui
Coriolis/centrífuga de coordenadas; a inercial mostra movimento balístico
quando ambas atrações são desligadas. Isso não é um binário que se desfaz
fisicamente ao desligar sua gravidade mútua: sua efeméride permanece prescrita.

Posição/velocidade3D, massas/separação/duração e sonda são editáveis. L4/L5
podem definir o estado inicial; estabilidade linear é indicada. Enquadramento
e referencial alteram somente a vista. Fronteira0,02a encerra o modelo sem
afirmar captura, colisão ou raio material; nunca suaviza uma singularidade
silenciosamente. DomínioNewton, sem GR, deformação material ou efeméridesreais.

Comparação independente com REBOUND inercial: erro máximo3.81e-14a no caso
congelado. DerivaJacobi1.87e-15, potencial/gradiente de maré conferidos por
diferenças finitas, traço de maré no vácuo~1e-16, cinco equilíbrios e quatro
combinações de fontes. UI e CEF nativo passaram sondas/controles. Evidências
binary-gravity-check,binary-ui-check,native-binary-check. Não é aceite geral
de três corpos, de colisões ou de um marco completo.

### Instrumentos eletromagnéticos:12/10

Campo uniforme agora tem camadasE/B/ambos com unidades próprias nas sondas;
mostrar a referência continua independente de suprimir aceleração/desvio.
Medição da partícula por instante apresenta velocidade, forças elétricas e
magnéticas separadas, potência, energia cinética e trabalho elétrico.
O backend calcula qE, q(v×B) e F·v; a UI consulta esses dados na linha do tempo.
Oito combinações de carga/gates conferiram forças e balançoK−K0−trabalho
até1.32e-15rel; potência magnética nula na tolerância. UI Edge passou unidades,
sonda temporal e vistas sem alterar física. CEF nativo verificado separadamente.
Isto não acrescenta dipolo/IGRF, campos autogerados ou transporte de plasma.

## Nono palco — dipolo3D com gravidade independente

Próton/antipróton em Bdipolar ideal estático e gravidade esférica, com atuação
e campos de referência independentes. Espelhamento decorre da integração
Lorentz completa; μ é diagnósticoadiabático. SondasB/g/forças/pitch/energia,
24linhas analíticas, esfera física e5curvas. Modelo delimitado1–10R, semIGRF/
plasma/atmosfera. DesligarB preserva campo/fonte e leva à trajetória calculada
comNewton (ou reta se ambosoff). v_parallel relativo à referência não basta
para classificar espelhamento no contrafactual. Evidênciasdipole-check/UI/
native-dipole passaram e imagens nativas finais revistas. ContratoC2-01incluído;
C2-12/13/20não completos. Próximo campo terrestre real exigeIGRF14fixado.

## Décimo palco — campo terrestre IGRF14

Instrumento por latitude, longitude, altitude WGS84 e época decimal 1900–2030.
Globo/vetores3D, mapa X/Y/Z/H/F/D/I e comparação com grau 1 do mesmo IGRF.
Força magnética instantânea em próton/antipróton clássico com velocidade local
prescrita; atuação/efeito/visibilidade independentes, campo/fontes preservados.
Não inventa trajetória ou tempo e não equivale a magnetosfera/temporal externo.
Síntese própria conferida em58casos com FortranBGS original: errocomponentes
máximo0,01455nT. Resíduo entre implementações não é acurácia observacional.
IGRF.md registra contrato prévio, fontes, cobertura e reprodução. Dez contratos
científicos passaram; UI Edge passou mapa/sondas/controles. CEF é cheque separado.

## Reexecução de verificações em17/10/2026

Na versão atual, passaram novamente verify-forces, verify-em-readings,
verify-fusion, verify-decays, verify-cno, verify-force-persistence e
verify-science-contracts. O recibo evidence/four-forces-recheck-20261017.json
guarda hashes dos resultados e das fontes desta execução. Os recibos anteriores
foram preservados emoutput/four-forces-recheck-20261017. Esta reexecução é
numérica e de contratos/controles/persistência; não repete as jornadas CEF.
C2-18 e C2-19 mantêm seus aceites delimitados nas decisões próprias. EM geral,
acoplamento amplo e resposta estelar continuam parciais. Gravidade256 passou
perfil nativo próprio emc211p256q3; isso não é um perfil das quatro forças.
