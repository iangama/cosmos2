# C2-14 — preparação de órbitas, precessão e tempo próprio

A residência F foi aceita; não repetir o ensaio. Esta preparação inicia a
próxima entrega autorizada, sem solver novo, contrato aceito ou dados novos.
Preservar a candidata científica0.27.0 e os seus atalhos.

O módulo app/relativity.py existente trata raios nulos Schwarzschild e
relógios estáticos. A seção C2-14 do ROADMAP-GERAL.md ainda exige órbitas e
precessão, observador/tempo próprio e comparação quantitativa Newton/GR.

Primeira fonte primária consultada: [Sean Carroll, seção7 das notas de GR](https://ned.ipac.caltech.edu/level5/March01/Carroll3/Carroll7.html),
principalmente a derivação geodésica e o potencial efetivo, as órbitas de
partículas massivas e a precessão discutida em torno das equações7.44–7.56.
O texto distingue órbitas nulas e massivas e relaciona a precessão às órbitas
ligadas não circulares. As fórmulas dessa página aparecem como imagens;
a transcrição matemática ainda precisa ser conferida na versão original.

Recorte a fixar no contrato: partícula-teste no exterior de uma massa
esférica estática, sem rotação/carga e sem realimentação nos16corpos.
Distinguir raio areal, tempo coordenado, tempo próprio e observador local.
A comparação Newton/GR precisa de uma regra explícita para o mesmo estado
inicial; não equiparar tangentes coordenadas e velocidades locais sem conversão.

Próximo exato: recuperar as equações originais, escolher regime/condições
iniciais e referência independente para precessão e tempo próprio; depois
fixar tolerâncias, refinamento, invariantes, domínios inválidos e orçamento
ANTES de implementar ou medir. Não usar o valor de precessão total de Mercúrio
como se representasse apenas a contribuição esférica relativística.
Nenhuma destas escolhas numéricas foi concluída nesta preparação.
