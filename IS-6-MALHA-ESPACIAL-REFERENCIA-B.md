# IS6 — guarda numérica do avaliador independente

01/11/2026, após tentativaA, antes da execuçãoB. Modelo, contrato científico,
fixtures e verificadorA ficam preservados. Não alterar tolerâncias de produção.

A parou no controle de vácuo do próprio tensor, com u≈1e−18. Os13testes
numéricos anteriores passaram, incluindo K por Riemann com erro5,38e−17.
O resíduo ortonormal de Ricci do avaliador foi2,124e−94 em80dps;100dps deram
1,671e−114,120dps8,410e−135 e160dps1,791e−174. A queda com precisão identifica
cancelamento na referência; o limite original1e−50×Rs/r³ é mantido.

B mantém saídas/comparações80dps e usa120dps internos somente na construção
independente de Christoffel/Riemann, arredondando depois para80dps. São40dígitos
de guarda, sem compartilhar a fórmulaK da produção e sem afrouxar erro.
Registrar ambas as precisões no recibo. A referência de quadratura permanece
80dps. Comparar a saída do tensor80+40 com avaliação160dps adicional no estado
de campo mais fraco antes de aceitar o controle.

Corrigir também a métrica do teste de inversão de rotação antes de executarB:
o contrato limita erro relativo de vetores/distâncias, não erro relativo de
cada componente quase nula. Medir norma do erro vetorial dividida pela norma
do vetor original, com o mesmo limite3e−13. Esse grupo não foi alcançado emA;
nenhum limite é escolhido após observar seus resultados.
