# Curadoria do caminho real — reprodução e correção preparada

Após o print do dono, a preferência foi registrada permanentemente nos AGENTS.md do dono e deste projeto: validar pelos atalhos e botões reais, com mouse/teclado, clareza e recuperação, sem confundir candidata isolada com entrega acessível.

O ensaio original-forces-user-flow-20261114b usou o CEF nativo da versão 0.27 aberta: clicou em Voltar ao Atlas, depois no botão Forças fundamentais do cabeçalho, registrou a falha e retornou pelo link visível. Não navegou por URL direta nem injetou comandos de abertura. A captura original de 1.920×1.080 confirma bancada vazia, zero cenários, zero parâmetros, “Failed to fetch” e Aplicar condições ainda habilitado.

O log do servidor confirma imports de forces.py/science_contracts.py da pasta is5-compression-product0.17.2 e ausência de ame2020-mass-original.txt nesse namespace. A causa é o desvio de imports após módulos legados alterarem sys.path, junto da falta dos dados no namespace carregado. Não é falha do solver de órbitas C2-14.

Também foi constatado que Voltar ao Atlas só retorna à página inicial: o backend permaneceu em experiment. O rótulo não descreve o destino real. Câmera, época e favoritos foram preservados; a única diferença no JSON físico foi history_evaluation_ms, uma duração de avaliação, sem mudança dos estados científicos. A primeira tentativa de reprodução, que supunha modo Atlas, fica preservada como incompleta.

A correção está preparada em output/original-forces-hotfix-staging, derivada da 0.27. Os 137 módulos Python científicos permanecem byte idênticos. O servidor fixa forces/science_contracts/artifacts locais antes dos imports legados, fornece data/science próprio e mantém exportações privadas. A interface propõe carregamento explícito, bloqueio de ações enquanto indisponível, mensagem compreensível, Tentar novamente e retorno rotulado Voltar ao simulador. A configuração concluída é clonada para não compartilhar o objeto em edição.

O JavaScript passou na verificação de sintaxe. Um servidor separado passou no catálogo de 12 cenários e nos cálculos padrão de gravidade, forte, fraca e luz/relógios; encerrou com código 0. Recibo original-forces-hotfix-http-20261114a. Isso aceita apenas esse ensaio HTTP.

A correção NÃO foi instalada na versão aberta, NÃO tem aceite do fluxo nativo corrigido e NÃO resolve por si só a revisão de todos os botões. Próximo: empacotar uma revisão separada, preservar o experimento pausado existente, testar o acesso pelo botão original, controles, recuperação/retry e retorno, em 100/150%. Conferir também o mapa geomagnético e o asset local earth.jpg, pois o rascunho copiou apenas data/science. Revisar a coerência dos atalhos Iniciar-Cosmos2, Abrir-Planetas e Abrir-Planetas-e-Luas, que apontam para versões diferentes.

Os perfis C2-14 A e B estão recusados; B não iniciou amostras por gap de observação nativa de 0,2690311 s, acima de 0,25 s. Ambos encerraram e restauraram suas sessões. Investigar isso somente após o fluxo de uso. Nenhuma fonte ou tentativa aceita anterior foi alterada.

Atualização posterior: após constatar que os 12 módulos científicos declarados eram byte idênticos, foram adicionadas 96 dependências ausentes nos namespaces legados 0.17.2 e 0.27 (dados científicos e earth.jpg), sem sobrescrever arquivos existentes nem mudar código. Recibo original-forces-dependency-repair-20261114a. Esse reparo chega ao caminho original; o rascunho de UX ainda não foi instalado. Em seguida, o dono explicitou que está testando manualmente e que a reorganização em painel unificado é futura: não manipular a sessão enquanto ele testa.

Continuidade em 20/11: a revisão separada `output/original-flow-hotfix-staging-v2`
inclui a textura da Terra e correções dos painéis existentes. Foram reproduzidas
16 falhas em 22 verificações isoladas; a revisão passou nas 22, em quatro
verificações de layout com escala real e em 14 verificações HTTP. Os 137
módulos científicos permanecem iguais. Fontes, limites, tentativas substituídas
e próxima validação estão em [CURADORIA-MALHA-CAMADAS-REVISAO-20261120.md](CURADORIA-MALHA-CAMADAS-REVISAO-20261120.md).
Não foi instalada nem aceita pelo percurso nativo. A restrição dos testes
manuais e a pendência da integração final permanecem vigentes.
