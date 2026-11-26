# IS-1 — contrato antes da integração dos quatro corpos

Primeira fatia do PLANO-INTEGRACAO-SISTEMA-SOLAR.md. Estado: contrato,
inventário e dados candidatos verificados, sem alteração do produto instalado, da candidata J ou dos
modelos científicos existentes. Não há aceite da cena conjunta.

## Evidência disponível

Executado `scripts/inventory-solar-integration.py` no Python Windows do projeto.
Recibo `evidence/solar-integration-kernel-inventory-20261023.json`: estados
geométricos de Sol10, Terra399, Lua301 e baricentro joviano5 disponíveis em
11/10/2026 12h UTC; centro de Júpiter599 indisponível nos kernels carregados
pelo Atlas. A orientação geral IAU_JUPITER existe no PCK, mas uma orientação
disponível não fornece o estado translacional que falta.

Esse inventário refere-se ao conjunto científico carregado pelo Atlas.
Assets upstream do OpenSpace têm suas próprias dependências; sua existência
não é prova de que o novo catálogo possua dados científicos fixados/validados.

## Registro de corpo

Cada registro deve ter os campos abaixo, com validação anterior à instalação
na sessão. A implementação será feita em candidata isolada.

| Campo | Conteúdo e regra |
| --- | --- |
| `id` / `naif_id` | Identidade estável `sol:naif:10/399/301/599`; baricentro5 fica em registro distinto, se exposto. |
| `entity_kind` | `physical_body` ou `system_barycenter`; nunca deduzir pelo nome traduzido. |
| `state_provider` | Kernels e hashes, centro de consulta0, J2000, correção NONE; cobertura efetiva para a cadeia completa. |
| `epoch` | UTC de apresentação e ET/TDB de cálculo; política da tabela de segundos intercalares. |
| `position_m` / `velocity_m_s` | Vetores finitos em SI, referencial declarado; uma mesma época geométrica para todo o conjunto. |
| `GM_m3_s2` | Fonte, resolução/incerteza disponível, corpo ou sistema ao qual pertence. `null` com motivo quando não adotado. |
| `shape` / `rotation` | Modelo e validade próprios; raio gráfico separado de raio de referência. |
| `capabilities` | Camadas com estado, modelo/versão, procedência, domínio, frame, época e dependências. |
| `provenance` | Geração de código/dados, tipo de origem e alterações do usuário. |

Valores desconhecidos permanecem `null` com motivo. Não aceitar NaN/infinito,
booleanos como números, IDs duplicados, frame implícito, GM negativo ou
metadados que chamem um baricentro de planeta. As recusas são transacionais:
nenhuma muda a fase, câmera, sessão ou arquivos do usuário.

## Matriz inicial de capacidades

| Corpo | Gravidade | Campo magnético | Processo nuclear |
| --- | --- | --- | --- |
| Sol10 | Estado e GM de referência disponíveis; cópia dinâmica legada | Modelo solar ainda não adotado | Bancadas pp-I/CNO-I; falta associação à cena e resposta estrutural. |
| Terra399 | Estado e GM disponíveis; cópia dinâmica legada | IGRF14 validado em instrumento separado; associação pendente | Dados de referência/bancadas; inventário isotópico real não adotado. |
| Lua301 | Estado e GM disponíveis; cópia dinâmica legada | Sem componente global atual no modelo descrito; crostal/externo não adotados | Dados de referência/bancadas; inventário isotópico real não adotado. |
| Júpiter599 | Estado/GM do planeta ainda não fixados nesta candidata | JRM33 selecionado para estudo; coeficientes/convenções/domínio ainda não adotados | Constituição nuclear; não assumir fusão estelar atual nem inventário isotópico. |

Estados da camada: `unavailable`, `available_reference`, `available_bench`,
`integrated_prescribed` e `integrated_evolving`, com motivo e capacidades
específicas. O estado sozinho não define precisão. Uma ausência de dipolo
global não torna nulos os campos crostais e externos. Uma bancada nuclear
disponível não equivale a abundâncias medidas no corpo selecionado.

## Importação para a dinâmica

Preservar `atlas_sun_earth_moon` e o validador legado. O conjunto de quatro
corpos usa novo tipo/versionamento, com referência e ramos próprios. Converter
estados SI para unidades canônicas após calcular o baricentro do subconjunto
com GMs compatíveis. Preservar estados SSB originais, translação e velocidade
da origem para inversão e comparação. Não editar identificadores nem somar
estado de 599 ao baricentro5 como se fossem corpos independentes.

Dois recortes jovianos são distintos: sistema agregado em5 com GM do sistema,
ou planeta599 e luas explícitas com GMs individuais. O requisito visual/físico
prioriza599. Um eventual agregado deve ser nomeado assim e não herdar camadas
centradas no planeta. Com quatro centros e sem luas jovianas, declarar as
influências omitidas e testar o próprio modelo reduzido.

O somatório newtoniano usa cada fonte uma vez. Gravidade dos outros corpos
reage também sobre o Sol. Partículas-teste podem omitir reação sobre planetas
apenas com essa aproximação explícita. Um campo magnético prescrito não deve
ser convertido automaticamente em força sobre o centro de um corpo neutro.

