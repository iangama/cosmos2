# C2-14 — perfil próprio aceito em21/11/2026

A candidata isolada0.28.2 passou nas quatro janelas contratadas: órbita
excêntrica, atraso dos relógios, trajetória retilínea e órbita circular.
Foram395amostras,66por janela estável, sem descarte de amostras. Cada
captura útil teve4.503intervalos e cerca de60,060s. A regra prévia excluiu
exatamente o intervalo que atravessa a abertura de cada janela.

Medianas13,365–13,375ms; p95≤14,454ms; p99≤15,344ms; máximo18,711ms;
zero intervalos acima de100ms. Picos amostrados da árvore própria:
RAM1.152.180.224bytes, GPU dedicada3.251.924.992bytes e dedicada+
compartilhada3.313.344.512bytes. Estes são máximos amostrados.

O observador registrou13.474polls brutos, inclusive o inicial. Seu maior
intervalo foi61,722ms, abaixo de250ms; a primeira descoberta durou16,957ms.
A maior duração de uma amostra foi213,291ms; cadência0,984–1,016s. A
inicialização PDH foi única e sem gauges descartados. A auditoria recalculou
cadência e cobertura usando todos os polls, além de frames, HTTP e leituras
CEF, identidades nativas e memória. Em cada janela houve cinco voltas e
mais de1.200avanços da animação.

Recibos imutáveis: evidence/c214-orbits-profile-audit-20261121b.json,
c214-orbits-profile-collector-20261121b.json e
c214-orbits-profile-host-20261121b.json. Receita/fontes arquivadas antes
dos dados. As oito saídas retidas (dono+candidata) tiveram código0. A fase
pausada, câmera, época e favoritos do dono foram restaurados e conferidos.

A preparação21a não chegou a iniciar a candidata: seu lançador ainda
exigia dois atalhos históricos. O guard de restauração também comparava
um favorito temporário já removido ao snapshot feito depois de adicioná-lo.
A recusa continua preservada; a recuperação foi confirmada em recibo
separado. A versão seguinte do host/lançador registra a transição explícita
dos atalhos e preserva a lista anterior de favoritos. A/B de14/11 continuam
recusados. A residênciaF não foi repetida.

Este aceite mede renderização/residência da candidata0.28.2 após cálculo
concluído. Não mede solver, não cobre GR16 e não conclui C2-14. A entrega
posterior na revisão local0.28.4 recebe validação funcional própria; estes
números não são transferidos para ela.
