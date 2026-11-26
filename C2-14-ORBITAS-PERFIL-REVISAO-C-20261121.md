# C2-14 — observador nativo com descoberta inicial curta

As tentativas A e B de14/11 permanecem recusadas. A tentativa B não coletou
gauges: o maior intervalo do observador foi0,2690311s, acima de0,25s. Os
nascimentos arquivados mostram cerca de200ms gastos na descoberta inicial.
A chamada adicional de psutil para ler a linha de comando de cada processo
é uma hipótese para esse custo, a verificar com a revisão nova.

O observador v2 conserva Toolhelp, handles retidos, caminho da imagem,
FILETIME de criação e saída, ascendência temporal, WaitForSingleObject,
recusa de desconhecidos, órfãos, reuso e saída diferente de zero. A identidade
é obtida das APIs nativas no próprio handle. Não consulta linhas de comando
no caminho de alta frequência; o host continua verificando as linhas de
comando das raízes e dos lançadores antes de reter seus quatro handles.
O campo opcional command_line fica explicitamente nulo. Não simular falha
de psutil nem alegar que essa informação foi medida.

Cada poll recebe um registro bruto separado: início/fim FILETIME, duração,
intervalo entre inícios e número sequencial. A inicialização também conta.
Não reiniciar o máximo, descartar polls ou relaxar0,25s. O auditor recalcula
o máximo pelo arquivo bruto e confere cobertura da inicialização até a
última amostra. O custo do observador permanece dentro do perfil.

Antes de selar novo perfil, verificar fixtures Windows com nascimento e
saída0, saída7 deliberadamente recusada, leitura RAM no handle retido e
cadência bruta. Fazer um diagnóstico curto de descoberta PDH na sessão
atual, sem gauges nem aceite de desempenho. Não repetir A/B ou residênciaF.

O produto científico0.28.2 e os critérios de frames, memória, cadência,
identidade de job, animação, quatro janelas e encerramento permanecem.
O novo host deve salvar a fase atual pelo botão, preservar arquivos,
encerrar normalmente, executar a candidata separada e reabrir o lançador
original selecionado, restaurando fase, câmera, época e favoritos.
