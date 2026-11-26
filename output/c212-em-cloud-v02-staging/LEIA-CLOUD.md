# Próximo recorte: 10 mil partículas de teste EM

Protótipo separado; código ainda sem prova. Arrays SI imutáveis e Boris
sincronizado, cargas/massas individuais e campos estáticos prescritos. Nenhuma
reação sobre fontes ou entre partículas de teste. Sem PIC, radiação, indução ou
órbitas atômicas reais. Domínio de componentes de posições/fontes até1e17m e
velocidades até0,01c. Falha em qualquer partícula recusa o passo coletivo inteiro.

Não rodar testes CPU durante perfil nativo das equipotenciais. Depois comparar
campos contra avaliador escalar0.4 e referência independente, passos contra
Boris escalar,10períodos analíticos e refinamento, exclusões/limites/imutabilidade,
trabalho elétrico eBsem aquecimento; então medir throughput isolado de10mil.
Ainda faltam checkpoint próprio, worker, UI e aceite nativo do perfil.

O transporte nativo atualC2CLD002 aceita SOMENTE massless_central_ias15_v1 e
length_unit_m=1e9; não passar EM fingindo gravidade. Próxima extensão precisa de
binding/modelo/tempo SI explícitos e um runtime candidato separado, mantendo
.runtime-cloud instalado e seus hashes. Mesmo GPUbuffer pode ser avaliado por
mérito, mas a semântica e a validação do pacote precisam mudar explicitamente.
