# Dinâmica16 — perfil próprio aceito

A candidata0.26.2 passou nas quatrojanelas previamente seladas. Foram
18.053intervalos válidos, nenhum acima de100ms. O maior intervalo foi
21,183601ms. O pico da soma de working sets foi1,252819GiB; a somaWDDM
dedicada+compartilhada dos processos próprios chegou a3,017479GiB.

| Janela | Quadros | P95ms | P99ms | Taxa medida/solicitada |
| --- | ---: | ---: | ---: | ---: |
| Sistema pausado | 4.512 | 14,072 | 14,768 | — |
| Sistema em0,1unidade/s | 4.516 | 14,183 | 14,908 | 0,999699 |
| Terra em1unidade/s | 4.512 | 14,193 | 14,937 | 1,000013 |
| Titã em10unidades/s | 4.513 | 14,212 | 14,949 | 1,000340 |

Cada janela teve30segundos de aquecimento e60segundos de quadros cobertos
por66amostrasPDH a1Hz. As janelas dinâmicas prepararam o solver por1segundo,
pausaram durante o aquecimento gráfico e retomaram na coleta. Titã chegou
a21,519535dias de modelo, dentro dos30dias verificados. O auditor recalculou
os percentis, somas deRAM, bytesPDH, identidades e parentesco temporal dos
processos, cobertura do intervalo, cenário estável e avanço estrito do relógio.

O auditorA recusou o tipo do contador de rastreio: o motor serializa inteiros
como4517.0, enquanto A exigia o tipoPythonint. A revisãoV2 foi preparada antes
de analisar os dados novos, usando a evidência de representação do perfil
anterior. Ela exige valor numérico finito, positivo e integral. Todos os
limites de quadros/RAM/GPU/taxa permaneceram iguais. A coleta foi executada
uma vez; o recibo recusadoA e ambos os auditores estão preservados.

O host fechou motor, servidor, launcher e wrapper com quatro códigoszero,
reabriu a0.26.2 e restaurou a vista. Um testeCEF posterior carregou a fase
salva16 nesse processo novo: corpos, posições, velocidades, massas, época,
origem separada e revisão voltaram exatamente. Terra/Júpiter/Titã retomaram
suas15contribuições, com erro de posição nativa zero. Checkpoint e favoritos
conservaram seus bytes; os nós da cena foram removidos ao voltar ao Atlas.

Abrir-Dinamica16.cmd foi testado e reutilizou a janela aberta. O atalho
anterior e as candidatas anteriores permanecem preservados. Recibos:
evidence/is6-dynamics16-profile-20261112a.json,
is6-dynamics16-profile-audit-v2-20261112a.json,
is6-dynamics16-reopen-20261112a.json e is6-dynamics16-opener-20261112a.json.

Esse aceite é do modelo pontual16 e de suas vistas medidas. K5Aoriginal
continua recusado;IS6 e aV1 permanecem incompletos. Próximo: contrato e
preparação do percurso ampliado entreAtlas16,dinâmica16 e as bancadas
existentes, com cada domínio científico e armazenamento identificados.
