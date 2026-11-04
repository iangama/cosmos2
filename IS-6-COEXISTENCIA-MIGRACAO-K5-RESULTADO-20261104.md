# IS6 K5 — CPU, jornadas funcionais e visual aceitos; perfil próprio pendente

A fundação converte e reabre24documentos de Terra/Júpiter, quatro combinações
de visibilidade e três formatos: envelope composto0.1.0, envelope0.2.0 e
registroK4 com envelope0.2.0. Os24pacotes foram reabertos em outro intérprete;
os oito arquivos de entrada conservaram seus bytes. As229recusas cobrem
ciência adulterada mesmo com checksums recalculados, gerações desconhecidas,
metadados divergentes, flags numéricas, campos extras e JSON/UTF-8 inválidos.

A conversão conserva corpo, época, referenciais, ciência, modelos e flags.
Cada pacote incorpora o texto original exato e seu SHA256, geração e política,
checkpoint de destino e relatório. BOM/CRLF permanecem como bytes da origem.
Somente gerações conhecidas com hashes exatos são admitidas; caminhos no
JSON não escolhem código. Recibo is6-layers-migration-20261104h.json.

Os armazenamentos J/J2 passaram, cada um, em oito combinações,24registros,
24recusas,16falhas de gravação injetadas preservando o anterior e24reaberturas
em outro intérprete. V2 evita reconstrução redundante ao resumir metadados de
um registro já validado; leitura e gravação continuam validando completamente.
O serviço L2 passou em duas importações e24recusas, sem chamada nativa.
O erro do auxiliar de teste L original permanece preservado.

A0.21.0 Q/R passou funcionalmente, mas suas capturas PrintWindow tiveram
textos incompletos. A0.21.1 altera somente ui/is6-layers.js para não regravar
textos idênticos. S/T passaram em12confirmações,11recusas, duas importações,
reinício com identidade viva nova e processos0/0. Ciência/procedência persistem
em salvar, ramos e exportação. As quatro flags e cancelamento HTTP foram
verificados. As15capturas tiveram zero mutações de texto em repouso, mas uma
legenda ainda parecia incompleta: isso não foi tratado como aceite visual.

A revisão W passou com16capturas nativas: Terra/Júpiter nas quatro flags,
vista/armazenamento150% e prévias100%/150%. Ciência, procedência, época,
posiçãoSI e flags reais foram conferidas; os registros conservaram todos os
bytes e o host fechou0/0. O contorno corporal pertence aos nós da referência
magnética e é distinto da malha espacial. O perfil próprio0.21.1 segue pendente.

Uma interpretação anterior do diagnóstico V dizia que PrintWindow havia
perdido a interface. A comparação direta refutou essa conclusão: somente quatro
pixels diferem entre os arquivos PrintWindow e nativo, com zero diferenças nos
retângulos da interface esquerda, legenda e rodapé. Os15retângulos de legenda
S/T também coincidem com W. As cópias de inspeção W preservam todos os pixels
RGB. O recibo anterior e a revisão C permanecem como histórico; a correção está
em IS-6-CAPTURAS-CORRECAO-DIAGNOSTICO-20261104.md e no recibo
is6-import-capture-pixel-comparison-20261104v2.json. Não foi demonstrada uma
falha interna do Windows/CEF ou do produto por essa inspeção.

A falha M de transporte CDP1MiB foi isolada do produto; cef_page_v2 admite64MiB.
A recuperação cancelou a prévia sem novos arquivos e fechou0/0. O diagnóstico
U inicial tentou navegar antes de a API estar pronta. V espera /health. O início
com catálogo persistido demorou cerca de2min; desempenho de inicialização ainda
precisa ser medido e diagnosticado, sem atribuir causa conclusiva.

As provas H/J/J2/L2 e Q/R/S/T estão em evidence/. Fontes executadas, recibos
recusados e capturas antigas permanecem congelados. Nenhuma candidata foi
promovida. K5D tem contrato próprio para saves apenas espaciais, ainda sem
implementação: não se fabrica B=0 nem se renomeia um save espacial como composto.
IS6/v1 e os demais requisitos do plano permanecem em construção.
