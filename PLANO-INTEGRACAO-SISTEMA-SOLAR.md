# Integração do Sistema Solar e das quatro forças

Pedido do dono em 22/10/2026, registrado em 23/10 UTC. Complementa o roadmap
vigente e CAMADAS-QUATRO-FORCAS.md. Implementação local já autorizada.
Este plano organiza entregas existentes e pendentes; não declara integração pronta.

## Resultado que queremos ver

Uma cena navegável com Sol, Terra, Lua e Júpiter, evoluindo no mesmo cenário,
com seleção de corpo, contribuições das forças, sondas, exemplos explicados e
comparações salvas. Expandir depois para os oito planetas, luas principais e
os destaques previstos em C2-16. Selecionar a Terra deve permitir investigar
órbita, influência lunar e solar, campo magnético e partículas; selecionar o
Sol deve conectar gravidade, plasma, processos nucleares e emissão.

As quatro forças entram nas escalas em que o modelo as descreve. Gravidade
e EM possuem campos macroscópicos; forte e fraca entram nos processos da
matéria, reações e decaimentos. Não desenhar campos clássicos forte/fraco
entre planetas. Essa organização é uma decisão de arquitetura, coerente com
os alcances descritos pelo [CERN](https://home.cern/science/physics/standard-model).

## Estado constatado antes de implementar

- O Atlas em `app/atlas.py` expõe Sol, Terra, Lua e Saturno. Não expõe ainda
  Júpiter como corpo científico selecionável dessa API.
- A cópia dinâmica em `app/atlas_import.py` importa exatamente Sol/Terra/Lua,
  com estados geométricos JPL e evolução newtoniana própria. Saturno fica fora.
  Isso já é uma base de interação gravitacional, mas não o sistema solicitado.
- IGRF14 é um instrumento terrestre separado, com época própria e campo
  interno. A ligação ao corpo, relógio e referencial da cena continua pendente.
- Há bancadas de Lorentz, dipolo, fusão, decaimentos e zonas pp-I/CNO-I.
  Ainda não existe resposta térmica/hidrostática solar acoplada à cena.
- C2-12/J tem um perfil próprio aprovado de 128 partículas. Potencial A e
  nuvem A foram recusados; potencial B interrompeu por confirmação nativa
  insuficiente. Nenhum desses resultados aprova uma cena planetária conjunta.

## Corpos, camadas e limites

| Corpo/região | Gravidade | EM | Forte/fraca e ligação com a cena |
| --- | --- | --- | --- |
| Sol | Massa dinâmica; atração recíproca dos corpos; sondas e potencial | Modelo solar/plasma adotado explicitamente; radiação e vento com procedência própria | Zona pp-I/CNO-I existente; composição, energia e neutrinos. Transporte e resposta estrutural são entregas adicionais. |
| Terra | Órbita, reação à Lua/Sol/Júpiter; campo diferencial de maré | IGRF14 interno com rotação e época corretas; partículas-teste. Magnetosfera externa exige outro modelo | Amostras isotópicas identificadas; decaimentos beta/EC disponíveis. Inventário real e calor geológico exigem composição e canais adicionais. |
| Lua | Órbita sob Terra/Sol e perturbações; contribuição às marés terrestres | Sem dipolo global atual no modelo observado; campos crostais locais quando houver base adotada; ambiente externo separado | Amostras/constituição nuclear em bancada ligada ao corpo; sem assumir abundâncias não medidas. |
| Júpiter | Centro físico e GM compatíveis; sistema de luas separado do baricentro | Adotar e validar JRM33 para campo interno; correntes externas são componente adicional | Matéria/constituição nuclear; não apresentar fusão estelar sustentada como fonte atual de Júpiter. Modelo térmico exige contrato próprio. |
| Io, Europa, Ganimedes, Calisto | Subconjunto joviano e perturbações; marés com modelo declarado | Distinguir campo intrínseco de Ganimedes, indução e campo externo de Júpiter; plasma de Io é extensão própria | Processos da matéria onde houver dados; sem atribuir as mesmas capacidades a todas as luas. |
| Demais planetas/destaques | Expandir estados, GM, formas e cobertura verificadas | Registro individual: intrínseco, crostal, induzido, externo ou indisponível | Bancadas ligadas ao corpo e fontes por espécie; desconhecido permanece desconhecido. |

A NASA distingue o campo global terrestre dos campos localizados da
[Lua](https://science.nasa.gov/moon/solar-wind/). O artigo original de
[JRM33](https://doi.org/10.1029/2021JE007055) é a referência candidata para
Júpiter; sua adoção exige fixar coeficientes, convenções, grau, domínio e
permissões de redistribuição. IGRF descreve o
[campo principal terrestre](https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field),
não uma solução completa das tempestades geomagnéticas.

## Contrato comum de integração

Cada registro de corpo/camada deve guardar ID estável, centro/baricentro,
GM ou massa com origem, unidade SI, época UTC/TDB, referencial, orientação,
modelo/versão, hashes dos dados, cobertura temporal/espacial e incerteza
disponível. Separar observado, ajustado e sintético. Ausência de dados não é zero.

Manter dois percursos explícitos: **Atlas de referência**, consultado nas
efemérides, e **experimento dinâmico**, inicializado por cópia e evoluído pelas
equações escolhidas. Não atualizar posições do experimento com efemérides a
cada quadro. Alterações criam um ramo, preservando a referência original.
Usar estados geométricos simultâneos para dinâmica; tempo de viagem da luz
pertence à observação. Referência: [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/manual.html).

Júpiter exige atenção particular: DE442 fornece o **baricentro do sistema**
como NAIF 5. O planeta é NAIF 599. Não renomear 5 como centro físico 599,
nem somar a massa do sistema e depois acrescentar novamente as luas.
O kernel de satélites e os GMs precisam ser compatíveis. Ver
[conteúdo e parâmetros DE442](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442_tech-comments.txt).

As sondas e os desenhos consultam a mesma solução, identificando tempo e
revisão. Campo obsoleto é marcado como congelado. O relógio geral associa
épocas aos módulos; escalas nucleares e trajetórias de partículas usam
subpassos e aceleração declarados. Não fazer o núcleo envelhecer milhões de
anos porque o usuário avançou alguns dias orbitais sem escolher esse modo.

## Ordem de construção e critérios de passagem

| Fatia | Trabalho concreto | Evidência exigida antes de aceitar |
| --- | --- | --- |
| IS-0 — revisão e exemplos | Reexecutar ciência existente; explicar exemplos e lacunas; guardar o ponto de retomada | Recibos novos com fontes/geração preservadas e relatório didático. |
| IS-1 — cadastro e estados dos quatro corpos | Contrato do catálogo; Júpiter 599 com kernel/GM compatíveis; ampliar Atlas e cópia em candidata isolada | Fixtures independentes JPL, cinco épocas dentro da cobertura real comum, unidades/frames/rotação, centros e recusas sem mutação. Preservar o caminho legado de três corpos. |
| IS-2 — gravidade conjunta | Evolução recíproca Sol/Terra/Lua/Júpiter; painel por fonte; órbitas e sondas | Uma janela de 30 dias contra DOP853 independente; refinamento IAS15; energia/momento/angular e invariância por translação. Comparação JPL separada, com desvio de modelo reduzido declarado. |
| IS-3 — Terra/Lua e campos dos corpos | Campo diferencial de maré; IGRF ligado à Terra; JRM33 em candidata; domínio lunar explícito | Maré exata por diferença de acelerações e limite linear; rotações vetoriais e épocas; referências externas dos campos; controles sem alterar órbitas neutras indevidamente. |
| IS-4 — partículas e ambiente solar | Cargas-teste nos campos adotados; E/B e gravidade somados no regime declarado; cenário de vento solar identificado | Lorentz com sinal/carga e gravidade contra ODE independente; refinamento do passo; balanço de trabalho; domínios/limites; separar campo prescrito de MHD autoconsistente. |
| IS-5 — núcleo solar, matéria e emissão | Associar zona pp/CNO ao Sol; abrir forte/fraca por canal; conectar diagnósticos de energia/neutrinos | Conservação de bárions/carga/energia, taxas e perdas; distinção entre potência nuclear, reservatório térmico e luminosidade. Fluxo espacial só com emissão/normalização/propagação modeladas. |
| IS-6 — percurso conjunto e expansão | Uma jornada que atravesse os corpos e as quatro forças; ampliar planetas/luas; malha relativística C2-14/15 | Salvar/reabrir/ramos e versões antigas; UI nativa e sondas coerentes; capturas revistas e perfis próprios com múltiplas camadas. |

IS-1 começa pelo contrato e pelos dados, sem exigir aprovação artificial da
candidata EM atual. Sua promoção depende das verificações próprias; a
integração visual EM de IS-3/4 depende de concluir as pendências de C2-12.
Correspondência: IS-1/2 → C2-13/16 e extensões de C2-06/11; IS-3/4 → C2-12/13;
IS-5 → C2-18/19/20; IS-6 → C2-14/15/16/17. Não renumerar os marcos anteriores.

Antes de capturar cada fatia, fixar fixture, tolerâncias e orçamento em
contrato próprio, usando os limites já vigentes onde aplicáveis. A janela de
30 dias acima é um teste proposto, ainda não executado. Erro do integrador,
diferença de modelo, incerteza de dados e desempenho são avaliações separadas.
Não exigir que um modelo newtoniano de quatro corpos replique toda a JPL.

## Exemplos que devem acompanhar os controles

1. **Terra–Lua–Sol:** mostrar vetores por fonte e a aceleração total. Dobrar
   a distância de uma sonda a uma fonte isolada reduz sua aceleração a 1/4.
   A maré é a diferença do campo entre ponto e centro, não a aceleração total.
   O exemplo pode mostrar o Sol atraindo mais fortemente a Terra e ainda
   tendo menor efeito de maré que a Lua. Não prever maré costeira com esse
   campo sozinho: a [NOAA](https://www.nesdis.noaa.gov/about/k-12-education/oceans-coasts/what-causes-tides)
   explica o papel da geometria e da resposta oceânica.
2. **Júpiter ligado/desligado:** comparar dois ramos com a mesma condição
   inicial e exibir Δposição/Δvelocidade da Terra/Lua. Ampliar graficamente a
   diferença com legenda; não exagerar os números físicos para torná-la visível.
3. **Próton próximo da Terra:** comparar E/B visíveis/ocultos e atuantes/inativos;
   verificar a hélice, carga com sinal, trabalho elétrico e potência magnética
   nula no campo prescrito. O caso uniforme é referência didática, separado do IGRF.
4. **Sol por dentro:** explicar a barreira eletrostática, ligação/reação
   nuclear e o canal fraco p+p→D+e⁺+νe. Os papéis se combinam; não classificar
   toda fusão como exclusivamente forte. Referência:
   [DOE, fusão próton–próton](https://www.energy.gov/science/np/articles/proton-proton-fusion-powering-sun).
5. **Amostra de carbono-14:** acompanhar população média, filha e antineutrinos
   por meia-vida; esclarecer que desligar beta suprime aquele canal. Outras
   formas de radioatividade, como emissão alfa, não são todas processos fracos.
6. **Controles gerais:** ocultar um campo mantém exatamente a evolução;
   suprimir um operador registra intervenção hipotética, preservando as fontes.
   Esses controles não resolvem um novo universo autoconsistente com constantes
   fundamentais diferentes.

Malha de espaço-tempo continua obrigatória no seu marco. Não somar funis
Schwarzschild dos quatro corpos e apresentar a soma como solução relativística.
Usar o modelo/observador apropriado e validar comprimentos/relógios conforme
CAMADAS-QUATRO-FORCAS.md.

## Próximo passo para a retomada

Ler o relatório de testes e `LEIA-PRIMEIRO.md`. IS-1 já tem contrato e dados
candidatos descritos em `IS-1-CONTRATO-CORPOS.md`: subconjunto599/5 isolado,
201 comparações exatas e cinco épocas aprovadas contra Horizons. O GM físico
599 foi fixado com procedência e a fixture inicial de quatro corpos está
preparada. Ampliar a API em candidata e executar os critérios de
`IS-2-VALIDACAO-PREVIA.md`. Em paralelo
sequencial, resolver a falta de diagnóstico da recusa nativa J potencial B,
preservando a execução original. Não repetir perfis formais às cegas, nem
promover J sem os três perfis próprios e aceite visual conjunto.
