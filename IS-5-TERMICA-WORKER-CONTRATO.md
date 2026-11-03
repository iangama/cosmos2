# IS5 — artefato/worker térmico,26/10/2026

Antes do código. Reusar por mérito protocolo/Store/client aprovados, em novos
arquivos próprios output/is5-thermal-worker-staging,sem alterar aceitos.
Referenciar ciência térmica isolada já validada; geração inclui EOS/rede/modelo,
fonteSolar arquivada e código do artefato. Tipos/kinds diferentes dos arquivos
de Tprescrita; nenhuma migração implícita ou reinterpretação de temperatura.

Configuração inicial conserva T0,rho,V,composição,gates/canais e basebeta.
Fonteorbital congelada;T,composição,U/pressão evoluem conforme contrato térmico.
Referência totalmente ligada com mesmas condições iniciais; se evolução real
ou referência sai do domínio,recusar cenário inteiro,preservando últimoaceito.
Nada de baixar duração/T ou extrapolar taxas para fabricar comparação.

Resumo pequeno e sonda0..240 incluem T,P,U,Cv,eta,composição,contagens,
potências e balançoEdisp/Enu/retido;curvas completas somente sob demanda.
Reprodução destes instantes não é integração em tempo real. Campos EOS/
reservatório não podem herdar o rótulo antigo de temperatura prescrita.

Artefato selado único conserva condições iniciais,fonte,solução/referência,
geração e vista. Restauração revalida fonte e recomputa soluções antespublicar;
comparar exato na mesma geração/runtime. UI/cena ficam para outra candidata.
Store próprio,32ramos com pai explícito,16MiB,locksWindows,recusas atômicas.
Guardasworker/artifact/token/revision e fila16mantidos;novo processo invalida
token,erro nunca publica solução parcial;quit encerra subprocesso.

Testar subprocesso real,sondaT/U/retido,configurar/restart,domínioquente
recusado sem mutação,save/load/newprocess/exato,ramos/flags/export,corruptelas,
guardas/tipos/versão antiga e locksWindows. Ciência e worker aceitos não
equivalem a aceiteUI/perfil,resposta hidrostática,transporte ou estrela real.
