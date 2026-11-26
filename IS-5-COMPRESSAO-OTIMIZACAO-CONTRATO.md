# IS5 — representação térmica das derivadas,29/10/2026

Preparação numérica separada,sem mudar física ou fontes aceitas. Preservar
EOS,wrappercross e solver completo como referências. A evolução comum precisa
deF,gradiente e apenas a linha térmica da Hessiana; não usa a matriz inteira
de segundas derivadas em todas as abundâncias. A representação atual calcula
essas entradas adicionais e confere gerações/recibos em cada avaliação.

Novo estágio is5-compression-fast-staging,sem editar os anteriores. Jet
térmico guarda valor,gradiente completo e H[lnT,:]. Propagar exatamente essa
linha pelas mesmas operações e funções analíticas. Herança do Jet anterior
serve somente à identificação dos ramos de fits; não expor uma Hessiana
completa inexistente. As mesmas funções de energia livre e os mesmos guardas
de estado/composição são importados,sem aproximar taxas ou usarfloat32.

API numérica interna continua validando todos os estados. Gerações/fontes
ficam conferidas antes e depois de uma integração completa,como no solver
isocórico aceito; não publicar resultado se qualquer fonte tiver mudado.
API pública de avaliação mantém conferência de geração. Sem monkeypatch dos
módulos aceitos ou remoção de guardas para obter velocidade.

Aceite do avaliador:12fixturescross aceitas e amostras interiores das
trajetórias completas quando a evolução B for aceita. Conferir P/U/Cv,
gradientes de energia emY e potenciais químicos de cada componente,além de
P_T eU_lnρ. Erro relativo≤5e−12; pisos de escala1e−12n_bk_BT para densidades
de energia/pressão,1e−12n_bk_B para capacidades/derivadas emT e1e−12k_BT para
potenciais químicos. Nenhum termo ou traço é descartado.

Somente após evolução lenta aceita,verificar evolução otimizada contra os
arquivos completos de Radau/BDF/refinamento e os quatro controles aceitos,
sem reintegrar as referências. Exigir Yabsoluto≤1e−10,Trelativo≤1e−9 e
erroW/E0≤1e−9,além dos mesmos balanços/guardas. Exercitar novamente uma recusa
de trajetória que cruza o domínio. Guardar fontes e hashes das referências.

Medir duração sem outros testesCPU concorrentes. Meta operacional do caso
de compressão padrão≤60s,contra≈172s da implementação de referência neste
hardware. Registrar separadamente aceite numérico e atingimento da meta;
não enfraquecer tolerâncias ou eliminar amostras para atingir velocidade.
Sem aceite automático de trabalhador,produto ou desempenho de quadros.
