# IS6 K5A — conversão CPU com origem preservada

A fundação `is6_layers_migration.py` passou em 24 conversões/releituras:
Terra e Júpiter, quatro visibilidades e três entradas conhecidas — envelope
composto 0.1.0, envelope 0.2.0 e registro K4 com envelope 0.2.0. Outro
intérprete reabriu os 24 pacotes. Os oito arquivos legados de entrada
conservaram seus bytes; a sessão do dono também conserva seu hash.

O conversor preserva a ciência, corpo, época, coordenadas, modelos e
visibilidades. Cada pacote contém o texto original exato, seu SHA256,
política/geração, checkpoint de destino e relatório da conversão. A leitura
reconstrói a origem e o destino. Caminhos do documento não escolhem código;
somente as gerações conhecidas, com hashes exatos, são aceitas.

As 229 recusas incluem adulterações científicas com checksums externos e
internos recalculados, geração desconhecida, metadados divergentes,
visibilidade numérica, campo extra, JSON duplicado/não finito e UTF-8 inválido.
O teste também preservou BOM e finais CRLF como parte dos bytes de origem.

Recibo: `evidence/is6-layers-migration-20261104h.json`. Entradas, pacotes,
releitura e ZIP de fontes estão em `output/is6-layers-migration-20261104h/`.
As fontes executadas dessa fundação estão congeladas.

Armazenamento com procedência, serviço, UI, candidata 0.21.0, reinício nativo
e perfil próprio ainda não têm aceite. Há duas versões do armazenamento em
teste: a revisão evita repetir a reconstrução ao projetar metadados de um
registro já validado; ambas mantêm validação completa antes da gravação.
Saves apenas espaciais exigem outra conversão e permanecem pendentes.
