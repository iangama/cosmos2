# Instrumentos orbitais — versão3.11

Implementação local de16/10/2026, com perfil de desempenho próprio128 aprovado. Este instrumento mede a fase confirmada de três massas selecionadas;
não aplica força adicional. O simulador continua integrando suas interações
newtonianas, ou as hipóteses físicas explicitamente configuradas na sessão.

Para um primário e dois orbitadores, os elementos osculantes são relativos ao
mesmo primário explícito. O plano inercial tem normal e direção de referência
fixas. Pode ser preenchido a partir da órbita interna no instante preparado.
O domínio atual é plano e prógrado; trajetórias radiais, retrógradas, não ligadas,
fora desse plano ou com ordenação interna/externa invertida ficam indisponíveis
com motivo. O instrumento não troca identidades automaticamente. Periastro
quase circular fica indefinido, embora a longitude média tenha limite estável.

Para primeira ordem j:(j−1), j de2 a9, os ângulos críticos são
θᵢ=jλexterno−(j−1)λinterno−ϖᵢ. A interface mostra −180° a180° e interrompe o
traço nas passagens do limite, lacunas e mudanças de definição. Não desempacota
amostras esparsas nem classifica libração automaticamente. Razão de períodos
próxima de uma comensurabilidade não prova ressonância; uma janela limitada não
prova captura permanente. Centros assimétricos são possíveis.

A captura tem cadência real de0,25 a5s e janela de128 registros, independente
das sondas gravitacionais. Cada leitura preserva instante, referencial, revisão,
configuração, geração científica, hipóteses de força e fase SI dos três corpos
selecionados; também guarda as identidades ativas. Essa fase selecionada não é
um replay de toda a trajetória global. Consultar um ponto usa o registro original.
Exportação SI, arquivos e ramos preservam as definições e os instantes reais.
Remover um corpo produz lacuna; outro corpo no mesmo índice não o substitui.

Os cenários 2:1 e1,8 são sintéticos, com três massas ativas, condições iniciais
seladas e nenhuma procedência observacional atribuída. O cenário2:1 foi medido
isoladamente por500 períodos externos: amplitude total0,602570rad, erro relativo
de energia4,441e-15 e de momento angular2,153e-15. O controle1,8 circulou94,021
voltas. Esses resultados descrevem esse intervalo e essa amostragem. A contagem
de inversões locais contém oscilações rápidas e não conta ciclos lentos.

A validação dos elementos compara240 casos com o REBOUND5.2.2: longitude
média≤1,333e-14rad e periastro≤3,997e-15rad. Uma construção Kepler independente
concorda a2,221e-14rad. O oráculo Newtoniano independente DOP853 cobriu20
períodos externos; seus refinamentos convergiram e a diferença IAS15 foi
≤1,887e-12, com ângulos≤6,111e-13rad. Não houve oráculo independente500períodos.

Session passou26 comandos inválidos/obsoletos e32 corrupções seladas recusadas.
Leituras e gravação mantêm o binário do mesmo integrador exato, fase idêntica
ao controle sem captura, retomada futura e ramos exatos. Worker passou6leituras,
20pausas≤1,373ms e stderr vazio. Jornada CEF real passou presets/formulários,
gráfico/consulta original/exportaçãoSI/save/load/ramos com definições distintas,
sem errosJS. Treze arquivos reais, incluindo3.10 com material e o legado do dono,
migraram e retomaram exatamente sem ativar captura orbital ou alterar originais.

Recibos em evidence/resonant-{angles,dynamics,oracle}-prototype-check.json,
resonance-{session-installed,worker-installed,ui,migration}-check.json.
Capturas cosmos2-resonance-{angles,branches}.png revistas visualmente.
Fontes e convenções primárias: [Beaugé etal.2003](https://arxiv.org/abs/astro-ph/0210577)
e [Goldreich eSchlichting2014v2](https://arxiv.org/abs/1308.4688v2).
Derivação e escopo em output/c211-resonances-staging/LEIA-RESSONANCIAS.md.
C2-11 permanece parcial: perfil desta versão e populações256/10mil pendentes.

Perfil c211orbital1:3×60s após30s de aquecimento,1920×1080,128 massas ativas,
16sondas e captura orbital independente a0,25s, duas janelas de128registros,
gráfico orbital visível. P95≤18,910ms/p99≤21,111ms/zeroquadros>100ms,
ritmo≥0,9980478 para1 solicitado e20pausas≤52,733ms. RAMsoma1,07776GiB,
WDDMsoma2,99869GiB eDXGIbudget7,19014GiB; somas podem repetir páginas/alocações
compartilhadas. Auditoria conferiu fontes atuais exatas antes da versão3.12.
ArchiveSHA2959e24cefcd65bf49fc51a2684c567662aad52f1648a6ebde7d0ca8ec53ba00,
backupoutput/c211-resonances-validated/app. Reciboc211-resonances-validated.json.
Números não representam256 massas ou10mil partículas.
