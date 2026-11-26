# IS-3 — mapa de casca e corte na cena nativa

Derivar de0.6.1 somente depois do seu perfil aceito, em candidata0.7 e
armazenamento próprios. Copiar a bancada numérica de mapas sem alterar os
provedores/coeficientes. Não ampliar a grade fixada de19×37/65×65.

Representações: vetor, linhas, mapa da casca e corte meridional. Cada mapa
usa símbolos cruzados nos pontosSI amostrados, em oito faixas discretas
de |B| com legenda emµT. Tamanho do símbolo é gráfico, não intensidade ou
volume físico. Não conectar lacunas, interpolarB no interior corporal ou
preencher o exterior mascarado. Faixas usam mínimo/máximo AMOSTRADOS do
mapa correspondente, sem alegar extremos globais. Costura/polos da casca
podem compartilhar um símbolo, preservando todos os dados científicos.

Mesma amostra, modelo, grau, época, centro e orientação das consultas. O
corte é visto perpendicularmente ao plano comZ para cima; u positivo
projetado à direita. Geometria normalizada pelo raio de referência, com
erro de quantização float32≤1e−6R, separado da incerteza observacional.
Ler e preservar fonte/reciboSI e hashes de cada mesh. Mapas congelados
continuam identificados após evolução e não aplicam força a centros neutros.

Uma sonda de célula recebe índices inteiros de linha/coluna e id da camada;
consulta os mesmos valoresSI que determinaram o símbolo/cor. Célula
mascarada não vira zero; recusa sem mudar sonda anterior ou fase. O rótulo
nativo da sonda confirma posição relativa≤1mm. Leitura/modelo/época/eixos/
posição/B aparecem no painel. Guardar somente índices e configuração em
checkpoint; reconstruir a célula a partir da mesma leitura congelada.
Validação antes de substituir fase recusa índices inválidos/mascarados.

Visibilidade e limpar preservam a política já aceita; sonda oculta não
reaparece sozinha ao selecionar outra célula. Salvar/carregar, ramos,
recargaCEF, novos processos e exportação conservam a definição e a sonda.
Modelos antigos vetor/linhas e checkpoints sem sonda continuam legíveis.

Verificar geometria/faixas/quantização/costura, câmera/perpendicularidade,
mesmo dado na sonda e no mapa, tipos/domínios e recusas. Depois jornada
realCEF/API/motor100/150 com imagens revistas, visível/oculto, troca de
representação/corpo, estado antigo e restore/restart. Perfil próprio por
mapa/modelo com orçamentos vigentes e coletor diagnóstico preflightado;
não herdar o perfil de linhas e não modificar candidato durante captura.
