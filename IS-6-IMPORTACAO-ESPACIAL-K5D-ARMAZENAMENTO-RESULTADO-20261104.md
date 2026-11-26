# K5D — armazenamento espacial CPU aceito

O módulo novo is6_spatial_import_store.py passou nas seis entradas solares da
fundação A: saved, ramo e exportação, cada um nas duas visibilidades. Os24
registros derivados (ramo importado, latest, filho e exportação por entrada)
foram reabertos em outro intérprete, com artefato, sondas, vista original e
cápsula de procedência conservados. Alterar a vista atual foi uma ação explícita.

A API Reference transporta a origem automaticamente. A importação cria UUID
local novo sem pai; guardar não modifica o ramo original; filho conserva o pai
local e exportação conserva a cápsula no mesmo registro schema2. O catálogo
revalida artefato, geração, origem e parentesco local e recusa origem adulterada.

As43recusas incluem JSON estrito, gerações/artefatos/vistas/cápsulas adulterados
com checksums recalculados, pais ausentes, ciclos, identidades divergentes,
escapes e limites64MiB/32ramos. As18falhas fsync/replace preservaram todos os
bytes confirmados em guardar, ramo, exportação e confirmação de importação.
Dois processos disputaram a última vaga: exatamente um gravou, total32. A trava
impediu outro processo e liberou após a saída do proprietário. Encerrar o escritor
depois do fsync e antes do replace manteve o registro anterior; a reabertura
removeu somente seu temporário abandonado e preservou um arquivo de terceiros.

O verificador B foi recusado ao criar um link simbólico auxiliar: WinError1314,
sem privilégio no Windows. Esse resultado permanece em
evidence/is6-spatial-import-store-20261104b.json. O complemento independente
revalidou os24registros, concluiu as provas entre processos e a reabertura,
sem editar o módulo ou o verificador B. Recibo aceito:
evidence/is6-spatial-import-store-20261104b-r2.json. O caso específico de link
simbólico não foi executado; nenhuma permissão ou política foi alterada.

Fontes executadas, três arquivos originais, seis fontes/cápsulas A e sessão do
dono conservaram seus hashes. Não houve chamada ao motor, amostra magnética,
reamostragem, conversão implícita ou alteração das candidatas0.18/0.21. Este é
aceite do armazenamento CPU solar, sem aceite de serviço/UI/nativo, desempenho,
outros corpos ou IS6/v1. O próximo corte é o serviço espacial do contrato próprio.
