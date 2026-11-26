# Pesquisa de referências e escolha da base

Consulta: 11/10/2026. Pesquisa documental em fontes oficiais e leitura de
arquivos públicos de código. Nenhum dos quatro aplicativos foi instalado ou
comparado em execução nesta etapa. As avaliações de esforço e adequação abaixo
são conclusões de projeto, não resultados de benchmark.

## 1. O que aprender com cada referência

| Referência | Contribuição principal ao Cosmos2 | Limite relevante |
| --- | --- | --- |
| SpaceEngine | Sensação de viagem contínua, corpos com presença visual, descoberta e superfícies | A escala de exploração não significa recalcular toda a dinâmica do universo |
| Universe Sandbox | Editar um objeto e compreender o resultado; ferramentas diretamente na cena | Cálculo físico tem custo e domínio de validade; acelerar o tempo exige controle de erro |
| OpenSpace | Navegação entre escalas, terrenos e camadas com procedência científica | Produto orientado a visualização; laboratório dinâmico exige desenvolvimento próprio |
| Celestia | Busca, seleção, seguir objetos, hierarquia de sistemas e complementos | Base de planetário; terreno procedural e colisões elaboradas não vêm resolvidos para nosso produto |

### SpaceEngine

O site descreve um universo que combina objetos de catálogos e geração
procedural, com navegação contínua entre superfícies e grandes distâncias.
Busca, visita a objetos, favoritos e ferramentas de escala sustentam a
exploração. O código é proprietário e fechado. Para o Cosmos2, serve de
referência de experiência e qualidade visual; não há base de código pública
a incorporar. Texturas, interface e modelos comerciais não entram no pacote.
[Visão oficial](https://spaceengine.org/),
[FAQ](https://spaceengine.org/manual/faq/).

### Universe Sandbox

Os desenvolvedores descrevem gravidade N-corpos e aproximações para permitir
interação em computadores pessoais. A lição central é tornar a alteração de
parâmetros observável e legível. A documentação de 2016 sobre integração é
uma explicação histórica, não especificação do solver atual.
[FAQ](https://universesandbox.com/faq/),
[N-corpos](https://universesandbox.com/blog/2016/02/n-body-problem/).

O roteiro de março de 2026 menciona migração de partes da simulação para
Unity DOTS e pesquisa em Barnes–Hut. Distinguir itens planejados de recursos
entregues: existe também o anúncio Update 36. Não presumir que tudo no roteiro,
como superfícies detalhadas e novas formas de colisão, já esteja disponível.
Não foi obtido nem presumido acesso ao código do aplicativo.
[Roteiro](https://universesandbox.com/blog/2026/03/universe-sandbox-roadmap-2026/),
[Update 36](https://universesandbox.com/blog/2026/03/pale-blue-dots-update-36/).

### OpenSpace

É software aberto para visualização astronômica. O projeto possui globos com
camadas de cor, elevação e iluminação, navegação e integração de dados de
diferentes escalas. A licença principal tem texto MIT; dependências e dados
têm seus próprios termos. O suporte gráfico atual requer OpenGL 4.6, e a
documentação registra diferenças de compatibilidade entre fabricantes.
[Projeto](https://github.com/OpenSpace/OpenSpace),
[camadas](https://docs.openspaceproject.com/releases-v0.22/building-content/globebrowsing/working-with-layers.html),
[compilação](https://docs.openspaceproject.com/latest/contribute/development/compiling/index.html),
[licença da versão candidata](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/LICENSE.md).

### Celestia

O repositório documenta navegação, seleção por nomes, navegador de estrelas,
árvore de sistemas e extensões por catálogos SSC, STC e DSC. Sua licença é
GPL versão 2 ou posterior. O código de coordenadas universais usa representação
de alta precisão e diferenças locais antes de reduzir a precisão de desenho:
uma referência útil para evitar tremor em escalas astronômicas.
[README e licença](https://github.com/CelestiaProject/Celestia),
[coordenadas](https://github.com/CelestiaProject/Celestia/blob/master/src/celengine/univcoord.h).

O site principal retornou bloqueio automatizado na consulta. A pesquisa do
Celestia usou o repositório oficial; não se tentou contornar esse bloqueio.

## 2. Estado observado e cuidado com versões

| Item | Observação em 11/10/2026 | Uso no plano |
| --- | --- | --- |
| OpenSpace | API oficial `releases/latest`: `releases/v0.22.0`, publicada em 12/06/2026 | Candidata inicial da prova, sujeita a reconferência ao implementar |
| Celestia | API oficial `releases/latest`: `1.6.4`, publicada em 04/11/2023 | Esse endpoint não descreve todo o desenvolvimento ou pré-lançamentos |
| OpenSpace `master` | Organização de build difere da tag; `.gitmodules` não existe nesse caminho consultado | Não misturar instruções de branches e releases |
| OpenSpace v0.22.0 | CMake mínimo 4.0 no arquivo consultado; submódulos, SPICE e integração CEF identificados | Congelar commit, submódulos e pacote da interface como um conjunto |
| Interface oficial OpenSpace | Manifesto atual contém React, TypeScript, Vite e API JavaScript do OpenSpace | Referência de extensão; versões compatíveis serão as da release escolhida |

Fontes de versão: [OpenSpace](https://api.github.com/repos/OpenSpace/OpenSpace/releases/latest),
[Celestia](https://api.github.com/repos/CelestiaProject/Celestia/releases/latest),
[build estável](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/CMakeLists.txt),
[submódulos estáveis](https://github.com/OpenSpace/OpenSpace/blob/releases/v0.22.0/.gitmodules),
[interface](https://github.com/OpenSpace/OpenSpace-WebGui/blob/master/package.json).
Essas observações não são um arquivo de dependências instalado.

## 3. Alternativas de arquitetura

Escala qualitativa: alta adequação significa menos trabalho novo para o objetivo.
As notas são julgamento desta pesquisa. Compatibilidade e desempenho não foram
medidos; não há soma numérica que possa decidir por eles.

| Caminho | Exploração de várias escalas | Visual planetário | Sandbox físico próprio | Trabalho de infraestrutura | Parecer |
| --- | --- | --- | --- | --- | --- |
| OpenSpace + módulos Cosmos2 | Alta | Alto ponto de partida | Viável, integração a provar | Médio; build/dados/interface relevantes | Candidato preferido |
| Celestia + extensões | Alta | Bom para atlas; modernização adicional | Viável, também exige solver | Médio; terreno e interface ampliam o custo | Alternativa de base |
| Unreal Engine + núcleo científico | Construir hierarquia astronômica | Alto potencial | Viável fora da física de jogo padrão | Alto; catálogos, escalas e pipelines próprios | Alternativa se visual de superfície dominar |
| Rust + wgpu ou C++ + API gráfica própria | Construir | Construir | Controle amplo | Muito alto; renderização, ferramentas e conteúdo novos | Adiar; não começar por um motor genérico próprio |
| Godot | Exige projeto astronômico específico | Depende de desenvolvimento | Núcleo externo possível | Médio/alto para esta meta | Não adotado por inércia do Cosmos anterior |

Unreal oferece tipos de maior precisão e renderização relativa à câmera, mas
isso não elimina a necessidade de referenciais cósmicos. Seus termos de uso
dependem da modalidade do produto; não existe compromisso de contratação neste
plano. wgpu é uma API gráfica multiplataforma, não um planetário completo.
[Unreal LWC](https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-in-unreal-engine-5),
[renderização LWC](https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-rendering-in-unreal-engine-5),
[termos oficiais](https://www.unrealengine.com/license),
[wgpu](https://github.com/gfx-rs/wgpu).

## 4. Recomendação e condição de mudança

Propor um aplicativo Windows nativo baseado no núcleo C++/OpenGL do OpenSpace,
com perfil de conteúdo próprio, interface Cosmos2 e um módulo de simulação
local independente. Reusar navegação, terreno e mecanismos de dados onde
forem adequados. Manter as alterações ao núcleo pequenas e documentadas.

A primeira prova precisa verificar simultaneamente: imagem convincente,
compatibilidade AMD, abertura offline, interface própria e atualização de
posições físicas sem travar o desenho. Apenas abrir o OpenSpace não aprova a
arquitetura. A interface documentada e as classes de translação tornam esse
caminho plausível; não constituem uma garantia de integração pronta.
[Controles personalizados](https://docs.openspaceproject.com/latest/building-content/custom-web-ui/index.html),
[classe de translação](https://github.com/OpenSpace/OpenSpace/blob/master/include/openspace/scene/translation.h).

Se a prova reprovar um requisito central e a correção ultrapassar o limite do
marco C2-00, registrar a causa e testar Celestia numa prova equivalente. Se o
problema dominante for a qualidade de superfícies e a base alternativa também
não atender, reavaliar Unreal. Não desenvolver dois produtos completos em paralelo
nem trocar de motor apenas por uma imagem promocional mais bonita.

## 5. Ciência e dependências especializadas

REBOUND é candidato ao worker gravitacional: núcleo em C, integradores para
diferentes regimes e rotinas de colisão. Sua licença é GPL-3.0; usar um processo
separado é uma decisão técnica, não uma conclusão automática sobre obrigações
de distribuição. Antes de qualquer distribuição, revisar o conjunto de código,
licenças e dados. O desenvolvimento local não exige decidir hoje se o Cosmos2
será publicado ou vendido.
[REBOUND](https://github.com/hannorein/rebound),
[integradores](https://rebound.hanno-rein.de/integrators/).

SPICE fornece geometria e efemérides; não passa a recalcular a órbita de um
planeta porque sua massa foi editada. Esse ponto define a transição explícita
do Atlas para Experimento. Geant4 e pynucastro são candidatos futuros para,
respectivamente, transporte de partículas e redes de reações. Nenhum deles
resolve sozinho a evolução completa do cosmos e das quatro forças.
[SPICE](https://naif.jpl.nasa.gov/naif/aboutspice.html),
[Geant4](https://geant4.web.cern.ch/about/),
[pynucastro](https://pynucastro.github.io/pynucastro/intro.html).

## 6. Incertezas que permanecem

Desempenho da RX 7600 com a release candidata; esforço real para substituir a
interface e ligar o worker; licenças de cada pacote de conteúdo; tamanho final
do perfil offline; custo de terrenos procedurais; preferência do dono entre
exploração e experimentação. O plano adota provisoriamente equilíbrio entre
ambas, com exploração visual primeiro. A prova inicial resolve as incertezas
técnicas antes de multiplicar funcionalidades.
