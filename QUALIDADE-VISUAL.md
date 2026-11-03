# C2-03 — contrato de qualidade visual anterior à ampliação

13/10/2026, após a navegação C2-02. Preservar modelos, coordenadas, relógios,
proporções físicas e rótulos de procedência. Não ampliar planetas ou anéis.
Saturno699 e seu elipsoide vêm do recorte SAT441 + PCK; o mapa NASA/JPL anterior é
ficcional e fica preservado como alternativa inativa. Após comparação visual,
usamos mapa2880×1440 do servidor OpenSpace, sem origem observacional/época
confirmadas, identificado como representação visual. Anéis são uma representação visual
com perfil radial de texturas, não uma simulação de partículas ou dinâmica.

Primeiro integrar o RingsComponent já presente no OpenSpace0.22 fixado,
com parâmetros/tamanhos documentados do asset upstream. Adquirir os cinco
perfis fixos da sincronização saturn_textures/v4, preservar manifesto, URLs,
tamanhos e hashes. Crédito do servidor/asset conhecido; origem observacional
dos perfis não confirmada. Não atribuir automaticamente Cassini/NASA nem
transferir licença MIT do código para imagens. Uso local já autorizado;
distribuição permanece fora deste trabalho.

Luz é dirigida pelo Sol na mesma época; sombras planeta→anéis e anéis→globo
devem ser verificadas visualmente e pela configuração/shader, sem alegar
transporte radiativo. Lua sem atmosfera; Terra com modelo de espalhamento
adaptado do upstream e altura/coeficientes identificados. Sombras são efeitos
de renderização. Não introduzir física nova nos experimentos.

Fornecer vistas úteis com composição/polos/terminador e aproximação para os
três mundos, limites do conteúdo e captura acessível. Separar exposição
didática (estrelas visíveis) de exposição de observador calculada: não existe
fotometria aparente nesta etapa. Ajustes de luz/exibição não alteram estados.

Aceite: revisar capturas nativas1080p de Terra/Lua/Saturno, hemisfério claro,
terminador e detalhe; anéis legíveis, oclusão e sombra coerentes, sem saltos
de escala ao aproximar/retornar. UI100/150 e navegação preservadas. Medir três
percursos com intervalos SGCT, p95/p99/pausas>100ms e memória do motor; não
substituir orçamento total já medido em G0 por uma leitura parcial do motor.
Não aprovar apenas por testes ou por haver anéis. Se restar defeito visual,
registrar C2-03 parcial e continuar trabalhando.
