# IS-2 — invariância da dinâmica sob mudança de origem

Receita prévia: utilizar a condição canônica salva na série auditada B, sem
alterar arquivos de sessão. Evoluir IAS15 epsilon10⁻⁹ no mesmo modelo
newtoniano pontual durante30dias,121saídas a cada6h. Executar três percursos:
original, transladado por `[2e11,-3e11,1e11]` m e transladado com velocidade
comum `[1234,-5678,910]` m/s. Nunca recentrar as partículas durante o ensaio.

Para cada instante, remover analiticamente a translação e a velocidade
comuns e comparar todos os componentes de posição e velocidade com o
percurso original. Limites prévios:10m e10⁻⁵m/s, os mesmos limites numéricos
de concordância da fatia IS-2. Conferir ainda diferenças de separação por
par após a transformação. Este teste mede simetria do modelo newtoniano
reduzido dentro do arredondamento; não valida invariância relativística ou
precisão observacional. Fixar fontes e hashes antes de evoluir e guardar
todas as séries. Nenhuma evidência antiga será reescrita.
