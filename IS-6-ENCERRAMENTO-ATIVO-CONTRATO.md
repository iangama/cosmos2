# IS6 — encerramento do aplicativo com vista ativa,02/11/2026

Antes de avançar a jornada integrada,verificar o caminho normal de fechar
a janela com a malha ainda aberta. As provas anteriores fecharam o instrumento
antes do motor; não cobrem esse percurso. A revisão do código identificou
possível propagação de erro nativo no teardown de SpatialLaboratory,
que pode interromper o fechamento dos demais serviços. Ainda é uma hipótese
até executar diagnóstico próprio; preservar0.18.2 e seus aceites restritos.

Host isolado,cópia solar pausada,malha padrão doSol. Registrar osPIDs
app/servidor/descendentes,a fase,o dono,as fontes e a sessão antes de criar.
Confirmar cena ativa. Solicitar shutdown normal do motor,sem leave prévio e
sem matar processos. Esperar até20s pelo encerramento de todos os processos
próprios; registrar quais persistem. Conferir process-result.json do launcher
com app_exit0 e server_exit0. Esse diagnóstico não aceita desempenho/visual.

Se falhar,preservar recibo/logs/fontes e criar revisão própria. Fechamento
de um serviço deve permitir tentar os demais e liberar transportes/processos,
mesmo com renderer indisponível. Distinguir teardown do aplicativo de deixar
uma vista com motor ativo,que continua exigindo restauração confirmada.
Não ocultar falha de remoção enquanto o motor ainda estiver disponível.
Não terminar processos externos nem alterar sessões do dono.
