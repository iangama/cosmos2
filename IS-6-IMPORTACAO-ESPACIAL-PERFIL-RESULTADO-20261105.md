# Perfil próprio da importação espacial — 05/11/2026

A candidata 0.22.1 mantém aceite funcional, de reinício e visual E/F, mas seu
perfil próprio permanece recusado/incompleto. Nenhum resultado de versões
anteriores substitui esse aceite. Produto principal 3.13 e atalho preservados.

P1 recusou inventário antes das amostras. P2 concluiu duas janelas estáticas,
mas recusou o inventário final da terceira janela; não aproveitar parcialmente
essas janelas como aceite. A causa dos PIDs ausentes não está estabelecida.

P3 usou fotografia Toolhelp e horários nativos de criação para excluir vínculos
de PPID anteriores ao pai atual. Recusou ainda na preparação, sem janelas:
OpenProcess retornou WinError 87 para PID 1692, pai 39860. O classificador
recusou o candidato sem identidade; não o ignorou. Isso não estabelece quem
encerrou o processo, nem que ele pertencia ao produto. Não houve prévia PDH
pausada em P3. Os quatro processos próprios encerraram com código zero.
O auditor independente v2 confirmou a recusa (zero janelas).

Recibos: evidence/is6-spatial-import-profile-20261105p{1,2,3}.json e auditoria
P3 correspondente. Fontes, planos e arquivos executados permanecem congelados.

Próximo trabalho: nova versão do executor para tratar instabilidade somente
na preparação, com espera limitada e diagnóstico de cada recusa antes de
confirmar cinco inventários iguais. Não ignorar PID sem identidade, relaxar
identidade durante a coleta, alterar limites ou retocar fontes executadas.
Depois preparar plano novo, validar PDH no palco pausado e coletar quatro
janelas completas, seguidas de auditoria independente. Revisar contratos de
identidade/PDH e perfil; não repetir a investigação geral.
