# Próxima expansão: luas principais

Após concluir as verificações próprias da navegação0.24, ampliar o catálogo
com Io501, Europa502, Ganimedes503, Calisto504, Encélado602 e Titã606.
Essa seleção atende às luas jovianas do plano de integração e aos destaques
deC2-16. Este documento fixa trabalho e critérios; não declara dados
adquiridos, luas implementadas ou aceite de desempenho.

As cópias locaisJUP348 eSAT459 foram adquiridas para extrair os centros
planetários599 e699. As receitasSPKMERGE preservadas incluem esses centros
e grupos de satélites irregulares. Não presumir que contêm os segmentos das
seis luas principais. Enumerar os objetos efetivos antes de qualquer extração.
Consultar as fontesJPL e adquirir os kernels adequados com nome, versão,
URL, tamanho, checksum publicado quando houver e SHA256 local registrados.
Downloads e preparação pesada ficam fora das janelas de perfil em curso.

Consulta do índiceNAIF em11/11 identificouJUP365 eSAT441 como fontes para
os seis alvos. Os comentários publicam os respectivos registros e parâmetros:
[JUP365](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/jup365.cmt)
e[SAT441](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat441.cmt).
O[índice e checksums](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/)
serão preservados na aquisição. Ambos os pacotes incorporam segmentosDE440;
esses segmentos devem ficar fora dos recortes usados sobreDE442s.

O estado é geométrico, simultâneo,SSB0/J2000/NONE, em SI. Usar a cadeia
satélite→baricentro do sistema5/6→SSB0 e conservar os centros físicos
planetários existentes. Não substituir o baricentro por599/699 nem carregar
os segmentosDE incorporados nos pacotes de satélites sobre a baseDE442s.
A janela só pode manter1995–2049 se a cobertura real de todos os novos
segmentos a sustentar. Qualquer redução exige registro explícito.

Recortar somente os seis alvos necessários, preservando coeficientes,
referencial, prioridade e comentários. Conferir estados relativos idênticos
bit a bit em201épocas uniformes, limites de segmentos e seus vizinhos
representáveis. Verificar independentemente a soma da cadeiaSSB com limite
1mm por componente de posição e1µm/s de velocidade. Os dez estados já
aceitos precisam conservar igualdade antes/depois de carregar os recortes.

GM deve pertencer ao centro físico e à solução de satélites adotada, com
valor impresso, resolução, unidade e incerteza disponível. Não usar a massa
do sistema como massa do planeta ao acrescentar luas. Forma e rotação vêm
de modelos declarados por corpo; o modeloIAU geral não vira orientação
precisa de missão por associação. Campos magnéticos de Ganimedes, indução,
campo joviano externo e plasma de Io permanecem capacidades distintas.

A API futura deve preservar os dez registros anteriores e acrescentar os
seis novos. Conferir cinco épocas, consultas inválidas sem mutação, exportação,
reabertura em processo novo e restauração do pool de kernels. Comparações
externas precisam identificar a família do modelo na resposta; diferenças
de gerações não recebem tolerância de igualdade do mesmo modelo.

A cena terá uma etapa própria posterior: mapas com procedência e limites,
semieixos/rotações conferidos no renderer, busca/árvore de parentesco,
viagens/favoritos, capturas100/150% revistas e perfil próprio. Preservar a
candidata0.24 e a janela do dono enquanto os dados são preparados. A nova
expansão não altera a recusaK5A nem conclui IS6/v1 automaticamente.
