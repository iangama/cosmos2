# Arquitetura proposta — Cosmos2

Arquitetura alvo, revisada em 12/10/2026. Há protótipo parcial com OpenSpace,
REBOUND e interface própria; C2-00 aprovou localmente a base. A sequência e
o aprofundamento por regimes estão emROADMAP-GERAL.md revisão4.0.
Este documento não descreve tudo como já implementado. Dados e experimentos
devem sobreviver à troca da base visual.

## 1. Componentes e responsabilidades

| Componente proposto | Responsabilidade | Limite |
| --- | --- | --- |
| Aplicação Cosmos2 | Estado, seleção, comandos, preferências e histórico | Não resolver gravidade no ciclo de desenho |
| Adaptador visual C++ | Representações, câmera, luz e seleção | Coordenadas reduzidas da GPU não são fonte científica |
| Interface local | Busca, painéis, tempo, editor e ajuda PT-BR | Não executar código recebido em catálogos |
| Serviço de Atlas | Catálogos, efemérides, geração e metadados | Não modificar fontes observadas durante uma experiência |
| Worker de simulação | Estado físico, passos, eventos, checkpoints e precisão | Independente de FPS e uploads de textura |
| Gerente de conteúdo | Manifestos, índice, obtenção, cache e cancelamento | Não apagar sessões ao liberar cache |
| Persistência | Escrita atômica, versões, recuperação e exportação | Compatibilidade declarada por esquema |

