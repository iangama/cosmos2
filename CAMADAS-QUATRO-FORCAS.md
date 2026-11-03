# Camadas das quatro forças — requisito de 18/10/2026

Pedido do dono: incluir a malha espaço-temporal e visualizações semelhantes
para todas as forças, incluindo os campos eletromagnéticos dos corpos que os
possuem. Implementação contínua autorizada. Este documento torna as camadas
uma saída obrigatória da v1; não declara recursos implementados nem muda o
prazo em PLANO-UM-MES.md.

Antes deste pedido já estavam previstos campos 3D, relatividade e controles
independentes. A malha era descrita como possível auxiliar didático, sem uma
entrega explícita. A associação de campos EM ao catálogo de corpos também
precisava de critérios de conclusão próprios.

## Entregas e etapas responsáveis

| Camada | Entrega obrigatória | Etapas |
| --- | --- | --- |
| Gravidade | Campo 3D ao redor do corpo, vetores, linhas e equipotenciais; atração acima/abaixo/laterais e fontes múltiplas verificadas. | C2-11; ampliação dos mapas em C2-14 |
| Malha espaço-temporal | Botão próprio para mostrar/esconder uma malha de referência do modelo relativístico; corte espacial navegável, fonte selecionável, observador/coordenadas identificados, medida de distância própria, relógios e curvatura. | C2-14, extensão Schwarzschild/Kerr em C2-15 |
| Campo elétrico | E vetorial, linhas, potencial, fonte/carga e força medida; superposição e configuração de cada fonte suportada. | C2-12 |
| Campo magnético | B vetorial, linhas 3D, cortes/mapas e sondas associados ao corpo selecionado; orientação do modelo no referencial do corpo e época explícita. | C2-12 (modelos sintéticos), C2-13 (corpos e dados) |
| Nuclear forte | Camadas de ligação, composição, canais e taxas na escala nuclear; mapas de energia/potencial apenas quando calculados por modelo efetivo declarado. Exibir dependências de canais mistos. | C2-18 e C2-20 |
| Nuclear fraca | Camadas de decaimento, atividade, canais, produtos, energia e neutrinos na escala do modelo; mapas de emissão da zona quando houver distribuição espacial suportada. | C2-19 e C2-20 |

