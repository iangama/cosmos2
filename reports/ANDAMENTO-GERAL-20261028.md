# Cosmos2 — andamento geral em 28/10/2026

A v1 tem 21 marcos: **7 aceitos localmente, 10 parciais e 4 planejados**.
Outras seis etapas são propostas de expansão. Essa contagem não mede percentual
de esforço, código ou qualidade total. Aceite local não é aprovação estética
do dono nem aceite da versão final.

O seletor normal confirmou a variante cloud da base 3.13, com hashes aprovados
do motor e aplicação. As candidatas mais recentes chegam a 0.14.0, sem promoção
sobre a base instalada. A análise leu planos, decisões, relatórios e seis
recibos recentes; não reexecutou suítes científicas nem benchmarks antigos.

| Marco | Frente | Estado | O que já existe | Falta para fechar | Disponibilidade |
|---|---|---|---|---|---|
| C2-00 | Base técnica e motor | Aceito localmente | Build Windows/OpenSpace, interface, worker, modo offline e prova G0 na RX7600. | Recorte-base aceito; novos recursos exigem regressões próprias. | Instalado |
| C2-01 | Dados, unidades e procedência | Aceito localmente | IDs, SI, épocas/referenciais, fontes verificáveis e cópia Atlas → experimento. | Ampliar cobertura nos marcos de conteúdo e integração. | Instalado |
| C2-02 | Navegação e interface | Aceito localmente | Busca, seleção, câmeras, viagens canceláveis, favoritos, tempo e interface 100–150%. | Expansão do catálogo e jornadas gerais pertencem aos marcos seguintes. | Instalado |
| C2-03 | Qualidade visual inicial | Aceito localmente | Terra, Lua e Saturno; atmosfera, iluminação, anéis e sombras no recorte aprovado. | Relevo contínuo e demais mundos continuam em C2-05/16. | Instalado |
| C2-04 | Atlas entre escalas | Parcial | Catálogo estelar, Via Láctea volumétrica e navegação inicial. | Completar viagens entre sistemas/galáxias, catálogo progressivo e retorno coerente. | Base inicial instalada |
| C2-05 | Superfícies e geração procedural | Planejado | Há mapas/texturas e geometrias de referência; não equivalem a terreno contínuo. | Lua/Marte, quatro famílias rochosas, 20 sementes e transição de superfícies. | Planejado |
| C2-06 | Editor gravitacional | Aceito localmente | Criar/remover/editar 1–128 massas; estados SI, órbitas, conservação e encontros. | Recorte aceito; colisões e instrumentos avançados têm marcos próprios. | Instalado |
| C2-07 | Colisões, spin e energia | Planejado | Raio geométrico e spin cinemático no editor. | Contato contínuo, fusão de corpos, torques, calor e balanços dinâmicos. | Planejado |
| C2-08 | Histórico e recuperação integrada | Parcial | Checkpoints, ramos, exportação e retomada, inclusive em novos workers. | Unificar histórico/comparação/portabilidade entre todos os modelos e jornadas. | Instalado + candidatas |
| C2-09 | Desempenho e pacote base | Parcial | Executável local, inicialização, modo offline e perfis próprios de vários recortes. | Pacote integrado, instalação limpa e regressão de todos os recursos em conjunto. | Instalado + perfis de candidatas |
| C2-10 | Entrega intermediária | Planejado | Protótipo local executável já existe. | Fechar dependências, empacotar e aceitar formalmente a entrega C2-10. | Sem aceite deste marco |
| C2-11 | Instrumentos e gravidade avançada | Parcial | Sondas, campo/maré, cortes, J2 e ressonâncias; ensaios de 256 massas e 10 mil partículas. | Consolidar o conjunto, ampliar instrumentos/jornadas e fechar o aceite do marco. | Base 3.13 instalada; marco aberto |
| C2-12 | Laboratório eletromagnético | Parcial | E/B, Lorentz, editor de fontes/cargas, linhas, sondas e persistência em recortes. | Fechar integração e aceites conjuntos; perfis isolados não encerram o marco. | Bancadas + candidatas isoladas |
| C2-13 | Magnetismo planetário | Parcial | IGRF14 na Terra, JRM33 em Júpiter; vetores, linhas/mapas e partículas-teste. | Expandir corpos e ambientes externos; concluir as jornadas planetárias integradas. | Bancadas + candidatas IS-3/4 |
| C2-14 | Relatividade em campo fraco | Parcial | Bancadas de relógios, luz/geodésicas e referências de curvatura. | Precessão, lentes/observador e a malha espaço-temporal solicitada. | Bancadas; integração pendente |
| C2-15 | Buracos negros e luz | Parcial | Experimentos limitados de luz no modelo Schwarzschild. | Kerr, spin/arrasto, observador e imagem relativística calculada/validada. | Bancada parcial |
| C2-16 | Acervo e observatório | Parcial | Acervo nuclear/estelar inicial, mundos de referência e bancadas científicas. | 12 mundos em destaque, 30 sistemas exoplanetários, 30 objetos profundos e 32 experiências completas. | Conteúdo inicial instalado |
| C2-17 | Integração e candidata final v1 | Planejado | Componentes e diversos recortes possuem evidências próprias. | Jornadas J1–J15, quatro forças/camadas, saves, pacote offline e aceite conjunto. | Versão final não entregue |
| C2-18 | Núcleos e interação forte | Aceito localmente | AME2020: 3.558 estados; carta nuclear, ligação, Q/limiares e fusão manipulável. | Recorte aceito; evolução estelar e aprofundamento quântico têm outras etapas. | Instalado |
| C2-19 | Decaimentos e interação fraca | Aceito localmente | Dez pais/19 canais avaliados, beta−/beta+/captura e cadeia Sr90 → Y90 → Zr90. | Recorte aceito; espectros/transporte/oscilação avançados seguem C2-22. | Instalado |
| C2-20 | Quatro forças e região estelar | Parcial | Candidata 0.14.0: pp-I/II/III efetivo + CNO-I/II, 16 espécies/18 canais e resposta térmica ideal. | EOS Coulomb/screening; depois estrutura/transporte/hidrostática/luminosidade e integração completa. | Foco atual · candidata não promovida |
| C2-21 | Matéria quântica | Expansão proposta | Escopo de aprofundamento definido. | Hidrogênio quântico, espectros, barreira/tunelamento e modelo nuclear reduzido. | Expansão após a v1 |
| C2-22 | Neutrinos e fraca avançada | Expansão proposta | Produção e energias de neutrinos já aparecem em recortes anteriores. | Espectros beta e oscilação de três sabores nos regimes contratados. | Expansão após a v1 |
| C2-23 | Plasma coletivo | Expansão proposta | Há partículas-teste e vento solar prescrito em candidatas; não são plasma coletivo. | PIC eletrostático 1D, modos coletivos e produtos MHD identificados. | Expansão após a v1 |
| C2-24 | Dinâmica galáctica | Expansão proposta | Via Láctea visual disponível como ponto de partida. | Potenciais disco/bojo/halo, órbitas, curvas de rotação e comparação de hipóteses. | Expansão após a v1 |
| C2-25 | Cosmologia e universo observado | Expansão proposta | Planejamento e referências registrados. | FLRW, distâncias/redshift, produtos CMB e teia cósmica identificados e validados. | Expansão após a v1 |
| C2-26 | Integração científica ampliada | Expansão proposta | Integração posterior planejada; nenhum aceite próprio. | Unir C2-21–25, mais 24 experiências e 56 no total, com pacote e jornadas próprios. | Expansão após a v1 |

