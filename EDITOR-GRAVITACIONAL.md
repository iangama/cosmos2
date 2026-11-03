# C2-06 — contrato prévio do editor gravitacional

13/10/2026. Implementação em fatias utilizáveis, mantendo C2-06 parcial até
cumprir criação/edição completa, raio/spin, prévia orbital e experiências.

Primeira fatia: selecionar qualquer corpo existente na cópia Atlas ou P32/P128
e editar massa, posição e velocidade em SI. Campo informa o referencial fixo:
baricentro inicial da fixture ou baricentro inicial do subconjunto/eixos J2000.
Não recentrar automaticamente após a edição. Não confundir com coordenadas
SSB do Atlas ou eixos GALACTIC de render. IDs e fontes originais sobrevivem.

Validar forma/unidades/referencial, finitude, limites declarados, ID único e
distância não nula entre partículas. Construir/avaliar uma cópia antes de trocar
a simulação. Edição aceita pausa o worker e reinicializa IAS15; falha preserva
estado, revisão e andamento. Registrar antes/depois, ΔE, ΔP e ΔL externos,
com unidade canônica e conversões SI. A energia numérica se mede a partir do
estado editado, sem esconder a energia adicionada/removida. Energia inicial
nula é válida; erro relativo fica ausente e erro absoluto continua disponível.

Reusar binárioREBOUND/checkpoint validado; manter originalAtlas imutável.
O editor não muda relógio/estado do Atlas. Raio, spin, criação/remoção,
colisões, J2 e prévias gerais terão contratos/ensaios próprios; não fingir
que um marcador ampliado já é um corpo extenso. Esta fatia conserva massas
pontuais, sem colisões, newtonianas/IAS15.

Limites iniciais de entrada: massa[1e-12,100] unidades nominais de massa,
norma posição<=1e17m e velocidade<=1e7m/s. São limites operacionais deste
editor, não garantia de validade relativística; nenhum termoGR é integrado.
Condição exige componentes de posição/velocidade e massa explícitos no
comando, com revisão da sessão esperada para recusar edição de estado antigo.

Aceite da fatia: vetores/massas SI→canônico→SI, balanços contra fórmulas
independentes, casoE=0, inválidos sem mutação, fontes/IDs/checkpoint/retomada,
edição real via CEF e movimento exibido confirmado. Um resultado parcial
não aprova C2-06 inteiro. Continuar criação/raio/spin/prévias em seguida.

## Criação e remoção — contrato anterior à segunda fatia,14/10

Cadastro separado do índiceREBOUND. Preservar IDs existentes e acrescentar
system_id por sessão/reinício; comandos exigem sistema/revisão/instante/frame
correspondentes ao estado carregado. IDs de novos corpos são gerados em
namespace próprio e nunca recebem referênciaJPL. Remover não renumera os
demais IDs. Estado derivado para o renderer usa identificadores estáveis.
Registro de todos os IDs emitidos evita reaproveitar um identificador removido.

Guardar fonteAtlas original completa mesmo após remover algum dos três corpos
copiados. Descrever claramente a população ativa; a comparaçãoJPL continua
um registro imutável, não uma descrição falsa do sistema modificado. Poder
iniciar um sistema definido pelo usuário com um corpo e acrescentar outros.
Domínio da segunda fatia:1–128corpos massivos ativos; impedir remover o último
ou exceder o limite. Não recentrar, preservar tempo e referencial inicial.

Criação/remoção são transações com cópia/reconstrução validada antes de trocar
o estado. Pausar ao aceitar; registrar matéria/energia/momento linear e
angular adicionados/removidos, com estados e procedência. Sem forças ocultas
para conservar artificialmente o sistema após uma intervenção externa.

Checkpoint3 guarda binário, cadastro, população original, IDs emitidos,
system_id, contratos, histórico e geração científica específica do modelo,
com metadados selados e substituição atômica. Leitura compatível com1/2,
validada antes de substituir a sessão ativa. Corrupção de nomes/IDs/fontes,
população incoerente ou binário inválido deve falhar sem mutação. Mudança de
geração é relatada, sem mascarar os dados de origem.

Ensaios: remoção no meio da lista, inserção seguinte sem renomear sobreviventes,
save/load/reabertura/legados/corrupção, balanços e integração independente,
limites1/128, sistema antigo/revisão/tempo obsoletos, fonteAtlas imutável,
UIreal com nome contendo acentos/aspas sem injeção de script e navegação da
câmera preservada dentro da precisão gráfica. Não aprovar C2-06 sem as
demais entregas de raio/spin/prévias e experiências.


Complemento14/10: um token de edição novo em cada carga impede reaplicar
formulários anteriores mesmo quando sistema/revisão/tempo voltam aos mesmos
valores. O token é de execução; IDs científicos e namespace persistem.
Cadência do worker cede aos comandos entre passos adaptativos e limita cada
lote a40ms de trabalho alvo; um passo individual ainda pode exceder esse alvo.
Tempo efetivo mostra o avanço realmente calculado. Um encontro abaixo de1mm
pausa por domínio da massa pontual, sem colisão, fusão ou impulso artificial.
Callback temporário de controle não vai ao checkpoint nem à cópia científica.
Entrada recusada conserva conexão gráfica e estado de execução; não atrasa
pausa fechando/reabrindo o canal do motor.
