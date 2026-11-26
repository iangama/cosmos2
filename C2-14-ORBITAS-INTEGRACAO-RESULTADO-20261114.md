# C2-14 — integração das órbitas e dos relógios

O núcleo, o serviço e o backend HTTP passaram. A candidata isolada 0.28.1 acrescenta comparação Newton/GR no mesmo estado inicial coordenado, linha do tempo de 1.025 pontos e atraso integrado dos relógios. O movimento orbital e o ritmo do relógio possuem operadores independentes; ocultar referências preserva o resultado físico. A intervenção de trajetória reta calcula o relógio sobre a própria trajetória, e não reaproveita o tempo próprio de uma geodésica diferente.

O serviço mantém o último resultado completo durante cálculo/cancelamento. Salvar, retomar e exportar usam pastas privadas e registram modelo, fontes e geração. Círculos não recebem precessão ou periastros artificiais.

Recibos aceitos: CPU 20261114a (20 casos, 23 recusas), serviço 20261114a (cinco grupos, dez recusas), HTTP 20261114b (quatro grupos, seis recusas, saída 0). HTTP A é preservado e recusado: imports legados desviavam os módulos locais; v2 fixa os módulos locais antes desses imports.

O nativo A completou cinco grupos e quatro capturas, com oito saídas 0 e restauração da vista/favoritos. Foi recusado porque o manifesto incluía o descritor operacional de PIDs como fonte imutável. Sua inspeção visual também recusou legenda de relógios e espaçamento do eixo. Tudo foi preservado. A revisão B remove somente esse descritor do conjunto de fontes mediante prova de restauração; demais protegidos e todas as fontes científicas permanecem selados. Corrige a legenda e o espaçamento e marca a posição Newton no instante escolhido.

As quatro imagens originais B foram inspecionadas e aceitas no escopo das vistas excêntrica e de relógios em 100/150%. Em 150%, a linha do tempo requer rolagem vertical. Ver o recibo nativo B para o estado final do ensaio, e o recibo visual B para seus limites.

Esta entrega é a bancada Canvas dentro do CEF do OpenSpace. Não acrescenta órbitas ao SceneGraph do Atlas nem acopla GR aos dezesseis corpos. Perfil de desempenho/residência próprio ainda pendente. C2-14 e V1 não recebem aceite completo por esses resultados. Produto 0.27 e atalhos preservados; nada promovido ou publicado.
