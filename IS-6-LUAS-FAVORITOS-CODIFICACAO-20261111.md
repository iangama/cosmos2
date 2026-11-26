# Favoritos entre processos Windows

A primeira troca para0.25.0 abriu a cena de16corpos e terminou os quatro
processos anteriores normalmente. A restauração da vista foi recusada pelo
SHA do arquivo de favoritos. O helper de transferência havia gravadoUTF8;
o servidor lia pela codificação do sistema,CP1252. O arquivo permanecia
íntegro emUTF8. Converter somente sua representação paraJSONASCII preservou
o payload e permitiu restaurar Júpiter sem fechar o aplicativo.

A0.25.1 escreve favoritos explicitamente emUTF8. Ao ler, tentaUTF8 eCP1252,
aceitando uma interpretação apenas quando o SHA do payload confere. Isso
também resolve sequências ambíguas: um arquivoCP1252 pode conter bytes que
formamUTF8 válido, mas representar outro nome. A leitura não regrava o
arquivo; a próxima operação de escrita usaUTF8. O helper novo transfere o
envelope emJSONASCII, compatível com as duas versões.

Cinco fixtures passaram:ASCII, portuguêsCP1252, bytes ambíguos`Ã©`, emoji
e outro alfabeto emUTF8. Os nomes anteriores foram preservados na leitura,
nomes novos com emoji foram escritos emUTF8 e alterações com SHA inválido
foram recusadas sem escrever. Recibo`is6-principal-moons-favorites-20261111a`.

A trocaB para0.25.1 passou com quatro saídas zero e restaurou a vista/época
de Júpiter. A0.25.0 e as recusas da trocaA/nativeA ficam preservadas. O
pacote0.25.1 alterou apenas`moon_navigation.py` e os metadados do perfil em
`planet_scene.json`; a ciência e os recursos visuais permanecem iguais.