“Semelhantes” significa controles, navegação, legendas, medição e integração
consistentes. A representação acompanha a grandeza física. As camadas forte
e fraca usam os palcos nucleares e estelares; não se desenha um campo clássico
planetário fictício para elas. O alcance e a escala dessas interações são
distintos dos campos gravitacional e eletromagnético.
[CERN — interações fundamentais](https://home.web.cern.ch/science/physics/standard-model/).

## Malha de referência gravitacional

O volume 3D e a queda radial continuam presentes. A malha é outra camada,
com opção de corte/orientação, escala visual e restaurar vista. Na primeira
fatia, usar o exterior esférico estático de Schwarzschild e um corte espacial
com geometria derivada da métrica. Escolher coordenadas, domínio e superfície
antes de implementar. Comparar comprimentos calculados na malha com a métrica
e testar o limite de massa nula/espaço plano.

O produto pode chamar o controle de “Malha espaço-temporal”, acompanhado de
“corte espacial do modelo” e da grandeza exibida. A altura do desenho e qualquer
ampliação são gráficas e têm legenda; não são uma quarta direção física nem
um tecido material. Não somar funis Schwarzschild de várias massas e apresentar
isso como solução relativística de muitos corpos. A extensão de campo fraco e
a extensão Kerr precisam de validação própria em C2-14/15.
[EinsteinPy — exemplo de embedding espacial](https://github.com/einsteinpy/einsteinpy/blob/main/docs/source/examples/Plotting%20Spatial%20Hypersurface%20Embedding%20for%20Schwarzschild%20Spacetime.ipynb).

## Campos dos corpos do catálogo

Cada corpo terá um registro de capacidades por camada: modelo disponível,
tipo de origem (medido/ajustado/sintético), fonte, versão, validade temporal,
referencial, unidades e domínio radial. Distinguir modelo indisponível, ausência
de componente global no modelo e valor nulo calculado. Dado desconhecido não
vira campo zero. Campo interno, crostal, induzido e externo têm procedências
e controles separados quando suportados.

Primeiro integrar a Terra com o IGRF já fixado, mantendo o dipolo sintético como
comparação identificada. C2-13/16 deve auditar os 12 destaques previstos e o Sol:
ligar um modelo validado ao corpo onde houver dados adotados e informar o que
falta nos demais. Próximas escolhas de modelos, coeficientes e licenças serão
registradas antes da implementação; esta lista não promete que todos tenham
o mesmo tipo de campo. Incluir exemplos de campos intrínsecos, localizados e
induzidos, em vez de atribuir um dipolo global a todo planeta/lua.
[NASA — Terra e Júpiter](https://science.nasa.gov/photojournal/earth-and-jupiter-magnetic-fields/),
[NASA — campo induzido de Vênus](https://science.nasa.gov/venus/venus-facts/).

Campos elétricos em torno de corpos também exigem carga/modelo de plasma ou
modelo externo escolhido; o botão não cria carga líquida observacional.
Respostas a rotação, vento solar e atividade só variam quando o modelo contém
essas variáveis. Conjunto de snapshots e ilustração continuam identificados.

## Controles e critérios de aceite comuns

1. Um painel permite selecionar corpo/região e mostrar/esconder cada camada.
   Separar E de B e campo de curvatura de campo newtoniano. Camadas simultâneas
   têm legendas próprias e não compartilham uma unidade incompatível.
2. Atuação física continua independente da visualização. Testar as quatro
   combinações em cada interação/efeito suportado. Esconder a camada preserva
   estado, evolução e resultados; desligar atuação registra a hipótese.
3. Sondas consultam a mesma solução da imagem, com posição, unidade, tempo,
   revisão e erro do modelo. Linhas, superfícies e malha usam essa solução;
   não constituem animações decorativas desvinculadas das leituras.
4. Guardar seleção, configuração, visibilidade e modelo em sessões/ramos;
   exportar leituras e procedência. Ao mudar o estado, atualizar a camada ou
   identificar claramente a leitura congelada.
5. Testar acima/abaixo/laterais, rotação do corpo, troca de fonte, épocas e
   domínios inválidos. As quatro interações passam pelo percurso da interface
   real, incluindo salvar/retomar, limpeza e migração de versões anteriores.
6. Medir cena e recursos com camadas ligadas/desligadas e múltiplas camadas,
   dentro dos orçamentos vigentes. Perfis antigos sem essas camadas não provam
   o desempenho das novas. Não ampliar o número de amostras sem medir.

## Ordem de execução e estado

- C2-11: concluir o corte atual 3.13 de partículas e corrigir/verificar os
  problemas de integração e estabilidade registrados em 18/10. Esse aceite
  parcial não encerra o pedido das camadas nem toda a etapa C2-11.
- C2-12: fontes/cargas e infraestrutura comum das camadas E/B, seguida da
  integração de corpos e magnetismo em C2-13.
- C2-14: primeira malha relativística utilizável e medida; C2-15 amplia o regime.
- C2-18/19/20: completar as camadas nucleares e estelares nos modelos previstos;
  forte/fraca não são adiadas para uma expansão posterior à v1.
- C2-16/17: fechar catálogo, percursos integrados e aceite conjunto. A v1 não
  fica concluída com a malha ou as camadas solicitadas ainda ausentes.

Estado em 18/10: requisito adicionado ao plano; malha ainda não implementada.
Campo gravitacional, referência de curvatura e parte das vistas EM/nucleares
já existem nos recortes registrados em QUATRO-FORCAS.md. Os testes específicos
do pedido anterior estão em RELATORIO-GRAVIDADE-MALHA-2026-10-18.md.
