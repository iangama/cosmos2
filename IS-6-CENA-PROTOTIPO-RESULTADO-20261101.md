# IS6 — malha no motor nativo,01/11/2026

Arquivos estáticos ACEITOS em8casos:4corpos×default65/máximo257anéis,
161/353linhas e12545/49601instâncias de vértices. Parser independente conferiu
todos os vértices,topologia,seams,cores e conversãofloat32 prevista. Erro
normalizado previsto máximo3,309e−7Rref,limite2e−6. Não é readbackGPU medido.
Recibo is6-spatial-scene-files-20261101a.json.

Protótipo nativoACEITO4corpos/5capturas/zeroJS,sem falha de cleanup:
is6-spatial-native-20261101a.json. Fonte/escala/arquivo/translação confirmados;
show/hide preservou fase e artefato; nós foram removidos e câmera/flags
restauradas. Tempo de cena pronta6,094–7,125s,limite15s. Host0.17.2 de diagnóstico
encerrou exit0. Nenhum runtime/upstream/produto aceito foi alterado.

Visual de protótipoACEITO por inspeção das5capturas reais em cópiasRGB
exatas: is6-spatial-prototype-visual-20261101a.json. Malha anular/centro excluído,
cores/legendas,época/GM/Rref,altura×200 e ocultação conferidos. Terra/Lua
permanecem quase planas nessa escala,sem inferir grande curvatura. Grade interna
densa fica brilhante pelo blending aditivo; controles e sondas do produto
precisam de experiência e revisão próprias.

Módulo renderer,contrato,verificadores e fontes ligadas ficam congelados.
Este resultado não aceita produto0.18,ponte persistente,journeyCEF100/150%,
camadas simultâneas ou desempenho. Próximo:contratar e construir candidata
isolada com transações de cena,formulário,sondas,persistência e verificações
próprias,sem alterar ciência/artefato/renderer já aceitos.
