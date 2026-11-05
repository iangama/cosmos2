# GPU/RAM — identidade em uma fotografia Windows

P1 recusou antes de amostrar; P2 conservou66amostras da terceira janela mas
recusou seu inventário final por NoSuchProcess de um PID ausente do inventário
inicial. As duas janelas estáticas não bastam para aceitar o perfil inteiro.
Não foi identificada a origem daquele PID; não atribuir a falha ao CEF ou produto.
Ambos os hosts fecharam0/0/0/0. Fontes/recibos anteriores permanecem congelados.

O inventário antigo consultava PPIDs sucessivos de todos os processos e depois
materializava a árvore. A revisão usa uma única fotografia Toolhelp de PID/PPID/nome
e confere criação por GetProcessTimes antes de classificar cada descendente.
Um filho mais antigo que o processo atualmente portador do PPID pertence a uma
relação antiga/reutilizada e não entra na árvore nova. Registrar somente PID,
PPID e tempos desses candidatos excluídos, sem nomes de programas alheios.

Após reconhecer um descendente próprio, desaparecimento, troca de identidade ou
erro de acesso recusam o inventário. Candidato que desaparece antes de poder ter
parentesco comprovado também recusa, com diagnóstico de PID/PPID; não ignorá-lo.
Não remover PIDs previamente confirmados para validar uma captura. Os conjuntos
antes/depois, dados GPU e amostras RAM devem concordar por identidade, sem zeros
substitutos. RAM usa a mesma classificação e recusa leitura faltante de qualquer
processo próprio, além da soma de working sets identificada como tal.

Provar CPU: pai/filho válidos, PPID reutilizado, ramos, desaparecimento e ciclo.
Depois, nova prova nativa no modo pausado, nova auditoria e todas as quatro
janelas em nova coleta. Não reciclar amostras de P1/P2 nem relaxar os limites.
