# IS5 — artefato, worker e leitura de instantes,26/10/2026

Antes da implementação: worker próprio,sem renderer/owner em testes de ciência.
Rede é calculada em241instantes; selecionar/reproduzir leituras percorre esses
instantes calculados, sem fingir um integrador físico executando em tempo real.
Recalcular condições/gates refaz cenário desde a composição inicial. Preservar
artefato anterior para ramos; não classificar a ação como impulso num instante
intermediário. Referência tem todos os operadores/canais ligados.

Arquivo único selado inclui fonteSolararquivada/configuração/redesreal+
referência/geração e vista(index0..240,visibilidades). Reload valida geração,
reconstrói fonte e recomputa rede antes publicar; arquivo antigo/corrompido ou
erro de cálculo não substitui último artefato aceito. GravaçãoatômicaWindows,
orçamento16MiB,sem duplicatasJSON;32ramos imutáveis com pai explícito.

Guardas porworker_id,artifact_id,edit_token,revision. Novo processo/load
troca token; mutações/leitura indexadas com guarda antiga recusam. Recalcular
e restart criam outro artefato. Fonte física é sempre a fase arquivada; UI/cena
devem distingui-la da cópia orbital atual. Não migrar checkpoint de outra fatia.

Publicação pequena: resumo e sonda. Curvas completas/proveniência sob demanda,
sem retransmitir redes inteiras em polling200ms. Fila16,protocolo e tamanhos
limitados;RHS200000 por integração. Quitcontrolado;sem processossoltos.

Testarcriar/recalcular/restart,sondasreal/referência,salvar/load/newprocesso
resultados idênticos,vista/ramos,hashsexportados e recusasantesmutar. Testar
bloqueioWindows/arquivo inválido,canais/gates,tipos e identidadeSourceSolar.
Nada deste contrato aceita UI nativa/perfil ou resposta térmica/transporte.
