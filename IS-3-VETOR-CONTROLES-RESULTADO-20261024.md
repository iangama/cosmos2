# IS-3 — controles do vetor magnético na candidata

Nova candidata isolada: output/is3-body-vector-product. A base com maré,
IGRF e JRM33 permanece em output/is3-tides-product, sem alteração. Instalado
e sessões do dono preservados. A camada não foi promovida.

O painel oferece mostrar, reenquadrar e ocultar uma amostra magnética de
Terra ou Júpiter, usando os formulários IGRF/JRM33. O servidor calcula a
leitura com guard de fase; o navegador não fornece B. O desenho guarda
época, fonte e componentes SI. Seta verde tem comprimento gráfico uniforme
0,3R, sem representar intensidade. Grade é WGS84 para Terra ou esfera de
referência do JRM33, sem alegar superfície física de Júpiter.

Mostrar oculta apenas o marcador ampliado do corpo amostrado. Ocultar
restaura a política atual de marcadores/raios. A camada fica fixa no frame
inercial ao evoluir e a interface identifica que a fase mudou. Restaurar,
trocar topologia/sistema ou voltar ao Atlas limpa seus nós. Recarregar CEF
recupera a camada da sessão atual do renderizador; checkpoints não guardam
ela nem seus formulários. Nenhuma força age nos centros neutros.

A jornada nativa foi verificada em duas partes, sem alterar o produto
entre elas: A passou criação/substituição, máscara, 100/150% e recusas; parou
ao tentar ler innerText de um painel recolhido. B abre o painel e verifica
recarga, ocultação, política atual de raios, evolução fixa, salvar/restaurar
e Atlas. A permanece incompleta. O resumo combina os checks válidos com
fontes idênticas: evidence/is3-body-vector-native-journey-summary-20261024.json.

A suposta ausência de geometria em prévias anteriores foi uma avaliação
visual incorreta. RGBA central idêntico em 100/150 comprovou isso, inclusive
para Terra e Júpiter. A correção e figuras foram preservadas. Nenhuma
correção de renderização foi aplicada. O código diagnóstico GL foi compilado,
mas seu staging falhou em duas DLLs; não foi aberto/adotado. Quatro fontes
foram restauradas byte a byte e o header criado foi removido; runtimes
medidos intactos. Registro output/render-state-diagnostic-staging/closure.json.

Perfil próprio em andamento: contrato IS-3-VETOR-PERFIL-PREVIO.md. Duas
janelas de 60s, após 30s de aquecimento cada, IGRF/JRM33 e três vistas.
A tentativa A pediu ritmo não suportado 0,001 e foi recusada antes de
aquecer/capturar. B usa a menor opção suportada, 0,1, confirmada por
preflight; não muda limites de quadros/memória. A camada continua da época
inicial, sem consultar campo fora de seu domínio ao evoluir. Não atribuir
a ela desempenho de campos atualizados a cada passo. Consultar recibo
evidence/is3-vector-profile-20261024b.json e auditor próprio antes do aceite.

## Auditoria e fechamento desta fatia — 24/10, 11:35 UTC

Perfil B concluído e auditor independente aceito, sem repetir capturas:
evidence/is3-vector-profile-audit-20261024b.json. Cada modelo registrou
4.499 quadros em 60 s; p95 máximo 14,597 ms, p99 máximo 15,023 ms,
nenhum quadro acima de 100 ms. Ritmo medido/solicitado mínimo 1,00020;
RAM máxima 1,03108 GiB e WDDM dedicada somada 2,96039 GiB. Os limites
originais passaram também em cada vista. Escopo: uma camada fixa por vez,
quatro centros neutros e ritmo 0,1; não cobre amostragem magnética contínua.

Capturas dos controles A revistas em resolução original e com recortes
ampliados sem interpolação. Região de cena 950×720 RGBA idêntica entre
100/150 para ambos os corpos; seta, ponto, grade e rótulo visíveis. Textos
dos controles legíveis. Recibo is3-body-vector-controls-visual-review-20261024.json.
Isso fecha a revisão destas quatro imagens, sem aceite visual final do catálogo.

Migração executada em cópia isolada do checkpoint IS3 anterior:
evidence/is3-vector-migration-20261024.json. Tempo e todas as componentes
binárias de massa/posição/velocidade permaneceram exatos; geração alterada
foi informada; IGRF/JRM disponíveis sem mutação orbital. Originais e ponteiro
do dono preservados. Não demonstra persistência da camada visual.

Ao retomar, nenhum processo OpenSpace/Python estava aberto no Windows;
output/session.json é apenas registro da abertura anterior. A candidata
de vetores permanece sem promoção. Próxima fatia: linhas magnéticas 3D
derivadas dos mesmos provedores, em staging e com contrato numérico próprio;
capacidades/ausência de modelo lunar e persistência visual continuam pendentes.
