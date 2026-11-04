# Cosmos2

Novo projeto de explorador e laboratório do universo para PC, inspirado em
SpaceEngine, Universe Sandbox, OpenSpace e Celestia.

**Estado em 04/11/2026: sete marcos com aceite local; construção em continuidade.**
A candidata isolada0.20.1 passou em persistência, reinício e perfil próprio,
com quatro janelas,240comandos e nenhum quadro acima de100ms. A importação
composta na0.21.1 passou nos testes CPU e nas jornadas funcionais nativas
Terra/Júpiter. A revisão visual W passou com16capturas nativas e as quatro
visibilidades por corpo. A comparação direta dos pixels corrigiu uma
interpretação anterior sobre o PrintWindow: os arquivos conservavam a interface.
O perfil próprio0.21.1 e os saves apenas espaciais continuam pendentes. Veja os
[resultados K4](IS-6-COEXISTENCIA-PERSISTENCIA-K4-RESULTADO-20261104B.md)
e [K5](IS-6-COEXISTENCIA-MIGRACAO-K5-RESULTADO-20261104.md).
Palavras de retomada: **cosmos2** ou **cosmos 2**. O Cosmos original permanece separado.

A revisão 3.0 incorpora o pedido de instrumentos científicos, gravidade
avançada, eletromagnetismo, magnetismo planetário, relatividade e maior riqueza
visual e de conteúdo. A revisão 3.0 inclui forte/fraca como prioridade inicial
e controles separados de atuação/visualização. Já existe uma bancada de
doze palcos delimitados; o restante do escopo segue em construção.

Comece pelo [plano de um mês](PLANO-UM-MES.md): meta,telemetria e orçamento
semanal real, substituindo estimativas anteriores de prazo não calibradas.
O [roteiro geral](ROADMAP-GERAL.md) preserva estado,27marcos, entregas,
dependências e ciclos de esforço. A v1 mantém21marcos; seis etapas posteriores
aprofundam matéria quântica, neutrinos, plasma, galáxias e cosmologia.
O [plano diretor](PLANO-DIRETOR.md) detalha a experiência/arquitetura da v1.
C2-10 é intermediária; C2-17 é candidata v1, não fim das expansões.

| Documento | Conteúdo |
| --- | --- |
| [Plano de um mês](PLANO-UM-MES.md) | Meta12/11/2026, capacidade semanal e entregas por bloco; revisão4.1 |
| [Roteiro geral](ROADMAP-GERAL.md) | Etapas completas, estado, horas restantes e ciclos de5h; revisão4.0 |
| [Pesquisa](PESQUISA-REFERENCIAS.md) | Quatro referências, alternativas técnicas e recomendação condicionada |
| [Experiência](EXPERIENCIA.md) | Interface, navegação, direção visual e quinze percursos de uso |
| [Quatro forças](QUATRO-FORCAS.md) | Prioridade atual, palcos, atuação e visualização independentes |
| [Escopo científico](ESCOPO-CIENTIFICO.md) | Interações, instrumentos, modelos, metas de conteúdo e fontes da ampliação |
| [Arquitetura](ARQUITETURA.md) | Escalas, tempo, dados, física, geração e salvamento |
| [Validação](VALIDACAO.md) | Critérios de ciência, imagem, desempenho e instalação |
| [Fontes](FONTES.md) | Referências oficiais e científicas, incluindo a ampliação |
| [Retomada](LEIA-PRIMEIRO.md) | Estado atual, limites e próximo passo |

Já há um protótipo Windows executável sobre build próprio OpenSpace0.22:
interface própria, Terra/Lua com texturas locais, atmosfera e panorama celeste.
Sol/Terra/Lua usam JPL DE442s; Saturno699 usa SAT441 + DE442s por época, com controle UTC de1950–2050
e exportação de estados/fontes; iluminação e rotações IAU gerais declaradas.
Abra **Iniciar-Cosmos2.cmd**. Arraste para orbitar e use a roda para aproximar.
F1 alterna a interface; F12 captura a cena.

O modo Experimentos já oferece P32/P128, pausa, alteração de massa central
e salvamento/retomada, com REBOUND em processo separado. O Atlas inclui
catálogo estelar e Via Láctea volumétrica baseada em modelo NAOJ. Veja [a captura real](evidence/cosmos2-atmosphere.png) e
[o resultado da integração](evidence/renderer-worker-check.json).

C2-00/G0 passou naRX7600: abertura útil14,9s nesta coleta com cache do aplicativo
novo; nove percursos1080p74–75FPS, sem pausas>100ms; soma dedicada por processo
2,99GiB e residente1,00GiB, com compartilhamento declarado. Consulte
[a decisão e seus limites](G0-DECISAO.md). Demais marcos permanecem em construção.

