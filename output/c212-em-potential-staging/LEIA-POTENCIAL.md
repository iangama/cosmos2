# Próxima fatia de C2-12: equipotenciais

Protótipo geométrico separado, sem UI/aceite nativo. A prova geométrica isolada passou (em-potential-check.json). Usa valores SI já medidos,
em um corte cartesiano declarado, com triangulação linear00→11. Segmentos
não atravessam triângulos com amostra inválida. Região toda no mesmo nível
tem contagem própria, sem linhas arbitrárias. Limites de trabalho explícitos.
Nenhuma altura gráfica é tratada como potencial físico; o volume3D continua.

Campos lineares (resíduo0), Coulomb± comrefinamento7→65(errodemáximoraio
0.1418→0.001802m,raio1m), regiõesconstantes, orçamento e potenciais±1e308 passaram.
Primeiratentativa49×49nãoatingiu0.003m;65×65atingiu semrelaxartolerância.
Caixasdecélulasquetocamesferasdeexclusão sãoomitidas conservadoramente,
incluindofontesinteirasentrevérticesválidos. Testar superposição/worker antesdeintegrar.
Amostragem65×65 exige lotes pausados≤128 com o MESMOsystem/token/revisão/tempo;
se qualquer lote divergir, descartar a camada completa. Não ampliar limite do
worker silenciosamente. Cada camada guarda grade/fontes/geração/instante e
hash do algoritmo. Gauge atual: Coulomb∞ e contribuição uniforme−E·x.

Integração posterior em candidata própria: botão de potencial independente de
E/B e atuação, legenda emV, sonda/exporte, congelamento, seleção e persistência.
Se a configuração do editor científico mudar, nova geração e migração explícita.
Perfis128 da0.4 sem equipotenciais não aprovam esse novo custo de cena.

O protocolo em_slice.py passou no worker real: 289 pontos em lotes128+128+33,
15ms no preset elétrico e32ms no Coulomb nesta prova. Dez recusas (tempo,
revisão, frame, sistema, token, ordem, contagem, estado em evolução e orçamento)
impedem publicar uma camada parcial. Ver em-potential-worker-check.json.
Esses tempos não medem128fontes/65×65, cena nativa ou perfil formal.
