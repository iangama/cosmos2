# Correção do diagnóstico de capturas V

A interpretação inicial registrada em
evidence/is6-import-caption-review-20261104v.json e na revisão C dizia que
PrintWindow havia perdido quase toda a interface. Essa conclusão não é
sustentada pelos pixels dos arquivos e fica revogada por esta correção.
Preservar o recibo, a revisão C e os PNGs originais como histórico.

A comparação RGB entre engine-before e PrintWindow encontra somente quatro
pixels diferentes na imagem inteira. Os retângulos da interface esquerda,
legenda e rodapé têm zero diferenças. Engine-before e engine-after também
têm RGB idêntico, além de PNGs com SHA256 idêntico. Logo, a aparente perda da
interface durante a inspeção não comprova falha do PrintWindow, CEF ou produto.
Não atribuir uma causa à apresentação das imagens sem evidência adicional.

W concluiu a jornada de restauração sem gravações, com dezesseis capturas
nativas, dezesseis verificações de ciência/posição/flags, quinze relações de
equivalência com as imagens S/T e zero mutações de texto em repouso. O PNG
nativo já é RGB. As cópias de inspeção regravadas em RGB preservam exatamente
todos os pixels; isso deve ser verificado e registrado, sem editar os originais.
A geometria da prévia terrestre150% está presente nos pixels, assim como
na prévia100%; a suspeita visual intermediária de ausência não foi confirmada.

A revisão manual final deve inspecionar as dezesseis cópias verificadas e
as duas prévias S/T anteriormente questionadas. O recibo final deve distinguir
os resultados funcionais S/T, as novas capturas W e a correção desta interpretação.
Conservar o escopo: nenhum perfil próprio ou promoção é aceito por essa revisão.
Não alterar ciência ou produto para corrigir uma diferença não comprovada.
