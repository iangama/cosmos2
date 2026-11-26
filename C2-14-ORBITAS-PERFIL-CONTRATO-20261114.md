# C2-14 — perfil próprio, antes dos dados

Esta receita não autoriza repetir a residência F nem transferir seus números
para a nova bancada. Requer recibos nativo e visual B aceitos, candidata
0.28.1 selada e nenhuma coleta concorrente. Não promove o produto.

Quatro janelas independentes, nesta ordem: órbita excêntrica com operadores
ligados; gráfico de atraso da mesma órbita; gráfico de atraso na intervenção
retilínea com relógio próprio ligado; órbita circular com operadores ligados.
Usar massa nominal de dez massas solares, p = 1.000 raios de Schwarzschild,
e = 0,6 nas três primeiras, oito ciclos e orientação positiva. Referências
visíveis. Círculo usa sua definição analítica e voltas azimutais. Zoom CSS
100%, janela 1.920×1.080, animação ativa durante a janela medida. Recomeçar a
animação ao terminar, sem recalcular ou trocar de job durante a janela.

Em cada janela: completar o worker; verificar configuração, job publicado,
identidade do resultado e fontes; aquecer 30 s; medir 60 s de intervalos reais
do renderizador. Excluir somente as bordas e eventos explicitamente descritos
antes da coleta, sem filtrar travamentos. Registrar todos os dados brutos e
contadores de duplicação/perda. Exigir pelo menos 90% da duração contratada.

Limites por janela: mediana ≤16,7 ms, p95 ≤25 ms, p99 ≤50 ms e zero intervalos
acima de 100 ms. RAM agregada da árvore própria ≤8 GiB e GPU dedicada
agregada ≤5,5 GiB, deixando explícito que são máximos amostrados.

Coletar 66 amostras a 1 Hz, abrangendo a janela de frames. Usar a descoberta
única de caminhos PDH antes do relógio amostral, sem consultar gauges nesse
bootstrap; limite de 10 s. Cada amostra deve durar menos de 1 s e a cadência
deve permanecer entre 0,85 e 1,15 s. Não ignorar a primeira amostra, não
repetir bootstrap e não aceitar uma linha parcialmente medida.

Preservar os contratos nativos já corrigidos: handles retidos, criação e
saída FILETIME, enumeração da árvore com histórico contínuo, RAM por
K32GetProcessMemoryInfo no mesmo handle com testemunhas antes/depois.
Exclusão de processo só quando sua saída antes da leitura está provada;
nenhum zero fictício. Falha de API ou perda de propriedade recusa a coleta.
Todas as amostras devem registrar o job/configuração/resultados completos
da bancada e a vista ativa, em vez de testar apenas o modo Atlas.

Arquivar receita e fontes antes dos dados. Auditoria independente confere
brutos, cobertura, identidades, integridade e limites sem reutilizar o
resultado resumido do coletor. Não executar backup, downloads, pesquisa ou
outro trabalho pesado durante as janelas. Depois do perfil, exigir quatro
saídas 0 e restauração da câmera, época e favoritos do dono. Guardar toda
tentativa recusada, sem modificar critérios após observar os números.

O perfil cobre renderização e residência após cálculo completo. Não mede
latência do solver, lentes fracas, trajetórias gerais no Atlas ou GR dos
dezesseis corpos. Esses escopos não recebem aceite por este ensaio.
