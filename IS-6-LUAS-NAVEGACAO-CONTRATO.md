# Navegação das seis luas principais

A candidata0.25.0 acrescenta Io, Europa, Ganimedes, Calisto, Encélado e
Titã à cena0.24. Conservar os dez centros anteriores, seus dados e mapas.
O catálogo terá16corpos e15destinos físicos navegáveis. As referências
permanecem geométricasSSB/J2000, renderizadas emGALACTIC, com orientaçãoIAU
geral. Usar somente os seis novos recortesSPK; segmentosDE440 incorporados
nos pacotes completos ficam fora da cena. A cópia dinâmica de três/quatro
corpos conserva seu escopo anterior, sem incorporar luas implicitamente.

A referênciaCPU de16corpos,1.236comparações dos recortes,25recusas e
comparação externa corrigida de30vetores são pré-requisitos. Fixar mapas
originais por hash e decodificar todos os pixels. Dados observacionais não
confirmados permanecem identificados como desconhecidos. A ficha informa
o maior semieixo para as novas luas, que podem ser triaxiais.

Verificar16posições e15rotações em cinco épocas, incluindo as bordas da
cobertura1995–2049. Orçamentos conservados: posição≤max(1mm,8ULP do maior
componente), rotação≤1e−12 por elemento e semieixos inferidos do renderer
≤2cm. A esfera envolvente de Saturno inclui os anéis; não substitui os
semieixos do globo. Conferir os seis arquivos realmente usados como mapa.

Percorrer15destinos pela interface, quatro vistas das seis novas luas,
busca/árvore de parentesco, favoritos, retorno/viagem/cancelamento, relógio,
exportação16corpos e acesso à ficha selecionada. Testar cópias anteriores,
recusas sem mutação e capturas100/150% revistas de cada nova lua. O teste
de dados do catálogo e o teste de navegação terão recibos próprios.

O perfil posterior terá15janelas estáticas de30s de aquecimento+60s de
medição em1920×1080/UI100%, céu ativo e exposição3,7, relógio pausado e
vista Visão geral. Conservar mediana≤16,7ms,p95≤25ms,p99≤50ms,zero>100ms,
RAM≤8GiB e WDDM≤5,5GiB. Usar préviaPDH,66amostras por janela, propriedade
temporal dos processos e rastreamento por etapa. Selar receita/executor/
auditor antes da coleta. O perfil0.24 não transfere aceite automaticamente.

Salvar a vista atual e avisar antes da troca de versão. A0.24 permanece
disponível pelo atalho já conferido. Ao testar0.25, conservar sua janela
aberta, restaurar a vista do dono e verificar fechamento/reabertura com
quatro saídas zero. Nenhuma candidata é promovida por este contrato.
