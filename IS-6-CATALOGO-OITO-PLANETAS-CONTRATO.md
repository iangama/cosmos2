# Catálogo dos oito planetas

## Recorte autorizado

A expansão do IS6 começa pelo cadastro geométrico de Sol, oito planetas e
Lua. Cada planeta usa seu centro físico NAIF199/299/399/499/599/699/799/899.
O catálogo preserva a distinção entre esses centros e os baricentros dos
sistemas. Os contratos e as gerações da dinâmica de quatro corpos e de seus
leitores servem de base para as verificações de compatibilidade.

O perfil composto K5A continua recusado. Seu diagnóstico instrumentado de
10/11 completou13.553intervalos, com máximo27,212501ms, zero longtasksCEF,
fontes verificadas e quatro saídas zero. A pausa original ficou sem
reprodução. A ampliação de dados avança como trabalho independente já
previsto no PLANO-INTEGRACAO-SISTEMA-SOLAR.md.

## Dados e cobertura

DE442s fornece a cadeia SSB dos sistemas. Reutilizar seus estados originais
de Sol, Mercúrio, Vênus, Terra e Lua, o subconjunto599/5 deJUP365 já aceito e
o subconjunto699/6 deSAT441 já usado pelo Atlas. Adquirir MAR099s para499/4,
URA182 para799/7 eNEP097 para899/8. Guardar URLs, bytes, hashes e comentários.
Conferir os MD5 publicados quando a fonte os fornecer.

Os kernels de satélites contêm também segmentos planetários de outros
modelos. Extrair somente os centros físicos e a cobertura solicitada com
CSPICE spksub, conservando os registros polinomiais originais. A autoridade
SSB permanece DE442s. Isso define uma cadeia geométrica mista declarada.
Cada origem fica vinculada ao segmento utilizado e seu modelo original.

A primeira janela comum da aplicação é
01/01/1995 00h UTC–30/12/2049 23h59min59s UTC. Medir a interseção dos
segmentos de cada elo antes de aceitar essa janela. As consultas usam
J2000/ICRF, centroSSB0, correçãoNONE, metros e metros por segundo. UTC é
convertido comnaif0012, mantendo sua política de segundos intercalares.

Semieixos vêm dePCK00011 e a orientação usa seus modelosIAU gerais.
ParâmetrosGM devem identificar o corpo físico, texto original, resolução e
origem. Incerteza ausente recebe valor desconhecido e motivo. Capacidades
magnéticas e nucleares dependem dos modelos registrados de cada corpo.

## Verificações previamente fixadas

Comparar os subconjuntos aos kernels completos em201épocas uniformes da
janela e em cada fronteira de segmento que caia nela, incluindo os pontos
imediatamente vizinhos. Exigir igualdade binária dos seis componentes de
cada estado relativo. Conferir a cadeia SSB por soma independente dos dois
vetores, com diferenças máximas de1mm em posição e1µm/s em velocidade.
O carregamento dos subconjuntos deve conservar bit a bit os estados antigos
deSol/Terra/Lua e dos baricentros consultados noDE442s.

Validar finitude, unidades, centros, época, orientação ortonormal, forma,
procedência e cobertura. Recusar booleanos, NaN/infinito, épocas externas,
IDs desconhecidos e arquivos alterados. Reabrir fontes e recibos em outro
intérprete. Conservar os hashes dos produtos anteriores e da sessão do dono.

Comparações externasJPL/Horizons em cinco épocas usam metadados de fonte
próprios e terão suas diferenças de modelo registradas. Essas consultas
complementam a conferência dos registros copiados e da cadeia de estados.

A fundação CPU antecede a integração em uma candidata própria, com catálogo,
fichas, navegação, época e exportação acessíveis pela interface. A candidata
precisará de leitura nativa das posições e de revisão de capturas100/150%.
As luas adicionais previstas no plano terão dados e testes próprios.

Fontes primárias consultadas na retomada incluem o
[diretórioNAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/)
e a [tabelaJPL](https://ssd.jpl.nasa.gov/sats/ephem/files.html).
