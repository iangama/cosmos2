# Coleta de residência — protocolo antes dos dados

O novo coletor conserva raízes motor/servidor e seus descendentes com
Toolhelp,GetProcessTimes e handles nativos retidos. Entre amostras,workers
podem nascer/encerrar. Toda saída observada exige códigozero e FILETIME;
reuso dePID,mudança de identidade,órfão vivo ou descendente não resolvido
recusa a coleta inteira. Não atribuir zero a processos sem contadorGPU.

Cada amostra1Hz descobre seus próprios caminhosPDH,conserva metadados e
valores inteiros brutos e repete inventário/caminhos depois de ler. Mudança
dentro dessa amostra é recusa,sem retry que descarte o dado. A auditoria
recalcula bytes,pares dedicado/compartilhado,tempoUTC,ancestralidade eRAM.
As dez janelas têm população/processos estáveis dentro dos seus66registros.

O controlador publica fases identificadas em arquivo atômico. Mudanças de
cena só começam depois do reconhecimento da fase de transição pelo coletor.
Uma amostra atravessando a troca do arquivo é conservada como fronteira;
não serve como amostra estável. Cada janela usa os primeiros66registros
completos da sua fase:três antes do início dos60s e margem posterior.
Registros adicionais e fronteiras permanecem brutos,nunca apagados.

Capturar também os quadros/rastreio das transições e do aquecimento. Somente
a primeira duração da janela estável é excluída dos percentis,retida bruta,
conforme regra anterior. Nas transições,conservar todos os intervalos,
inclusive qualquer duração≥1s;reportar pausas sem alterar limites após
medir. A admissão numérica de quadros16,7/25/50/100ms aplica-se às janelas
estáveis;as transições têm os orçamentos70/750s definidos no contrato e
seus travamentos ficam explícitos como diagnóstico de usabilidade.

Esta medida não é throughput científico nem aceite de toda latência de
interação. O escopo é residência e quadros estáveis com trilha integral
das trocas. O próprio consumo da instrumentação integra a medida.
