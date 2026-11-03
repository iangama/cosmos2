# IS6 — caminho de exportação na sonda, revisãoF

O diagnóstico nativo de geometria duranteJ0C identificou o elementoexato:
zone-file retém o caminho longo da exportação,scroll332/client297 e painel
scroll352/client337. O ajuste de min-width da0.18.4 ainda não quebra essa
palavra. A0.18.4 foi construída e preservada,sem execução/aceite nativo.

Derivar0.18.5 com uma única diferença relativaà0.18.4: is5-zone.css acrescenta
quebra anywhere e white-space normal nos textos de ajuda do painel. Preservar
conteúdo completo,cópia e rolagem vertical. Não usar overflow-x:hidden.

J0D usará0.18.5,mesmos cenários e limites,com verificações de rodapé,overflow,
restauração nativa e10PNG a revisar. Ciência/serviços/renderer idênticosà0.18.3.
