# Acervo nuclear AME2020 — contrato prévio

Fatia C2-01/18: instrumento de referência que amplia o conteúdo nuclear.
Tabela original AMDC/IAEA mass_1.mas20, estados de referência avaliados,
IDnucleus:ame2020:Z:A. N/Z/A, excesso de massa e incerteza, B/A tabulada e
incerteza emkeV, massa atômica e incerteza emu. Campos marcados# mantêm origem
estimada; asterisco mantém ausência, nunca zero. Não confundir B/A com meia-vida
ou estabilidade: incluir estados não ligados. Não atribuir ligação total à
força forte isolada: EM e outras contribuições pertencem à energia avaliada.

Carta de nuclídeosN×Z, sonda porposição, filtro de estimativas, seleção porN/Z,
curvaB/A×A e exportação com fontes/hash. É instrumento de dados, sem posição
clássica de nucleons inventada, trajetória, tempo ou reação automática. Liga-se
à bancadaD+T e decaimentos existentes, cujos gates e solvers continuam próprios.

Aquisição originalfixada, formatoFortran publicado preservado. Critériosantes:
- Quantidade/IDs únicos/N+Z=A/domínio, nenhuma linha ignorada silenciosamente.
- Neutron/H/D/T/He4/C12/Ni62/Fe56/U238 contra fonte original e ligação por massas
  independentemente, tolerância correspondente ao arredondamento tabulado.
- Incertezas e#estimadas disponíveis porpropriedade, valores ausentes explícitos.
- Comparação de massa com recorte upstreampynucastro para todos osIDs comuns;
  não usar esse recorte como autoridade de incertezas, pois ele as remove.
- UIcarta/sonda/filtro/seleção/curva/export,720px e CEFnativo, imagensrevistas.

Estado13/10: primeira fatia implementada e verificada; não encerra C2-18.

Tabela original de472.648bytes fixada SHA256e8599c6d…3307, recibo
evidence/ame2020-acquisition.json. Parser próprio stdlib respeita o formato
publicado, inclusive a parte inteira separada da massa em micro-u; ela não é
sempre igual aA (por exemplo O16). Os3.558registros têm IDs únicos, N0–177,
Z0–118,A1–295;1.008estimativas deB/A e295energiasbeta não calculáveis.
Não importar asterisco como zero nem a incerteza ausente como exata.

app/nuclei.py e /api/nuclei/catalog/export/save/load fornecem dados, contrato,
geração e seleção. UIapp/ui/nuclei.html ligada à bancada: cartaN×Z e curvaB/A×A,
pan/zoom/sonda por mouse, seleçãoN/Z,9referências, comparação de2estados,
filtro de estimativas deB/A, propriedades com unidade/incerteza/flag e fontes.
Seleção/vista/filtro persistidos com hash e geração; carga alterada é avisada.
Exportação grava JSON atômico emuser/exports, com caminho informado na interface,
e oferece download no navegador; não depender de handler de download doCEF.
Links levam aos palcosD+T e fraca; não acoplam seleção a uma reação.

verify-nuclei.py conferiu14.232campos por tokenização independente do original,
9âncoras contra números fixados e ligação por massas atômicas: maior resíduo
4,494e-5keV/núcleon. RelaçãoB/A com excessos de massa conferida emtodos os3.558,
com tolerância pelos arredondamentos próprios de cada campo; o maior resíduo
0,5073keV/núcleon ocorre no conjunto de estimativas arredondadas, não é erro
observacional. Recortopynucastro/NUBASE tem3.558IDs comuns e diferenças até5keV
pelos arredondamentos. O16 é exceção de último dígito:7e-5keV além da tolerância
de arredondamento, menor que incerteza tabulada3e-4keV; preservado o original
AME, sem igualar silenciosamente fontes distintas. Evidência registra a exceção.

Edge e CEFnativo passaram cartas/curvas, clique real na célula, comparação,
filtro, ausência/estimativa explícitas, consulta inválida sem mudar seleção,
salvar/retomar/JSON local, links dos palcos e validação da API. Edge720px sem
overflow e zeroerrosJS; CEF é teste separado no produto real. Capturas finais
foram revistas e rótulos sobrepostos corrigidos. Nenhum benchmarkG0 reatribuído.
Fontes primáriasF74/F75 emFONTES.md; relatóriosnuclei-check,nuclei-ui-check,
native-nuclei-check. Próximas lacunasC2-18:Q/limiares e processos avaliados.
