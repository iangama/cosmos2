# IS5 — ponte transacional da compressão

Recibo `evidence/is5-compression-bridge-20261029a.json` concluído e aceito.
Quatro grupos passaram com trabalhadores e cálculos físicos reais: cancelar a
criação inicial, cancelar recálculo preservando exatamente o artefato anterior,
recusar falha de anexação da cena e confirmar a troca de trabalhador somente
após sucesso. Cancelamentos medidos em 0,1861 s e 0,1735 s; limite prévio 6 s.
O processo candidato terminou, sem publicação tardia, e o ramo pai foi mantido.

A cena nesse verificador foi simulada. O resultado não aceita HTTP, CEF,
renderização, inspeção visual, desempenho ou promoção. Ponte, contrato e
verificador vinculados ao recibo permanecem preservados.

Em 01/11, a receita existente concluiu a candidata isolada 0.17.0, sem promoção,
e o launcher abriu o motor nativo. Aceites próprios de interface e perfil
continuam pendentes.

O diagnóstico CEF `is5-compression-cancel-cef-20261101b.json` confirmou uma
falha da 0.17.0: a ponte publicava a transação cancelável, porém a interface
descartava atualizações enquanto aguardava a resposta longa e ocultava o
botão. Cancelamento HTTP direto de limpeza levou 0,0767 s. Captura examinada.
O primeiro diagnóstico (sufixo a) não iniciou o cálculo por uma corrida do
próprio teste com o botão ainda desabilitado; ficou preservado sem aceite.

`scripts/revise-is5-compression-product.py` preparou a candidata 0.17.1,
alterando somente `ui/is5-zone.js`. Durante a espera, a interface agora atualiza
os campos de ocupação e cancelamento, mantendo a leitura confirmada. Fontes
da 0.17.0 e ciência/worker/ponte foram preservados. O teste nativo próprio
`verify-native-is5-compression.py --label 20261101a` está em execução.
Primeiro grupo passou: botão visível em 0,158 s, cancelamento CEF em 0,999 s,
recusa de segundo cálculo em 0,0013 s e nenhuma alteração/publicação tardia.
