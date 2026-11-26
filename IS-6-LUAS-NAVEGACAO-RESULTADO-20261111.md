# Seis novas luas na cena0.25.1

Io, Europa, Ganimedes, Calisto, Encélado e Titã estão implementados na cena
com os oito planetas e a Lua. O catálogo contém16centros físicos;15são
destinos navegáveis. O Sol conserva iluminação e consulta de dados.
Busca, árvore de parentesco, fichas e catálogo foram ampliados. A candidata
permanece isolada e sem promoção.

O teste nativoB passou nas cinco épocas do contrato:80posições e75rotações.
O erro máximo de posição foi0,48828125mm, com orçamento max(1mm,8ULP).
O erro por elemento das rotações chegou a1,1102230246251565e−16, abaixo de
1e−12. Os45semieixos foram recuperados da altitude geodética no próprio
renderer, com erro máximo0,367477536mm e limite2cm. Os seis arquivos de
textura usados no motor correspondem aos mapas fixados por SHA256.

O percurso visitou15destinos, aplicou quatro vistas a cada lua nova e
testou favoritos, seguir rotação, voo livre, deslocamento, relógio e quatro
recusas de época sem mutação. As cópias anteriores de três/quatro corpos
continuaram funcionando no laboratório separado. A sessão protegida e o
atalho principal conservaram seus hashes; a vista inicial foi restaurada.

As12capturas nativas das seis luas em100/150% foram inspecionadas, sem
edição de pixels. Fichas, maior semieixo, fontes, limites dos mapas e
rolagem permaneceram legíveis. Titã usa um mosaico fixo, sem atmosfera
dinâmica ou calibração fotométrica. Dados observacionais não confirmados
permanecem desconhecidos na interface.

A0.25.0 abriu a cena mas teve recusa na transferência do favorito entre
UTF8 eCP1252. A primeira verificação nativa parou antes dos casos. A0.25.1
fixou a codificação com compatibilidade verificada; trocaB terminou com
quatro saídas zero do host anterior e restauração de Júpiter. As fontes
anteriores e recusas continuam preservadas.

Recibos nativo/visual:`is6-principal-moons-navigation-native-20261111b.json`
e`is6-principal-moons-navigation-visual-20261111b.json`. Os dadosCPU e a
comparação externa são descritos emIS-6-LUAS-DADOS-RESULTADO-20261111.md e
IS-6-LUAS-HORIZONS-TEMPO-20261111.md.

O perfil próprio de15janelas terminou e foi aceito pelo auditor20261111a:
67.798intervalos, nenhum acima de100ms, maior p95 de14,489ms e maior p99
de15,039ms. O pico de RAM foi1,603GiB e o de memória dedicada+compartilhada
WDDM foi3,041GiB. As2270fontes seladas e os registros brutos permanecem
preservados. O aceite cobre vistas gerais estáticas com recursos já
consultados; não cobre partida fria ou múltiplas camadas.

A jornada complementar20261111a passou busca dos15destinos, árvore das
seis luas novas, filtro das sete luas, voo suave com retorno, cancelamento,
fichas e exportação dos16corpos. A página do catálogo passou consulta2000,
recusa1994 sem trocar o estado confirmado, exportação e erros HTTP. Suas
duas capturas em100/150% foram inspecionadas diretamente em12/11UTC, sem
edição; o recibo visual éis6-principal-moons-catalog-visual-20261112a.json.

A reabertura20261111a terminou os quatro processos anteriores com código
zero e abriu a0.25.1 pelo novoAbrir-Planetas-e-Luas.cmd. Repetir o atalho
reutilizou a janela. O atalho anterior0.24 eIniciar-Cosmos2.cmd continuam
preservados. O backup parcial de fontes/evidênciasv13 tem5092arquivos e
commit LOCAL18702c03f1df278733b8e6ecb92c17f20abbf8da; nenhum push.

Recibos adicionais: is6-principal-moons-navigation-profile-audit-20261111a,
is6-principal-moons-journey-native-20261111a,
is6-principal-moons-catalog-native-20261111a e
is6-principal-moons-navigation-reopen-20261111a, todos em evidence/*.json.
O driver local terminou suas cinco etapas com código zero. A janela segue
aberta. K5A permanece recusado; V1 segue7/21 e IS6 permanece incompleto.

O próximo passo autorizado é verificar o percurso e a persistência das
camadas gravitacional/magnética na cena ampliada, com contrato e registros
próprios antes de medir desempenho composto. Não repetir o perfil estático.
