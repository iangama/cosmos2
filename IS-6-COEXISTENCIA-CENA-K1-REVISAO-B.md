# K1B — posição relativa à origem do laboratório

K1A recusou a preparação oculta antes de mostrar qualquer par. O verificador
comparou worldPosition com a posição localGALACTIC,mas LabRoot tem translação
gráfica [1e14,0,0] no runtime. O campo e a imersão usam coordenadas locais.
As fontesA e seu recibo permanecem congelados.

K1B confere a translação local do centro com erro≤1mm e a posição do ponto
relativa ao centro:worldPosition(ponto)−worldPosition(centro),comparadaà
rotação declarada aplicada ao vetorSI. Guarda ambos os valores brutos.
A subtração de origens grandes usa limite ulp(ponto)+ulp(centro)+1mm por
componente,conforme o verificador corporal já aceito. Não somar a translação
gráfica à fonte científica. Demais parâmetros e roteiro não mudam.

Novo módulo is6_layer_scene_v2.py,verificadorv2,driver11,label20261102b.
Sem novo aceite antecipado. Fonte de referência do diagnóstico:
app/laboratory.py da0.18.5,criaçãoLabRoot, e
scripts/verify-native-body-field-prototype.py,conferência de diferençasworld.
