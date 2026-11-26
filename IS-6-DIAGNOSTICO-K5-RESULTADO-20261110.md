# Diagnóstico instrumentado de K5

O ensaio previamente definido20261110a completou as três janelas e encerrou
motor, servidor, launcher e wrapper com quatro códigos zero. O verificador
conferiu1.859fontes, a cápsula de fontes do diagnóstico e os recibos.
Checkpoints, sessão do dono e atalho conservaram seus hashes.

| Janela | Intervalos brutos | p95 em ms | p99 em ms | Máximo em ms |
| --- | --- | --- | --- | --- |
| Terra, PDH ativo | 4.517 | 13,927 | 14,394 | 26,989 |
| Júpiter, PDH ativo | 4.517 | 13,901 | 14,291 | 26,579 |
| Mesmo Júpiter, coletor encerrado | 4.519 | 13,913 | 14,315 | 27,213 |

Os13.553intervalos ficaram abaixo de100ms. O maior tempo das etapas internas
foi2,641ms em renderização. O intervalo externo ao motor teve máximo26,628ms.
O observadorCEF registrou zero longtasks. As362consultasCEF de estado das
camadas terminaram, com maior duração6,777ms. Os buffers ficaram completos.

A pausa original580,569ms ficou sem reprodução. A ordem fixa e a ausência de
um novo evento mantêm a causa em aberto. K5A segue recusado e o perfil formal
composto continua pendente. As comparações científicas deste ensaio foram
asserções do executor selado; a análise posterior confere registros e tempos.

O plano, recibo bruto, correlação original e análise estão nos arquivos
`evidence/is6-k5-hitch-*-20261110a.json`. As estatísticas desta tabela incluem
o primeiro intervalo bruto. O auditor formal existente usa sua regra
original para o intervalo inicial.

A próxima construção independente do IS6 é a expansão do catálogo aos oito
planetas, com centros físicos, cobertura comum e fontes próprias.
