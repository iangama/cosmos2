# Oito planetas navegáveis na candidata0.24.0

A cena ampliada está construída e aberta no simulador. Mercúrio, Vênus,
Marte, Júpiter, Urano e Netuno somam-se a Terra, Lua e Saturno. O Sol
permanece como fonte de iluminação e corpo do catálogo. A interface possui
seleção, busca, árvore, distâncias e os controles de câmera para os nove
destinos físicos. A candidata permanece isolada e sem promoção.

As posições geométricas dos dez centros passaram nas cinco épocas do
contrato, inclusive as bordas da janela1995–2049. A diferença máxima de
readback foi0,48828125mm; o orçamento prévio era max(1mm,8ULP). As nove
rotações tiveram erro máximo1,1102230246251565e−16 por elemento, abaixo
de1e−12. A API conserva ET/TDB exato, sem arredondar pelo texto UTC.

Os27semieixos foram recuperados a partir da altitude geodética do próprio
renderer, colocando a câmera nos eixos principais de cada globo. A maior
diferença foi0,367477536mm, com limite prévio2cm. Os seis caminhos de textura
realmente usados no motor apontam aos arquivos fixados e mantêm seus hashes.
São mapas fixos, com época e origem observacional ainda sem confirmação.

O roteiro visitou os nove destinos pela interface e aplicou quatro vistas
a cada planeta novo. Quatro épocas inválidas foram recusadas conservando
os dados confirmados. Favoritos da candidata salvaram/restauraram Netuno;
seguir rotação, voo livre, deslocamento e avanço/pausa do relógio passaram.
As cópias anteriores de três e quatro corpos continuaram funcionando,
pausadas no instante inicial, com posições nativas conferidas. O laboratório
fica em LabRoot deslocado1e14m, preservando seu contexto separado do Atlas.

A revisão visual inspecionou as12capturas nativas de seis planetas em100%
e150%. Globos, fichas, fontes, limites dos mapas e rolagem ficaram legíveis.
Na interface ampliada, Ver ficha/Ver catálogo alterna os painéis.

Os recibosA/B/C de verificação foram preservados com suas recusas. A
primeira versão interpretou o vetor geodético como três retornos Lua; a
segunda usou um seletor de painel inexistente; a terceira confundiu a esfera
envolvente dos anéis de Saturno com o raio máximo do globo. O complementoD
concluiu os semieixos e controles, aproveitando as posições/visitas deA e
capturas deC com hashes selados. O limite dos semieixos permaneceu2cm.

Evidências: `is6-planet-navigation-native-20261111a/b/c/d.json` e
`is6-planet-navigation-visual-20261111a.json`, na pastaevidence. A sessão
do dono e o atalho principal conservaram seus hashes. O aplicativo permanece
aberto. O ciclo próprio posterior terminou com quatro saídas zero e reabriu
a mesma candidata, restaurando vista e época anteriores, em Júpiter. O novo
`Abrir-Planetas.cmd` abre o app separado da sessão de testes e reutiliza
a janela quando acionado novamente. Recibo `is6-planet-navigation-reopen-20261111a.json`.

O perfil próprio foi preparado em
`is6-planet-navigation-profile-plan-20261111a.json`, com2196fontes seladas.
A receita fixou nove janelas estáticas,30s de aquecimento e60s de medição,
prévia PDH e66amostras por destino. K5A continua recusado; este perfil
pertence à cena ampliada. V1 segue7/21 e IS6 permanece incompleto.

O perfil foi concluído e aceito pelo auditor independente: nove janelas,
40.686intervalos auditados, zero acima100ms, máximo bruto31,0514ms.
Medianas13,291–13,331ms; p95≤14,147ms e p99≤14,637ms. Pico de RAM1,53862GiB
e soma WDDM3,02166GiB. As nove coletasPDH de66amostras cobriram suas
janelas; prévia e contexto passaram. A receita mede vistas estáticas em
1920×1080/100%, com recursos já consultados, relógio pausado e céu ativo.
Entrada ficou inerte durante coleta e foi restaurada. A vista inicial foi
recuperada com o app aberto. Este aceite não cobre partida fria ou camadasK5.
Recibos `is6-planet-navigation-profile[-audit]-20261111a.json`.

O complemento `is6-planet-journey-native-20261111a.json` também passou:
busca dos nove destinos, viagem suave, retorno à pose/época anterior,
cancelamento seguido de visita direta, exportação dos dez corpos e abertura
da ficha selecionada de Netuno com sete propriedades. O teste restaurou a
vista inicial e conservou os arquivos protegidos.
