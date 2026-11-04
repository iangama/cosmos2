# Abertura da interface local — correção em validação

O dono relatou uma página branca com127.0.0.1 e ERR_CONNECTION_REFUSED.
O carregador anterior abre o servidor HTTP e o motor em paralelo; o bootstrap
aguarda a cena3D e navega sem conferir se o HTTP já está atendendo. Essa ordem
permite a navegação prematura. O print não identifica o instante/processo de
cada ocorrência; não se atribui uma causa única a todas as falhas anteriores.

O novo helper espera /health com aplicação/protocolo corretos e a página
Cosmos2. O processo dono deve continuar vivo, com limite de espera e erro claro.
O novo carregador Python da candidata0.21.1 só abre o motor após essa resposta;
o bootstrap também confirma HTTP antes de navegar. Não há recarga periódica
capaz de interferir na navegação posterior do dono.

Sete provas passaram: escuta atrasada, serviço errado, protocolo booleano,
página ainda incompleta, processo encerrado, encerramento após health e
resposta pronta. A primeira versão do verificador exigia vários retries TCP;
no Windows uma única tentativa pode atravessar a abertura atrasada da porta.
O verificador V2 conserva a exigência de esperar o serviço, sem contar retries.
O código de prontidão não foi relaxado.

Na abertura nativa B da candidata, o helper esperou15,625s antes de iniciar o
motor. O Atlas carregou sem navegação/reload manual; a captura nativa foi revista.
O processo pai arquivou saída0/0 de app/servidor. B inicialmente recusou apenas
porque psutil já não recuperava o código do servidor recolhido pelo pai; a
auditoria B-r2 consulta o registro dos próprios handles e mantém B intacto.
Essa duração observada não é um perfil de desempenho de inicialização.

O teste do atalho instalado encontrou novos processos PowerShell suspensos
antes de executar código, com uma thread e CPUzero. A origem da suspensão é
desconhecida. Uma tentativa de retomar o parser próprio não resolveu e não foi
repetida; somente os três processos de teste identificados foram limpos.
Nenhuma política de segurança foi alterada. A pergunta ao dono sobre pausa
externa ou aviso de segurança ficou pendente. O atalho original continua
preservado; start-cosmos2-v2.ps1 está preparado, sem ativação antecipada.

Provas: evidence/local-ui-readiness-check-20261104.json,
local-ui-native-startup-20261104b-r2.json e
local-ui-powershell-stopped-20261104.json. Código científico, dados do dono e
instalação3.13 permanecem intactos. O perfil K5 próprio continua pendente;
seu coletor GPU também depende do PowerShell.
