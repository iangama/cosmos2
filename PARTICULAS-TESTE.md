# Partículas de teste — Cosmos2 3.13

Instalada localmente em18/10/2026 após auditoria dos perfis de10.000 partículas
e256 massas no mesmo motor. A abertura padrão, criação/seleção na interface e
as quatro telas de forças passaram. Os10.000 marcadores são partículas sem
massa; o perfil de256 mede corpos autogravitantes separadamente.

## Modelo e papéis

Uma fonte newtoniana com massa positiva e até10.000 partículas com massa
exatamente zero compartilham UM IAS15. N_active=1 e testparticle_type=0:
partículas recebem gravidade da fonte, sem reação nela e sem força entre testes.
A Session principal é apenas espelho da fase confirmada da fonte; ela não é
integrada em paralelo. Fonte, instrumentos e balanços globais continuam separados
da população passiva. J2, maré material e edição da fonte ficam bloqueados
neste modo; remover partículas permite voltar à edição normal.

A interface cria um anel circular sintético, de1 a4 unidades canônicas de raio,
sem época absoluta ou origem observacional. Isso é uma condição inicial plana;
o solver continua tridimensional. O teste gravity-spherical-installed-check.json
confere1030 direções emdois centros; gravity-spherical-native-check.json mostra
seis corpos em±x/±y/±z aproximando-se igualmente do centro na cena real.
Para uma fonte isolada: a=−GM(r−r0)/|r−r0|³. A contribuição aponta para o centro
inclusive acima e abaixo. Outras fontes somam contribuições; J2/maré têm os seus
termos adicionais. Não há estrutura material interna da esfera neste modelo.

## Identidade, leitura e arquivo

IDs individuais são tp:cloud_id:index. O índice é estável dentro da população;
reiniciar cria outra identidade, enquanto salvar/retomar conserva a população
e troca o token de edição. A leitura selecionada guarda posição em m,
velocidade em m/s, energia específica em J/kg e momento angular específico
em m²/s. Os dois últimos são relativos à fonte inercialmente móvel.
Balanços globais incluem somente fontes ativas; uma fonte imóvel tem escalas
nulas de normalização. Nesse caso o erro normalizado fica indefinido e os erros
absolutos SI são conferidos, sem fabricar erro relativo zero.

O checkpoint mantém o estado completo do IAS15 em sidecar binário selado,
fora dos snapshots JSON de interface. Validação inclui massa/papel, identidade,
contagem, instante, origem, metadados, binário e futuro exato. Ramos continuam
imutáveis e migradores preservam os checkpoints antigos antes da instalação.

## Cena e exportação

Um RenderablePointCloud desenha todos os pontos; não existe um nó por partícula.
Uma âncora e um marcador acompanham a seleção. O transporte tem posições SI
float64, identidade de sistema/token/população/fonte/referencial, sequência,
instante e escalas. Python confere SHA256 eCRC32; o motor confereCRC32 e publica
o SHAdeclarado. Não atribuir cálculo deSHA256 ao motor.

A ponte mantém um pacote em voo e só declara o instante exibido após confirmação
nativa do mesmo pacote e uploadGPU. O desenho quantiza coordenadas emfloat32;
leituras e exportações científicas continuam float64. O erro gráfico é publicado
no recibo nativo. O perfil aprovado se refere ao anel padrão, não a qualquer
posição/velocidade ou população arbitrária.

Exportar posições pausa e exige instante nativo confirmado; o arquivo contém
as10.000 posições originais, índice/identidade, unidades, fonte e geração.
Exportar leitura conserva o instante guardado e a marca de antiga quando houver
evolução. O marcador pode continuar seguindo posições novas sem transformar os
números antigos em uma leitura ao vivo. Arquivos saem em user/exports.

Travas transitórias de arquivosWindows têm janela de retry de10ms, sujeita ao
escalonamento. Uma falha não valida uma fase nova nem perde o pacote anterior;
indisponibilidade persistente por2s é erro explícito. Testes com travasREAIS
recuperam a publicação curta e recusam a permanente, limpando temporários.

## Evidência

- cloud-final-regressions-check.json: nove suítes, incluindo persistência,
  futuro exato, worker, corrupção, J2, maré, ressonâncias e13 migrações reais.
- cloud-product-candidate-check.json: jornada realCEF, seleçãoSIexata, evolução,
  foco, leitura antiga, exportações, save/load e retornoAtlas sem errosJS.
- cloud-legacy-query-ui-check.json ecloud-legacy-baseline-ui-check.json:
  fluxos massivos preservados; ativar/carregar nuvem em motor antigo é recusado
  antes da mutação. A interface informa a indisponibilidade nesse modo.
- native-benchmark-c211cloud4-review.json:3×60s após30s,1080p, p95≤18.328ms,
  p99≤19.516ms e zeroquadros>100ms; auditoria também confere cada trecho,
  RAM/WDDM/DXGI, ritmo, pausas e bytes congelados.
- cloud-profile-phase-c211cloud4-check.json: todos10.000 pontos após39.200
  órbitas internas conferidos porKepler independente; erro relativo≤5.371e-13.

A meta de publicação do worker é30Hz, não o passo do integrador nem uma cadência
assegurada. Observação posterior porpoll40Hz encontrou pelo menos14.735
confirmações nativas/s, com carga extra e possibilidade de perder atualizações.
O tempo físico manteve ritmo1.00059; atraso máximo observado foi.2 unidades do
modelo. FPS do renderizador e cadência de atualização física são medidas distintas.
Perfis anteriores e suas recusas permanecem arquivados; nenhuma janela recusada
é aproveitada para completar uma execução nova.

Aceite de instalação18/10: c211-cloud-validated.json, cloud-installed-ui-check.json,
cloud-installed-four-forces-cef-check.json e runtime-default-boot-check.json.
P256 no mesmo motor: c211p256c2, p95≤21.461ms, p99≤23.260ms, zero>100ms;
pausa máxima53.376ms, ritmo mínimo1.0002195u/s. Backup3.12 em
output/c211-pre-cloud-20261018T033232Z/app.
Seis ciclos de limpeza de mapas e duas transições256↔10000↔Atlas passaram
(cloud-native-transitions-check.json). Um encerramento anterior durante limpeza
continua registrado; essas repetições não identificam nem eliminam sua causa.
Malha e novas camadas ainda pendentes conforme CAMADAS-QUATRO-FORCAS.md.