O avanço recente na integração do Sistema Solar foi:

| Frente | Resultado registrado | Limite atual |
|---|---|---|
| IS-1/2 | Sol/Terra/Lua/Júpiter, estados e gravidade conjunta; referências e perfil próprios | Recorte reduzido; não é todo o Sistema Solar nem aceite da v1 |
| IS-3 | IGRF/JRM33, orientação, vetores, linhas, mapas/cortes e persistência | Campos e amostras nos domínios declarados; integração total pendente |
| IS-4 | Cargas-teste 0.8.1 e vento Parker 0.9.0/0.9.1, com perfis e revisão visual | Cenário prescrito; não resolve MHD/magnetosfera/plasma coletivo |
| IS-5 | Rede estelar 0.14.0 e resposta térmica; referências solares B23 auditadas | EOS ideal, densidade/volume fixos; estrutura, transporte e luminosidade pendentes |
| IS-6 | Percurso completo e expansão definidos | Ainda sem aceite conjunto |

A candidata CNO-II possui recibos de ciência, worker, interface, imagem e perfil
aprovados. Seu perfil próprio de quatro janelas registrou p95 máximo 13,917 ms,
p99 máximo 14,405 ms e zero quadros acima de 100 ms; RAM 1,208 GiB / GPU 2,990 GiB.
São resultados dessa cena/UI/IPC, não throughput do solver ou desempenho de
qualquer combinação do produto. O pico de 401 ms da primeira coleta pp-III continua
registrado como falha, sem causa estabelecida; a coleta B passou.

Próximo passo técnico registrado: contrato de EOS Coulomb/screening a partir
de energia livre e derivadas termodinâmicas, antes de alterar solver/modelo.
Comparações com B23 encontraram pressão ideal acima das referências em cerca
de 1,74–2,28% no recorte avaliado; isso não identifica uma causa única.

Minha avaliação: a base gravitacional/nuclear e a validação por recortes
avançaram bastante. O maior risco de produto é acumular candidatas sem fechar
uma experiência integrada instalada. Também faltam superfícies, colisões,
expansão do conteúdo e a malha relativística solicitada. O próximo bloco deve
preservar o rigor do contrato científico e reservar integração/consolidação
para que os recursos aceitos cheguem à versão normalmente iniciada.

A meta continua 12/11/2026: 15 dias de calendário a partir desta análise. Com 14
marcos da v1 ainda sem aceite completo, não há base medida para garantir todo
o escopo nessa data. As antigas previsões em horas/meses foram retiradas e
não foram usadas aqui; não se alterou o prazo silenciosamente.

Fontes principais: ROADMAP-GERAL.md; PLANO-UM-MES.md;
PLANO-INTEGRACAO-SISTEMA-SOLAR.md; CAMADAS-QUATRO-FORCAS.md;
as sete decisões locais; IS-3-MAPAS-LOTES-RESULTADO-20261024.md;
IS-4-PARTICULAS-RESULTADO-20261025.md; IS-4-VENTO-SOLAR-RESULTADO-20261026.md;
IS-5-CNO-II-RESULTADO-20261027.md; IS-5-REFERENCIAS-SOLARES-RESULTADO-20261027.md.