## Época e referenciais dos campos

IGRF: converter posição e vetor entre J2000 e ECEF no mesmo instante,
explicando a precisão do modelo de rotação escolhido. O Atlas usa PCK geral;
isso não equivale a orientação terrestre precisa com EOP/ITRF. A validade
temporal do campo pode ser menor que a dos kernels orbitais.

JRM33: conferir raio de referência, normalização dos harmônicos, grau,
longitude e convenção SystemIII/rotação publicadas antes de adotar o modelo.
Não presumir que uma matriz IAU_JUPITER substitui todas essas convenções.
Campo interno e modelo de correntes externas terão registros distintos.

Fora do domínio, recusar ou identificar uma extrapolação autorizada pelo
modelo; não zerar o campo. Uma camada congelada mantém sua época/revisão
visível. A sonda deve retornar o mesmo provedor usado para as linhas/mapas.

## Critérios que faltam executar

1. Adquirir/fixar dados de599 e GM compatível; verificar integridade, licença
   e cobertura comum. Manter os arquivos fora da promoção até aceitar.
2. Cinco épocas e consultas independentes JPL/Horizons com mesmos centros,
   escala temporal, correção e frame. Fixar tolerâncias antes da captura.
3. Validar referências/IDs/GMs, ida e volta SI/canônicas e separação
   planeta/baricentro. Recusar dados adulterados sem mutação.
4. Reexecutar os testes legados de três corpos somente após mudar a integração.
   Não gastar nova rodada científica por simples mudança deste contrato.
5. Fazer a propagação de quatro corpos por30dias em IS-2, contra uma ODE
   independente do mesmo modelo, com refinamento e balanços separados da
   comparação com efemérides completas.

## Fonte candidata a examinar na próxima retomada

O [diretório oficial NAIF de satélites](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/)
lista JUP365 (luas principais) e JUP347/348/349. Ler os comentários e
coberturas antes de escolher: número maior não prova adequação ao planeta
e às luas exigidas. JUP365 completo é aproximadamente1,1GB no diretório;
avaliar subconjunto reproduzível e armazenamento proporcional. Não baixar
todo acervo de satélites por rotina. O arquivo
[gm_de440.tpc](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc)
mistura parâmetros de fontes indicadas nos comentários; não tratá-lo como
um único ajuste contemporâneo ou assumir compatibilidade só pelo nome.

## Avanço posterior do mesmo ciclo: dados candidatos disponíveis

Os comentários foram lidos. O [JUP348 oficial](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup348.cmt)
inclui o centro599 herdado de JUP365 e estados DE442 de5/10/3/399. Foi adquirido
somente JUP348, 59.772.928bytes, com MD5 oficial conferido e SHA256 próprio
`9b04592fb6d5448eba480c347b60ed5f0629d049e59417c40039021b64662701`.
Comentários JUP348/JUP365 e receitas foram fixados no mesmo cache.

`scripts/prepare-jupiter-candidate-subset.py` extraiu apenas599 relativo a5,
frame1/J2000, numa candidata de6.565.888bytes, com cobertura de30/12/1949 a
03/01/2051 (limites UTC convertidos pelo LSK fixado). Em201épocas, os seis
componentes relativos ficaram bit a bit iguais aos polinômios originais;
adicionar o subconjunto manteve os estados DE442s10/399/301/5 idênticos.
O centro599 e o baricentro5 ficaram separados por4,77–215,85km nessa amostra.

Cinco épocas também passaram contra consulta independente ao serviço
Horizons, alvo599/centro5, ICRF/TDB/NONE: diferença de posição máxima
0,000103m e de velocidade2,15×10⁻⁹m/s. Limites fixados antes da consulta:
1m e10⁻⁵m/s. Comparação da mesma família de efemérides por outro percurso;
não é precisão observacional. Resposta original e cabeçalho foram guardados.

Recibos: `evidence/jupiter-acquisition-20261023.json`,
`jupiter-candidate-subset-20261023.json` e
`jupiter-candidate-reference-20261023.json`. Dados derivados em
`output/solar-integration-staging/jupiter-center-jup365-from-jup348.bsp`.
O Atlas e o importador do produto continuam com os corpos anteriores.

O GM físico599 foi fixado para a candidata a partir das duas linhas
concordantes da tabela JUP365:126686531900370400m³/s². O recibo
`evidence/jupiter-candidate-gm-20261023.json` preserva valor original, linhas,
fonte e valores diferentes dos comentários JUP348 e do sistema5/DE442.
Incerteza não adotada permanece desconhecida; não é erro zero.

Foi preparada a condição inicial de quatro centros em
`output/solar-integration-staging/four-body-initial-si.json`, época
11/10/2026 12hUTC, com estadosSSB/J2000, GM e contribuições gravitacionais
por fonte, mais transformação para o baricentro do subconjunto. São dados
iniciais candidatos, ainda SEMpropagação aprovada ou integração no produto.

Próxima ação exata: implementar o cadastro/API em candidata isolada e executar
a referência numéricaIS-2 com a fixture já preparada, preservando o caminho
legado de3corpos. Não carregar o JUP348 completo no Atlas: isso poderia
substituir a autoridade DE442s de outros alvos e incluir luas não solicitadas.
