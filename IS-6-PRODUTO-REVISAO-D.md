# IS6 — encerramento0.18.3,02/11/2026

0.18.2 permanece imutável com perfilC aceito(18016quadros/272sondas),provas
funcionais/visuais e diagnósticosA/B recusados. Encerramento ativoA confirmou:
app_exit0/server_exit1,todos osPIDs terminaram em3,688s. O traceback mostra
ConnectionClosedError na tentativa de restaurar câmera depois que o motor
já encerrou. Não houve processo persistente,nem alteração da sessão do dono.

Criar0.18.3: somente servidor e serviço espacial mudam. Durante teardown
interno,indisponibilidade do transporte nativo é registrada explicitamente,
sem impedir o fechamento dos demais serviços. Deixar a vista pelo comando
público continua exigindo confirmação e mantém suas falhas. Nenhuma leitura
de câmera é anunciada como restaurada quando o motor já está indisponível.
Sempre esperar o término da thread; servidor tenta fechar todos os serviços,
mesmo se algum deles falhar,e reporta outras falhas reais de encerramento.

Reservar _close ao chamador interno; o endpoint público deve recusá-lo antes
de admitir uma ação. Caso contrário um comando sem guard poderia encerrar a
thread e deixar chamadas seguintes esperando indefinidamente. Provar recusa
sem mutação e serviço ainda funcional. Sem mudanças de ciência/renderer/UI.

Antes de aceitar: conferência de apenas2arquivos diferentes,regressão própria
do serviço e diagnóstico nativo de janela fechada com malha ativa,app/server0,
PIDs encerrados em20s e dono intacto. Provas0.18.2 conservam seus escopos;
não chamar o perfil antigo de uma execução0.18.3 nem promover a instalação.
