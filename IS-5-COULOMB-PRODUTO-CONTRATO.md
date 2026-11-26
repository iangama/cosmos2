# IS5 — candidata Coulomb0.15.0, contrato29/10UTC(28/10local)

Fork isolado de0.14.0 após aceite do trabalhador Coulomb. Armazenamento
próprio, sem promoção. Preservar código/evidências da ciência, trabalhador,
candidatas e instalação3.13; não restaurar fontes de runtime alteradas
intencionalmente. Não adicionar dependência de rede ao cálculo.

Instrumento térmico isocórico, condição padrãoN14/15MK/10kyr, sementeO16
selecionável, lei Be7EC10<T/MK<16. Modelo PC de íons clássicos, ideal FD
não relativístico e radiação confinada; β fixoNUBASE2020 neste recorte.
Remover o seletor wc12, pois esse modelo não oferece essa variante.

Adicionar controles separados de Coulomb na EOS e screening de fusões.
Screening exige Coulomb; desligar Coulomb desmarca e desabilita screening.
Religar Coulomb mantém screening desligado até escolha explícita. API
continua recusando combinação inválida e não ignora parâmetros enviados.
Gates forte/fraca/EM continuam controlando canais, com p+p permitido em
EMoff; as opções da EOS são próprias. Referência completa usa MESMAS
opções de EOS/screening e parâmetros, variando apenas gates/canais.

Sonda mostra U_Coulomb com seu sinal, fatores adicionais p+p/N14p/O16p e
tabela dos18 canais sob demanda. Quatro β e EC têm fator adicional1;
explicar que a lei de plasma de Be7EC permanece. Novo gráfico de U_Coulomb
com eixo vertical que admite valores negativos, sem cortar valores em0.
Ocultar energia esconde também esse gráfico, sem alterar a física. Manter
todos os gráficos e formatos de resíduos CNO/ppIII aceitos.

Durante cálculo, mostrar espera explícita inclusive na abertura da zona.
Processamento deve ficar fora da renderização. Ponte nativa usa prazo
maior que240s do cálculo/300s do transporte; admitir somente um comando
mutável por vez para evitar pedidos enfileirados que publiquem após erro.
State deve continuar respondendo. Fechamento normal exige cliente/worker/
filho encerrados, nenhum arquivo/cenário do dono sobrescrito.

CEF: criar padrão pelo formulário, comprovar18 controles/sondas/fatores,
alterar Coulomb e screening separadamente, sementeO16 e um canal de captura,
guardar/restaurar/ramos/novo processo/exportar, índices0/120/240 e curvas,
recusas de tipo/gate/generation/source/mode/combinação inválida mantendo o
último artefato. Mudança de estado busy não pode aceitar cálculo concorrente.
Não herdar timeout45s de testes antigos: medir espera de cálculo e o percurso
completo, com limites explícitos.

Capturas originais100/150% devem comprovar marcador/rótulo do Sol arquivado,
modelos e controles legíveis, sinal de U_Coulomb, fatores e tabela, além
dos gráficos de composição existentes. Conferir pixels originais caso o
preview omita camadas. Zero errosJS. Perfil próprio4janelas somente após
funcional/visual aceitos, sem testesCPU concorrentes. Sem herdar perfis0140.

Escopo continua sem correções quânticas iônicas, ionização parcial, MHD,
transporte, estrutura, luminosidade superficial ou calibração observacional.
Precisão numérica e fidelidade física precisam continuar distintas no produto.
