# IS-4 — primeira vista nativa ampliada da trajetória

A cena de laboratório usa uma translação de 1e14 m. Nesse deslocamento, uma
trajetória de elétron desenhada na escala física perderia pequenos movimentos
no arredondamento global. Usar uma ampliação local explícita: origem no
ponto de lançamento, eixos do modelo congelados e uma unidade física L
mapeada a 1e7 m de desenho. L é o raio de giro inicial quando aplicável;
para q=0, usar uma escala cinemática declarada. O painel mostra L em SI e
identifica a vista como ampliada. Não interpretar o tamanho desenhado como
uma distância astronômica ou tamanho físico da partícula.

O marcador usa o deslocamento científico dividido por L. A trilha conserva
até 129 amostras reais do worker e seus tempos, com a última fase igual ao
marcador. A matriz é modelo→J2000→render já adotada. Arquivar pacote, origem,
escalas, vértices e hashes. Erro float32 mais limite conservador do quadro
global, convertido de volta para SI, deve ser ≤1e−6 de max(L, extensão local).
Recusar identidades, matrizes, componentes, sequência, tempos e origens
incoerentes antes de preparar arquivos. Nenhuma força é calculada na vista.

Primeiro aceite: geometria e cena PAUSADAS. Exigir readback das coordenadas
locais do marcador, CPU ociosa e quadros reais posteriores; capturas100/150
revistas, limpeza e restauração da câmera/visibilidade. O host0.7.1 e sua
fase orbital permanecem intactos. Usar worker/storage próprios e runtimeV2.
Essa prova não confirma upload GPU por quadro durante evolução. Ponte ao
vivo, UI de produto e perfil próprio são próximas etapas.
