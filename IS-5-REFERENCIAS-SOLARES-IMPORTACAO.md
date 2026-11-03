# B23v1.2 — importação e comparaçãoEOS,27/10/2026

Contrato após inspecionar ReadMe/header originais, antes do código. Preservar
ZIP/metadataaquisição/SHA. Importar seis struct+nu originais,semexecutarR.
47colunas de cabeçalho exato,2001linhas,r/Rsun=0..1 passo0.0005. Validar
shape,finite,raio estritamente crescente,massa crescente. Frações individuais
0..1;somatório≤1+5e−6 (precisão de6dígitos dos campos dominantes, tolerância
conservadora),registrar saldo sem normalizar. Valores de perfil não previstos
pelo esquema recusados. Dados brutos nunca corrigidos silenciosamente.

A primeira linha r=0 tem resíduos assinados de interpolação emmassa/L/dm/ν.
Preservar e sinalizar;mass/|L|residuais só na primeira linha tolerados≤1e−12.
nu/dm são colunas auxiliares assinadas preservadas,semuso como produção local
absoluta. Excluir r=0 das comparaçõesfísicas. logR perto do centro é
inconsistente comr/Rsun:registrar logR−log10(r/Rsun), sinalizar desvios>0.002dex
contra mediana desse deslocamento eexcluir da comparação. Nãoinferircentro
físico ouRsunadotado apartir dessesartefatos, nemsubstituir logR por raioinventado.

Converter logT→K;logrho(g/cm³)→kg/m³ por×1000;logP(dyn/cm²)→Pa por×0.1;
Csoundcm/s→m/s por×0.01;ne=10^log_ne×N_A×10^6m⁻³. Radiusnorm fica
adimensional;logRcm fica original (derivaçãoSI só identificada como tal).

EOScomparativa:usar apenas linhas originais com10<T6<16,ρ1e4..3e5 e sem
flagsderaio/centro;registrarelegíveis/excluídas. NÃOintegrar/recalibrarSol.
UsarEOSideal validada (íonsclássicos/elétronsFDnão-rel/radiaçãoLTE),comne
fornecido pelo perfil e convençãoYi=Xi/A da zona para espécies isotópicas
explicitadas. CoberturaH1/He3/He4/C12/C13/N14/N15/O16/O17;O18eoutroselementos
ficam emmassa não representada. Nenhuma composição inventada ou reescalada.

Para obter intervalo conservador de númeroionérico,ni/nb∈[ΣYcoberto,
ΣYcoberto+XnãoRepresentado/10]:O18temA18 e os demais elementos não cobertos
começam emNe(Z10),logoA≥10. Usar ne do perfil para ambos extremos,sem inferir
estadoionizadodosmetais. O intervalo pressupõe as convenções deabundância e
EOSideal declaradas; não é uma incertezaestatística daEOSreferência.
Comparar Pidealextremos/Preferência−1,sem atribuir causaindividual à diferença.

Aceite:conversãoDecimal amostrada≤1e−12rel,contagens/flags reproduzíveis,
recusas de headers/linhas/radius/fração/dadosnãofinitos;auditor independente
recalcula elegibilidade/pressões e pontos decontrole. Figura científica
exportável compara T/ρ/fraçãoH/He e intervaloP deGS98/AGSS09,com0..1r/Rsun nospainéis deestrutura e recorteexplicitamentenomeado no
painelEOS,
versão/procedência/domínio. Não transformar os perfis em previsão do Cosmos2.
