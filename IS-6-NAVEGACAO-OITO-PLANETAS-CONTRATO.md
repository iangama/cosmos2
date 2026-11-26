# Navegação dos oito planetas

A próxima candidata estende a cena do Atlas aos oito planetas e à Lua.
Os seis globos adicionais usam os centros físicos já conferidos no
catálogo0.23, seus kernels fixados e as rotações IAU gerais do PCK00011.
O perfil próprio seleciona o arquivo de cena da candidata por caminho
absoluto. O estado geométrico usa DE442s e os deslocamentos planetários
declarados no catálogo, dentro da janela comum1995–2049.

Os mapas vêm dos recursos de sincronização do OpenSpace consultados no
código upstream local. Guardar manifesto, URL, bytes, dimensões, SHA256
e fonte Lua de cada recurso. São mapas visuais fixos. Sua época e origem
observacional recebem declaração própria quando forem conhecidas.
O campo magnético e a física orbital seguem os provedores registrados.

O Atlas terá seleção, busca, árvore, distância da câmera, visita direta
e suave, vistas iluminada/polar/terminador, retorno, voo livre, época,
favoritos e exportação para os novos planetas. A interface identifica os
oito destinos e conserva a consulta de dados por propriedade.

Conferir os dez estados nativos em cinco épocas. A diferença entre a
posição nativa em GALACTIC e a referência calculada deve ficar em
max(1mm,8ULP do maior componente). Esse orçamento mede arredondamento do
readback. Comparar orientações com erro máximo1e−12 por elemento e verificar
semieixos e nomes dos arquivos realmente usados pelo renderer.

O roteiro nativo visita os nove destinos físicos, testa troca e recusa de
época, retorno, favoritos em armazenamento próprio e transição para a cópia
gravitacional existente. Conferir as sondas e o contexto da experiência
separada, incluindo seu LabRoot deslocado. Capturas100/150 de cada novo
planeta precisam de revisão. Testes de uma nova versão terão recibos próprios.

O perfil posterior usará1920×1080, UI100%, aquecimento30s e coleta60s por
destino. Permanecem mediana≤16,7ms, p95≤25ms, p99≤50ms e zero quadros>100ms;
RAM≤8GiB e soma WDDM≤5,5GiB. A coleta usa árvore temporal de processos,
préviaPDH e66amostras por janela. O rastreamento por etapa fica ativo para
localizar pausas que surjam. Definir a receita final e selar fontes antes
da execução. O aceite desse perfil pertence à nova cena.

O aplicativo aberto a pedido do dono deve receber aviso antes de uma troca
de versão. Conferir seu estado atual e conservar uma cópia da navegação
antes da troca. O trabalho offline prossegue com a janela aberta.
