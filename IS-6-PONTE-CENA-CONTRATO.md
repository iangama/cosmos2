# IS6 — transação de cena, contrato prévio01/11/2026

Após protótipo nativo/visualA, criar adaptador isolado em
output/is6-spatial-bridge-staging. Não editar renderer ou fontes aceitas.
Ainda não é produto0.18,HTTP,formulário,persistência de serviço ou perfil.

Uma cena candidata prepara seus arquivos e nós com DrawElementsfalse e
não move a câmera nem oculta a cena confirmada. Cancelamento por evento é
conferido antes/depois das chamadas nativas e imediatamente antes do commit;
sem publicação tardia. Fechar candidata pendente só remove seus próprios nós.

O owner mantém câmera e flags originais uma única vez. Commit valida existência
dos nós/configuração e troca desenho/câmera em um comandoLua. Só depois do
acknowledgement aceita novo owner/artefato,remove antigo e conserva o contexto
original para sair da vista. Se houver falha de confirmação,restaurar câmera,
flags e desenho anterior antes de reportar falha; registrar rollback não
confirmado se o motor estiver indisponível. Nunca anunciar aceite parcial.

Fonte/época/fase/artefato/view anteriores ficam preservados em cancelamento,
candidata incompleta e falha de acknowledgement. Mostrar/ocultar não muda
artefato; fechar restaura câmera/flags e remove nós do owner. Nenhum comando
altera órbitas,GM ou épocas.15s para inicializar candidata,limite do protótipo.

Teste nativo próprio com matemática/artefatos reais:criarSol,trocarTerra,
cancelar depois da criação real dos nós,rejeitar candidata com foco removido,
simular perda de ack depois de executar troca real e conferir rollback. Verificar
desenho/fase/artefato/câmera antes/depois,limpeza de pendentes e saída normal.
Não usar mocks como aceite nativo. Arquivar fontes antes de executar; nenhuma
captura nova é necessária para esse teste de protocolo,que não aceita visual
de produto ou desempenho. ProdutoUI/CEF/perfis continuam etapas futuras.