O botão **Forças fundamentais** abre a bancada na mesma janela: gravidade 3D,
fontes binárias com sondas de potencial/maré, Lorentz em campos uniformes,
dipolo3D com espelhamento, gravidade independente e curvasB/pitch/energia,
campo terrestre IGRF14 por posição/altitude/época, globo e mapa de componentes,
fusãoD+T/ligaçãoAME2020, seis misturas/sete canais com composição e energia,
quatro decaimentos iniciais NUBASE e nova bancada ENSDF com dezpais/19ramos,
beta−/beta+/EC, alimentação Sr90→Y90→Zr90 e contagem de leptões/energia;
redespp-I/CNO-I
com canais e neutrinos, e geodésicas/relógiosSchwarzschild.
Use os controles Atuação/Referência e de efeitos, selecione condições e
compare resultados. Salvar/retomar registra condições e geração científica,
indicando mudanças de modelo, dados ou versões; exportação inclui
modelo, unidades e dados. São modelos limitados e identificados; ainda faltam
evolução térmica/hidrostática, transporte, magnetosfera, Kerr e integração geral das
experiências. Os modelos e seus limites ficam identificados na bancada.

O Atlas copia Sol/Terra/Lua para um experimento pausado, com IDs ramificados,
GM/época/fontes e vetores originais preservados no checkpoint. As vistas do
sistema e Terra–Lua têm rótulos. **Dados e fontes** consulta sete propriedades
por corpo e quatorze pacotes locais/73arquivos, verifica SHA256 e exportaJSON real
emuser/exports. O acervo nuclear mostra3558estadosAME2020, cartaN×Z e curvaB/A,
comparação/incertezas/estimativas. Veja [o aceite localC2-01](C2-01-DECISAO.md)
e seus limites. O [aceite C2-18](C2-18-DECISAO.md) inclui acervo, Q/limiares e
fusão; o [aceite C2-19](C2-19-DECISAO.md) cobre os decaimentos avaliados.
O [aceite C2-02](C2-02-DECISAO.md) cobre busca/tipo/proximidade, árvore, seleção na cena, viagens canceláveis, câmera livre/órbita/seguimento, favoritos com época e interface100–150%. Selecione um objeto e use **Visitar**; G visita, F segue, Espaço pausa e Esc cancela. Digitar nos campos preserva a câmera. O [aceite C2-03](C2-03-DECISAO.md) inclui anéis/sombras de Saturno, vistas geral/terminador/polo/órbita próxima, exposição e céu didático. Os mapas são fixos; origem e limites ficam na ficha. C2-06 também tem aceite local; demais marcos seguem em construção.

O editor gravitacional já cria e remove corpos (1–128 massas ativas), edita
massa/posição/velocidade em SI e conserva IDs estáveis. Em **Corpos · criar,
editar ou remover**, escolha a operação e use **Pausar e preparar**. Raio e
spin ficam em **Raio e rotação**: são geometria e orientação cinemática, sem
colisões, torques ou energia interna. O tamanho pode mostrar marcadores
ampliados ou os raios físicos definidos.

**Órbita e escape** compara a cônica instantânea atual com os campos preparados,
sem aplicá-los; as curvas ficam fixas no instante calculado. **Conservação e
baricentro** mostra massa, energia e momentos; intervenções externas ficam no
histórico. **Sonda pontual · g e potencial** mede o campo em uma posição SI,
com tempo/revisão/referencial; sua leitura ainda não é salva.

**Experiências prontas** oferece encontro hiperbólico, captura por troca de
companheiro e ejeção de um terceiro corpo. São condições locais de modelo,
sem fonte observacional. Carregue pausado, escolha o ritmo e inicie. Há pausa
única no horizonte recomendado e continuação depois dele. Salvar/retomar
preserva as condições originais, o estado e os balanços. Captura/escape são
classificações do intervalo medido, sem garantia de estabilidade eterna.

O [aceite local C2-06](C2-06-DECISAO.md) inclui ciência, cinco jornadas,
revisão visual e perfis formais P128/G0 do motor final. Campo volumétrico e
instrumentos avançados seguem em C2-11; colisões/energia interna em C2-07.

**C2-11 parcial, geração3.6:** em **Sondas salvas · campo e maré**, crie pontos
fixos ou seguindo corpos por ID e exporte g, Φ e tensor. Em **Campo 3D e cortes
equipotenciais**, prepare centro/escala, desloque/gire o corte e meça. A cena
mostra setas omnidirecionais e curvas equipotenciais; cor de |g| usa linear/log,
com legenda SI. Leituras são congeladas e marcadas quando o estado muda.
Definições e configuração ficam no checkpoint; medições completas saem em JSON.
Jornadas científicas/nativas passaram; dois perfis do mapaP128 não passaram
as portas de desempenho e seguem em diagnóstico.
Comparações/séries, ramos, J2/marés/ressonâncias e perfis256/10mil continuam
pendentes, sem aceite completo deste marco.

Perfil fresco c211fields3 aprovado/auditado:128massasativas+569amostrascongeladas,
p95<=22,264ms/p99<=27,325ms/zero>100ms/20pausas<=51,786ms. RAMsoma1,55343GiB/
GPUWDDMsoma2,45255GiB/DXGI7,19014GiB. Releituras sob pedido<=1662,380ms fora
das janelas formais. Recibo/sourcearchive próprios e backup3.6validado.
C2-11 parcial; candidatos de comparação/histórico3.7 ainda fora do produto.
