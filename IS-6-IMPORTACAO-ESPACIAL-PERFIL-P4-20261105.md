# Perfil P4 da importação espacial aceito — 05/11/2026

Candidata 0.22.1: quatro janelas completas 1920×1080, UI100%, aquecimento30s
mais coleta60s cada, malha solar original1–8Rref65×96. Auditor-v3 aceitou
18.059quadros/240comandos,100%concluídos no prazo; zero quadros>100ms.
Pior mediana13,332ms, p95 13,815ms, p99 14,172ms. Comandos p95 máximo0,263s,
máximo0,315s. Pico RAM1,12961GiB; soma WDDM dedicada+compartilhada3,01709GiB.
A soma de contadores por processo pode contar alocações compartilhadas mais
de uma vez; não representa memória física única. Limites originais preservados.

Prévia PDH pausada validada antes das janelas. A preparação registrou10tentativas,
uma recusa transitória e depois cinco fotografias válidas consecutivas iguais,
em10,593s. Durante coleta, identidades ausentes continuam recusando o resultado.
PDH foi validado em66amostras por janela, incluindo cobertura de todo intervalo,
gerador, executável e inventário de processos; RAM usa a mesma árvore temporal.
Fonte, cápsula, amostras científicas, fase pausada e registros confirmados
permaneceram íntegros. Limpeza encerrou motor/servidor/launcher/wrapper0/0/0/0.

Recibo bruto: evidence/is6-spatial-import-profile-20261105p4.json.
Auditoria independente: evidence/is6-spatial-import-profile-audit-20261105p4.json.
Plano: evidence/is6-spatial-import-profile-plan-20261105p4.json.
Fontes executadas e seus arquivos permanecem congelados. P1/P2/P3 preservados
como recusas; o resultado novo não reclassifica essas tentativas.

Este aceite cobre renderização e comandos de vista da referência importada.
Não mede importação/salvamento/inicialização, entrada humana, malha derivada257,
GR orbital acoplada nem autoriza promoção automática ou aceite de todo IS6/v1.
Produto instalado3.13, atalho principal e sessão do dono preservados.

Próxima pendência independente: perfil próprio0.21.1 de importação composta,
com nova revisão que use PDH Python, RAM estrita e host Python próprio. Não
transferir o aceiteP4 a0.21.1. Depois retomar integração prevista no plano.
