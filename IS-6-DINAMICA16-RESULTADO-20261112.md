# Base numérica dos16corpos

O conversor e o ensaioCPU B passaram, com auditor separado. A base contém
Sol, oito planetas, Lua, Io, Europa, Ganimedes, Calisto, Encélado e Titã.
São16centros físicos com GMs individuais; nenhum baricentro de sistema foi
acrescentado como partícula. A candidata com interface ainda é a0.25.1,
cuja cópia dinâmica continua com três/quatro corpos.

Cinco épocas passaram na conversão SI/canônica,25entradas adulteradas foram
recusadas e120pares demonstraram atração recíproca. O maior erro de
aceleração foi6,7211e−12m/s², abaixo de1e−10m/s². As origens inerciais
separadas passaram por quatro recusas adicionais, cópias independentes e
serialização sem alterar o estado interno.

IAS15 e a ODE SI independente DOP853 foram comparados em121instantes de
30dias, totalizando1936posições de corpos. A diferença máxima por componente
foi0,136424206m e6,411589884e−6m/s, com limites10m/1e−5m/s. O refinamento
IAS15 de1e−9 para1e−12 diferiu até0,029103831m, abaixo de1m. O auditor
recalculou energia/momentos das séries arquivadas; todas as derivas ficaram
abaixo dos limites1e−9/1e−10/1e−10.

A execuçãoA ficou recusada por18,239958µm/s em Encélado e por20,331371µm/s
no teste com coordenadas absolutas transformadas. Três controles numéricos
e um controle de recentralização estão preservados. A revisãoB mudou a
representação da ODE de referência para incrementos SI e manteve a origem
inercial separada das coordenadas locais do solver. Não mudou tolerâncias
físicas ou integrou novamente os estados por efemérides. A invariânciaB é
da interface de origem separada; o ensaio de coordenadas absolutas deA
continua recusado. Ver IS-6-DINAMICA16-COORDENADAS-V2.md.

Fontes: output/is6-dynamics16-staging/system16_import.py e
system16_frames.py. Recibos: evidence/is6-dynamics16-verification-20261112b.json
e evidence/is6-dynamics16-audit-20261112b.json. A, diagnósticos e suas séries
permanecem nos mesmos prefixos com seus rótulos originais. Fontes executadas
e contratos estão selados; mudanças futuras exigem revisão própria.

Próximo: empacotar candidata isolada0.26.0, conectar importação explícita16,
IDs/registro, contribuições gravitacionais, controles, persistência e legado.
Validar serviço antes de trocar a janela; depois jornada/capturas/perfil
próprios. Campos magnéticos e processos nucleares não foram acoplados aos
16corpos por este ensaio. Sem promoção; V1segue7/21 e IS6incompleto.
