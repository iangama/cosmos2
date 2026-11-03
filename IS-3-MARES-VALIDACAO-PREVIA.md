# IS-3 — primeira ligação: maré externa na fase dos quatro centros

Próxima implementação autorizada em candidata isolada, após concluir a
auditoria do perfilIS-2. Não exige integraçãoEM nem aprovação artificial deJ.
Não há resultado desse instrumento neste documento.

Entrada: snapshot confirmado dos quatro centros, identidade/revisão/token,
instante,frame e deslocamento vetorial em metros a partir do centro escolhido.
Os eixos do deslocamento são os inerciaisJ2000 da dinâmica; não chamar um
vetor nessa base de coordenada geográfica ou direção vertical de uma costa.
Exemplo inicial: deslocamento `[6378137,0,0]`m a partir da Terra, com esse
comprimento explicitamente escolhido para a demonstração, sem adotar nova
geometria científica no cadastro nem presumir uma orientação terrestre precisa.

Para cada fonte externaj, calcular a diferença exata
`GMj*((rj-ri-d)/|rj-ri-d|³ - (rj-ri)/|rj-ri|³)`.
O campo próprio do corpo escolhido é excluído nos dois pontos. Essa diferença
é a maré externa do recorte pontual; ela não prevê água oceânica, deformação,+aquecimento ou resposta material por si só. Somar vetores por fonte usando
o mesmo snapshot e manter a contribuição de cada fonte identificável.

Guardar também o tensor linear de cada fonte, aplicado ao deslocamento,
e o resíduo exato menos linear. Não confundir g total com sua diferença.
Validar no modelo de monopolos; rejeitarJ2/maré material ativos até existir
contrato que inclua seus campos diferenciais. Campo indisponível nunca vira0.

Receita antes da execução:72casos, quatro centros×seis direções cartesianas
×três comprimentos (100m,100km,6378137m), contra avaliação independente em
Decimal com70dígitos. Tolerância absoluta de componente2e−15m/s² e relativa
1e−10 para valores maiores que1e−12m/s². Testar deslocamento0 exatamente,
refinamento do limite linear (1000m→100m, resíduo compatível com segunda
ordem), ausência de campo próprio e soma vetorial. Todos os campos retornam
identidade/revisão/token/instante/frame e épocaTDB; não marcar amostra antiga
como atual depois de evoluir, editar ou restaurar.

Recusas sem alterar fase nem arquivos:IDs desconhecidos, vetores incompletos,
booleanos/NaN/infinito, coordenadas fora do domínio declarado, singularidade
de outra fonte, guard obsoleto e modelos ainda não contemplados. Preservar
fontes/fixtures antes de calcular. A função científica começa em
`output/is3-solar-staging`; sua ligação à API/UI exige recibos próprios e
depois uma jornada nativa. Não editar a candidata solar durante um perfil.

Depois: ligarIGRF à época/posição/rotação da Terra com o limite da orientação
declarado, estudar/fixarJRM33 com coeficientes e convenções verificadas e
manter campo lunar/global/crostal/externo separados. Essas entregas seguem
pendentes; este contrato não lhes dá aceite nem adota novos dados externos.