A interface candidata usa as tecnologias presentes no OpenSpace WebGui,
em bundle local associado à release. A renderização e o worker continuam
nativos e o uso principal é offline. C2-00 deve comprovar o controle da
aplicação pela API e CEF; substituir a interface envolve estado, entrada,
acessibilidade e comandos, além de aparência.
[Manifesto oficial](https://github.com/OpenSpace/OpenSpace-WebGui/blob/master/package.json).

## 2. Ferramentas e organização futura

Adotar o padrão C++ e toolchain da release escolhida do OpenSpace. Fixar CMake,
compilador, submódulos, CEF e interface como um conjunto. Não combinar manual
`latest`, código de uma release antiga e interface `master`. Python pode
auxiliar preparação de dados e testes; não será requisito instalado pelo
usuário final.

Estrutura conceitual, a criar somente na implementação:

```text
app/                 interface e comandos do produto
modules/cosmos2/     integração com a base visual
core/                IDs, unidades, tempo, contratos e histórico
workers/gravity/     processo físico independente
content/manifests/   fontes, licenças, limites e hashes
content/profiles/    conteúdo básico e opcional
tools/               preparação reproduzível de conteúdo
tests/               ciência, contratos e percursos
packaging/           pacote Windows e inventário de terceiros
evidence/            medições e capturas relevantes
```

Fixar a base upstream e manter uma lista pequena de alterações. Preferir
extensões por módulo. APIs internas do OpenSpace não são tratadas como
contrato estável entre versões; o adaptador Cosmos2 concentra esse risco.

## 3. Identidade e procedência

Todo objeto tem ID persistente com namespace. Exemplos conceituais:
`sol:naif:399`, `star:gaia-dr3:<source_id>`, `proc:<versao>:<semente>:<caminho>`
e `exp:<uuid>:<id>`. Nomes e traduções não são chaves. IDs grandes chegam à
interface JavaScript como strings para preservar todos os dígitos.

Uma propriedade pode conter valor, unidade, incerteza, época, referencial,
origem e status: observado/catalogado, calculado por modelo, procedural ou
desconhecido. Um exoplaneta pode ter período medido, massa inferida e textura
gerada; um único selo global “real” não basta.

Separar objeto de referência, estado físico e representação. O primeiro
guarda parâmetros/fontes daquela versão; o segundo guarda posições,
velocidades, massas, raios, spin, modelo e tempo; o terceiro guarda materiais,
detalhe e rótulos. Aumentar um marcador não altera o raio de colisão.

Exportações incluem versão do motor, parâmetros, seed, hashes de entradas,
unidades, modelo e cobertura temporal.

## 4. Coordenadas e escalas

Hierarquia: universo representado → galáxia → região estelar → sistema → corpo
→ posição local. Transformações têm referencial e época. Metros em um único
vetor absoluto, mesmo double, não preservam detalhe de superfície nas maiores
distâncias.

Proposta: posições locais float64 no domínio; âncoras hierárquicas e IDs de
regiões para grandes distâncias; diferenças relativas ao observador antes
de converter para GPU. Em viagens longas, mudar a âncora preservando posição
e orientação relativas. A compatibilidade dessa abordagem com o renderer
upstream precisa ser provada em C2-00.

Ao seguir a Lua, a câmera opera numa referência próxima; ao ver a Via Láctea,
numa referência galáctica. Calcular diferenças no ancestral comum adequado,
sem somar detalhes pequenos a um número cósmico para depois subtrair. O estado
do experimento permanece no próprio referencial inercial.

Precisão de posição, profundidade, transparência e iluminação são problemas
distintos. Avaliar o tratamento de profundidade já usado pela base antes de
introduzir reversed-Z ou buffer logarítmico. Testar anéis, eclipses, terreno
e partículas simultaneamente.

Rotação axial e câmera não modificam o referencial do solver. Conversões na
borda SPICE explicitam km→m, km/s→m/s e eixos. Convenções de quaternions,
handedness e matrizes entram nos contratos e testes.

## 5. Tempo

| Relógio | Função |
| --- | --- |
| Tempo do Atlas | Consultar fontes/efemérides na faixa de cobertura |
| Tempo do experimento | Último estado integrado confirmado pelo worker |
| Tempo monotônico de execução | Agendamento, latência e orçamento |
| Tempo apresentado na imagem | Interpolação permitida entre estados, sem criar eventos científicos |

Guardar época e escala temporal. UTC serve à apresentação; consultas usam a
escala exigida pela fonte, como TDB. Conversões usam bibliotecas e tabelas de
segundos intercalares, sem uma subtração constante informal. Alvo solar:
1950–2050 para corpos cujos kernels escolhidos cubram a faixa; não é cobertura
já confirmada. Cada corpo declara o próprio intervalo.

Retroceder no Atlas consulta estados anteriores. Num experimento com colisões,
usa checkpoint e reprodução de eventos, sem passo negativo para “desfazer”
dissipação. Um ajuste no passado cria outra ramificação. A interface mostra
onde termina o histórico disponível.

## 6. Do Atlas ao experimento

1. Congelar a época e escolher corpos, incluindo o corpo central necessário.
   Mostrar quais influências ficam excluídas.
2. Obter posições e velocidades geométricas no mesmo tempo/referencial.
   Dados insuficientes exigem uma hipótese explícita ou recusam o preset
   científico; não inventar uma velocidade observada.
3. Criar outro ID e transformar para o referencial inercial do experimento,
   preservando origem e transformação inversa.
4. Fixar convenção de massa/GM, G, unidades e constantes. Não combinar massas
   arredondadas e parâmetros gravitacionais inconsistentes silenciosamente.
5. Enviar ao worker e receber primeiro estado confirmado antes de executar.
   Guardar a referência inicial para comparação.

Um sistema reduzido declara perturbadores, marés e correções excluídos. O
fundo galáctico desenhado não exerce força sem um potencial externo escolhido
explicitamente em modelo futuro. Cada objeto tem um só provedor de movimento.

## 7. Worker, integradores e atualização

REBOUND é candidato por ter núcleo C e métodos gravitacionais especializados.
Avaliar IAS15 para poucos corpos e encontros; WHFast para sistemas hierárquicos
bem separados no regime apropriado. Física de corpos rígidos do renderer não
substitui integração orbital.
[Integradores](https://rebound.hanno-rein.de/integrators/).

No Windows, preferir canal herdado ou named pipe restrito ao usuário. Protocolo
versionado, comandos pequenos e snapshots completos. JSON atende a primeira
prova de 32/128 corpos; layout binário ou memória compartilhada só se a medição
justificar. Não abrir servidor público.

Comando: `request_id`, `experiment_id`, revisão esperada, operação e parâmetros
tipados. Resposta: aceito/recusado e revisão resultante. IDs tornam reenvio
idempotente. Operações: carregar, pausar, continuar, alterar, inserir/remover,
avançar, checkpoint e encerrar.

Snapshot: sequência, revisão, tempo, estado por ID, eventos e diagnóstico.
A aplicação apresenta apenas pacotes completos da revisão atual. Uma fila
limitada pode substituir quadros intermediários atrasados; comandos e eventos
físicos não são descartados. Interpolar só entre estados compatíveis, nunca
atravessando colisão, inserção ou mudança de parâmetro.

O worker tem orçamento por lote e atende cancelamento entre lotes. Quando a
taxa pedida exceder a capacidade, avança mais devagar e informa a taxa efetiva;
não relaxa precisão para acompanhar FPS. Integradores bloqueantes precisam
de pontos de interrupção ou integração subdividida, a verificar na prova.

Edições pausam num estado confirmado, registram evento e invalidam previsões
posteriores. Trocar integrador preserva o estado físico e reconstrói dados
internos. Determinismo exato depende de ambiente/configuração; entre plataformas,
validar tolerâncias, sem prometer igualdade bit a bit de floats.

Alterar massa, velocidade, inserir ou remover um corpo pode fornecer/retirar
energia e momento do sistema. Registrar esse efeito como intervenção externa
e iniciar uma nova referência de conservação; não apresentar o salto causado
pelo usuário como erro numérico. Desfazer restaura o estado anterior à
intervenção e não tenta compensá-la com uma força fictícia.

No editor inicial, massas e raios são positivos e finitos; vetores e tempo
devem ser finitos. Gravidade nula pode existir como preset balístico explícito.
Valores fora do domínio do solver são recusados com indicação do campo.
Massa, raio e densidade não são três parâmetros independentes: a interface
permite escolher qual dos dois primeiros manter e calcula o terceiro. Registrar
a política no evento de edição, inclusive ao reabrir o experimento.

## 8. Colisões, calor e efeitos

Primeiro modelo: esferas com contato detectado ao longo do avanço, refinando
o passo para evitar atravessamento de corpos pequenos. Fusão preserva massa
e momento linear. Momento angular vai para spin ou para uma conta explícita
do modelo, nunca é perdido sem diagnóstico.

Para densidades constantes e soma de volumes, propor
`Rnovo³ = R1³ + R2³`. Compressão e vaporização ficam fora desse modelo. O balanço
energético inclui mudanças de energia cinética, potencial gravitacional e o
reservatório interno adotado. Fragmentos e luz de efeito não criam massa física
nova. A v1 não promete SPH nem crateras hidrodinâmicas.

Para uma esfera isotérmica simples, temperatura de equilíbrio opcional:
`Teq = [L(1-A)/(16πσεr²)]^(1/4)`, com luminosidade L, albedo A, emissividade ε
e distância r. Não é clima observado nem inclui automaticamente efeito estufa.
Reservatório térmico de impacto é outro modelo, com capacidade térmica e
resfriamento declarados. Só ligar modelos de materiais após validação própria.

## 9. Renderização e carregamento

Pacotes visuais derivados contêm posição relativa, orientação, raio, material,
luminosidade, ID selecionável e procedência. Um universo procedural extenso
não requer materializar todos os objetos.

Estrelas usam índice espacial e descarte por visibilidade. Pontos e
representações simplificadas conservam IDs. Galáxias podem ter volumes e
componentes estatísticos. Uma imagem 2D de nebulosa não passa a ser observação
3D por ser colocada no espaço.

Terrenos usam patches hierárquicos compatíveis com a base, erro projetado na
tela, transição de detalhe, união de bordas e carregamento próximo à câmera.
Um nível básico fica residente. Pedidos obsoletos são cancelados; uploads têm
orçamento por quadro. Arquivo ausente conserva o nível anterior e informa
carregamento, sem bloquear os controles.

Avaliar atmosfera, anéis, luz e exposição juntos. Reusar primeiro o modelo
da base; Bruneton é referência se uma lacuna concreta exigir extensão. HDR
interno pode produzir saída SDR em monitor comum. Modo fotográfico não altera
dados físicos.
[Referência atmosférica](https://ebruneton.github.io/precomputed_atmospheric_scattering/).

## 10. Geração procedural

Resultado depende de versão do gerador, seed e caminho estável do objeto.
Usar PRNG especificado e seeds independentes da ordem de acesso; visitar um
planeta antes de outro não muda o sistema. Não depender de hash instável da
linguagem nem de sorteio por frame.

Gerar região → sistema → estrela(s) → órbitas → corpos → materiais → terreno.
Impor restrições do modelo, como ausência de sobreposição inicial, órbitas
declaradas e classes térmicas coerentes. Isso não comprova estabilidade por
bilhões de anos: o sistema informa seu status de validação dinâmica.

Catálogos prevalecem nos objetos identificados. Procedural é uma camada
explícita, sem preencher lacunas de observação como se fossem descobertas.
A v1 limita região, famílias e sistemas ativos. Sementes de referência cobrem
rochoso sem atmosfera, rochoso com atmosfera simples e gigante gasoso visual.
Terreno navegável é obrigatório na família rochosa inicial.

## 11. Fontes e pacotes

| Conteúdo | Fonte candidata | Restrição proposta |
| --- | --- | --- |
| Solar | SPICE; Horizons para verificação | Recorte temporal, centros/referenciais e termos fixados |
| Estrelas | Recorte Gaia DR3 e associação conferida de nomes | Seleção documentada; sem catálogo completo |
| Exoplanetas | NASA Exoplanet Archive | Consulta, data, referências e campos desconhecidos preservados |
| Lua | NASA SVS CGI Moon Kit | Resolução apropriada e créditos por asset |
| Demais mapas | Pacotes públicos do perfil escolhido | Termo por pacote; sem licença uniforme presumida |
| Galáxias | Conjunto curado e modelos próprios | Separar parâmetros medidos de distribuição ilustrativa |

Fontes: [SPICE](https://naif.jpl.nasa.gov/naif/aboutspice.html),
[Horizons](https://ssd.jpl.nasa.gov/horizons/manual.html),
[Gaia](https://www.cosmos.esa.int/web/gaia/data-release-3),
[TAP](https://exoplanetarchive.ipac.caltech.edu/docs/API_resources.html),
[Lua](https://svs.gsfc.nasa.gov/4720/).

Distâncias estelares exigem critério de qualidade: não inverter qualquer
paralaxe, inclusive negativa ou com grande incerteza. Começar com recorte
conservador; estimativas probabilísticas futuras preservam método e incerteza.
Velocidade radial ausente não é zero conhecido. Extrapolações de movimento
próprio ficam limitadas ao intervalo aceito.

Manifesto: ID, versão, fontes, consulta, créditos, termos, unidades,
referenciais, época, cobertura, arquivos, tamanhos e hashes. Obtenção grava
temporário, confere integridade e promove atomicamente. SQLite é candidato
para nomes/metadados; dados de desenho ficam separados por região.

Pacotes importados são dados. Scripts Lua da base pertencem à instalação
confiável; importações do usuário não são executadas automaticamente. Um
futuro importador de Celestia começa por subconjunto declarativo documentado,
sem prometer compatibilidade com qualquer complemento.

## 12. Sessões, falhas e exportação

Sessão guarda câmera com âncora, modo, tempo, seleção, camadas, versões do
conteúdo e referências aos experimentos. Experimento guarda estado inicial,
eventos e checkpoints. Escrita atômica preserva a última cópia íntegra.

Usar IDs/hashes de pacotes e caminhos relativos para portabilidade. Conteúdo
ausente é informado; não substituir por outra versão silenciosamente. Arquivo
futuro incompatível é recusado sem sobrescrever.

Se o worker cair, o Atlas permanece navegável, o experimento para e oferece
o último checkpoint íntegro. Falha de catálogo não bloqueia os demais. Cache
visual é reconstruível. Falta de disco cancela a operação atual preservando
a sessão anterior.

CSV exporta os corpos/época escolhidos com unidades e IDs, independentemente
do detalhe gráfico. Imagens têm legenda opcional e manifesto associado.
Uma imagem não substitui o estado necessário para repetir o experimento.

## 13. Campos, instrumentos e solvers especializados — plano 2.0

Preparar contratos em C2-01, sem implementar todos os solvers antecipadamente.
O laboratório atual de gravidade continua uma primeira implementação. Novos
modelos têm capacidades explícitas e processo/orçamento próprios quando isso
isolará custos ou falhas. O renderer não passa a ser autoridade científica.

| Contrato | Dados necessários |
| --- | --- |
| Modelo | ID/versão, equações, parâmetros, domínio, unidades, referências, capacidades e acoplamentos permitidos |
| Campo | Tipo g/potencial/gradiente/E/B/métrica, região/referencial, tempo, revisão, método e resolução da amostragem |
| Sonda | ID, posição/âncora ou trajetória, grandezas, unidades, amostragem, tempo confirmado e incerteza/erro quando conhecido |
| Diagnóstico | Energia/momentos, trabalho externo, erro estimado, taxa efetiva, validade e idade dos dados |
| Observador relativístico | Evento, quadrivelocidade/base local, métrica, coordenadas e convenção de tempo |
| Checkpoint | Estado do solver, escalonamento dos passos, revisão, campos, sondas, observador, eventos e hashes |

Não misturar a escala visual atual de posições com uma definição física de
unidades. Fixar L0, M0 e T0 coerentes para gravidade canônica, com
T0=sqrt(L0³/(Gfísico M0)) quando Gcanônico=1. Campos EM inicialmente usam SI
no worker; conversões e carga em coulombs são explícitas na borda. Não somar
teslas ou V/m diretamente a vetores adimensionais do REBOUND.

Campo amostrado por corte/linhas pode usar cache por modelo, revisão, tempo,
região e precisão. Sondas quantitativas consultam o avaliador científico.
Cancelar pedidos obsoletos; leitura anterior fica marcada até chegar nova
medição. Interpolação gráfica não atravessa mudança de parâmetros nem permite
registrar um estado interpolado como observação calculada pelo solver.

Campos prescritos, Coulomb mútuo e métricas fixas são modos diferentes. Um
registro de acoplamentos declara fontes, receptores, reação e troca de energia.
No começo, impedir combinações não validadas por capacidade do modelo. Não
aplicar simultaneamente órbita newtoniana e geodésica à mesma partícula.
Dados do Atlas seguem como referência; uma edição cria ramificação.

Cada solver tem relógio/condição de avanço apropriados. Boris pode guardar
velocidade em meio passo; checkpoint e saída devem representar essa convenção
corretamente. Parâmetro afim de um raio nulo não é o tempo próprio de uma
partícula massiva. Integração lenta não bloqueia câmera, pausa ou histórico.

Comparação usa a mesma entrada e amostra resultados em instantes/referenciais
compatíveis; não exige que integradores tenham os mesmos passos internos.
Cada novo modelo traz salvamento mínimo antes de entrar no fluxo principal.
Em C2-17, empacotar dependências escolhidas e validar todo o ciclo offline.

## 14. Semântica das quatro forças

QUATRO-FORCAS.md prevalece sobre adiamentos antigos. Contrato separado para
fontes/modelo, atuação por operador/processo e visualização de referência.
Trocar visualização não invalida estado físico nem altera taxa; trocar atuação
cria revisão/intervenção. Configuração exportada preserva todos os controles.
O cálculo de referência usa as fontes intactas, mesmo se o operador não atua.
Um experimento com interação suprimida é identificado como contrafactual.

Núcleos exigem redes/estados quânticos e dados avaliados, não vetores clássicos
de longo alcance inventados. Taxas mistas declaram dependências. Supressão
de um processo com matéria fixa não significa recalcular constantes da teoria
fundamental. Caso fora do domínio deve ser recusado ou modelado explicitamente.

Primeira bancada usa POST /api/forces/evaluate, operações limitadas e respostas
com hash de configuração; /save e /load preservam escolhas atomicamente em
user/forces. Ciência em app/forces.py, sem autoridade científica no canvas.
A visualização 3D usa projeção de vetores e trajetórias calculados pelo backend.
A bancada não passa a controlar os corpos do Atlas ou o worker P32 implicitamente.

### Fatia C2-01 implementada em12/10

app/science_contracts.py define dez IDs/versões de modelo e contratos de
exportação: unidade por grandeza, referencial, tempo decorrido ou parâmetro
afim, amostragem e proveniência de código/dados SHA256. A resposta conserva
configuration_sha256 para todas as escolhas e acrescenta physics_sha256
para entradas/modelo/operadores científicos; visibilidade não muda este último.
O módulo congela hashes no import: alterações científicas exigem reiniciar o
backend como geração única. UI não é autoridade para constantes ou forças.
Os contratos identificam incertezas de fonte não propagadas separadamente
dos resíduos numéricos. Em Schwarzschild, as posições cartesianas são uma
apresentação do raio areal, sem declarar distância espacial euclidiana.

Laboratório canônico: data/science/canonical-units.json fixa L0=1e9m,
GM0solar nominalIAU2015, T0=sqrt(L0³/GM0)=2745.011593s e M0=GM0/G.
G CODATA2022 tem incerteza padrão1.5e-15; a massa nominal expressa emkg
herda essa incerteza, ao contrário deGM0que é conversão nominal definida.
Snapshots/checkpoints registram physical_scale; UI apresenta horas, ritmoh/s
e massa nominal. O offsetLabRoot é de exibição, não coordenada astronômica.
Binding explícito incompatível é recusado; checkpoint canônico antigo permanece
compatível com a conversão padrão declarada. Nenhum timestep/corpo foi alterado.

Isso não encerra C2-01: contrato solar inicial TDB/efemérides e IDs está abaixo;
IDs de catálogo completos, pacotes gerais ou observadores gerais pendentes. Campos
binários e redes são modelos limitados; não há acoplamento tácito entre eles.

### Dipolo prescrito e gravidade:12/10

app/dipole.py soma operadoresNewton/Lorentz numa partícula clássica3D. Campo
dipolar e GM permanecem prescritos ao suprimir atuação. DOP853 integra giro
completo; espelhamento emerge da trajetória, sem aplicar força adiabática
adicional. μ é diagnóstico aproximado; v_parallel refere-se aoBcompleto mesmo
quando a atuação está desligada. Uma mudança de sinal isolada não classifica
espelhamento. Limites1/10R encerram o modelo, sem produtos de colisão.

241estados exportados para sondas/curvas; traçado tem amostragem local por
frequência nos extremos/meio de cada intervalo do solver, margem5%, alvo20
amostras/ciclo, <=12.001pontos. Inclui todos os instantes de medição e ocanvas
corta por tempo físico, não por proporção da contagem irregular. Referência
completa tem sua própria duração; não sincronizar falsamente trajetórias que
terminam em fronteiras diferentes. Fonte esféricaR=6371km é escolha do modelo;
GMnominalIAU2015 e B/eixo definidos, sem época terrestre/IGRF. Contrato declara
unidades próprias paraB/g/forças/potência/energia/pitch e limites.

### Instrumento IGRF14: 13/10

app/geomagnetism.py sintetiza o campo interno com coeficientes IAGA fixados,
referencial terrestre ECEF e componentes geodéticas N/E/baixo. Época decimal
explícita 1900–2030, sem herdar Atlas; raio harmônico 6371,2km, elipsoide WGS84.
Grau 1 é truncamento dos mesmos coeficientes, sem usar o dipolo ideal anterior.
Mapa/globo e projeção em geomagnetism.js só apresentam dados calculados.
O contrato spatial_snapshot inclui 703 pontos mais a sonda, sem time_s fictício.
Força clássica local qv×B depende do operador EM; coeficientes, fonte terrestre
e referência persistem ao suprimi-lo. Não há MHD, tempestade ou órbita integrada.
Hash do dataset e código/versões/época/unidades são exportados; campo externo
e detalhes locais omitidos e incertezas não propagadas permanecem explícitos.

### Condições e geração científica persistidas:13/10

Esquema3 em user/forces/latest.json grava scientific_generation, ID/versão de
modelo, hashes congelados de código/dados e versõesPython/NumPy/SciPy. Hash
individual da configuração é preservado; hashes da geração e do envelope
detectam alteração também nos metadados. Gravação atômica continua vigente.
APIload responde restoration: same_generation/changed_generation/
unknown_generation, com diferenças por arquivo ou ferramenta. Esquema1/2
verifica o hash original antes de migrar e não inventa procedência passada.
Retomada usa código atual para recalcular; correspondência de versões declaradas
não garante igualdade de bits em outra máquina/BLAS. Não é checkpoint dinâmico.
UI comunica a geração após recalcular e recusa envelope corrompido.

### Atlas solar JPL:13/10

app/atlas.py calcula estados geométricos DE442s: IDs sol:naif:10/399/301,
SSB0, J2000/ICRF, NONE, posiçõesm/velocidadesm/s. LSKnaif0012 converteUTC↔ET/TDB,
preservando leap2016. Aplicação1950–2050; spkcov confirma faixa de cada corpo.
Rotações IAU geraisPCK00011 não são ITRF/orientação lunar de alta precisão.
Proveniência de kernels/código/assets e runtime congelada ao inicializar.

Raiz do renderer éGALACTIC, exigida também pelas sombrasatmosféricas upstream.
Contrato exporta matrizJ2000→GALACTIC e position_render_m; autoridade científica
continuaJ2000. Matrizporlinhas/vetorescoluna, aliascena distinto doIDNAIF. Câmera
Lua exigeReferenceFrame; perfilJSON exigeframe. Tests conferem composição das
rotações e posições emcincoépocas, além do ângulo real Sol−câmera. Mudança de
época valida/calcule antes de mutar, aplica no próximo frame e só confirma após
et/posições/pausa corresponderem. ClockAtlas não altera solverREBOUND ou forças.
Serviço aguarda marcador de cena antes de conectarWS, sem fila durantestartup.

### Contratos solares, pacotes e cópia —13/10

C2-01 aprovado localmente emC2-01-DECISAO.md. atlas_properties.py separa
21propriedades de três corpos; observer identifica estado geométricoSSB/NONE,
sem emissão/recepção calculadas. packages.py verifica dezpacotes/34arquivos
contra manifestos fixados, com última leitura e alcance do cache explícitos.
Cópia atlas_import.py preserva propriedades/fontes/UTC-TDB/GM/matrizes eIDsexp;
checkpoint esquema2 sela envelope ebinário, compara geração do integrador,
valida transformação eescala. ArtefatosJSON são locais/atômicos pelo helper
artifacts.py. Contratos prévios ATLAS-EXPERIMENTO ePACOTES-PROPRIEDADES contêm
critérios/resultados. O observador aparente e o gerenciador geral de instalação
continuam nas etapas posteriores; não transformar contratos em alegação de
acervo completo ou física unificada.
