# K5D — próximo corte: registro atômico com procedência

A fundação CPU A está aceita. Implementar em novo módulo do staging espacial,
sem editar is6_spatial_import.py ou as fontes0.18/0.21 executadas. Esta definição
é o próximo corte autorizado; o armazenamento abaixo ainda não foi executado.

O novo registro usa schema2 e kind is6_spatial_body_mesh_checkpoint_with_origin,
com campos exatos artifact, view, branch, lineage_parent, origin e record_sha256.
A origem é a cápsula completa validada pela fundação A; pode ser nula somente
para referências novas sem importação. O artefato do destino deve coincidir com
o artefato original da cápsula. A vista do destino pode mudar por ação explícita;
a vista original permanece imutável na cápsula e identificada no resumo.

Importar cria UUID de ramo local novo, parentNone e lineage_parent igual ao
novo ramo. IDs de origem nunca selecionam arquivos do destino. Guardar latest,
criar filho e exportar conservam a cápsula no mesmo arquivo atômico. Não escrever
um segundo arquivo de procedência após o commit. Salvar não muda o pai; carregar
um ramo valida sua identidade e parentesco local, sem procurar os pais antigos.

Usar trava entre processos, temporário exclusivo, flush/fsync e os.replace,
limpeza de temporários e limite64MiB antes de abrir/gravar o destino. Conservar
32ramos no orçamento inicial. Falhas não alteram os bytes confirmados. JSON,
artefato, geração, vista, cápsula e hashes são conferidos na leitura/gravação;
catálogo não deve classificar origem adulterada como válida.

Provar as seis entradas A, mudança explícita de vista, latest/ramo/filho/export,
parentes inválidos e ciclo, adulterações com checksums recalculados, limites,
falhas fsync/replace e reabertura em intérprete novo. Preservar fontes e entradas,
registrando recibo próprio. Só depois integrar serviço/UI e proprietário nativo
com fase científica arquivada separada do contexto vivo atual.

A API nova transporta uma Reference validada e projeções por cópia. Uma
referência local nova declara originNone; uma importada carrega a cápsula
automaticamente em save/branch/export, sem argumento opcional que o chamador
possa esquecer. Mudar vista exige argumento explícito e não altera a original.
Load confere todo o parentesco local e recusa ciclos; IDs antigos são apenas
evidência. A reabertura, sob trava, remove somente temporários com a assinatura
exata deste escritor, conservando arquivos de terceiros. A prova inclui morte
do escritor antes do replace e dois processos disputando a última vaga32.
