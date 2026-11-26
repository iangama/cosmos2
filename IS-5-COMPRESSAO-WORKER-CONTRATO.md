# IS5 — trabalhador da zona com trabalho externo,29/10/2026

Contrato de implementação após aceite integral da evolução. Basear novo
estágio de trabalhador no V2 Coulomb aceito, sem editar esse estágio, suas
fontes, os produtos0150/0160 ou qualquer sessão anterior.

Artefato e checkpoint têm espécie própria de zona com densidade prescrita,
incompatível com os tipos anteriores. Parâmetros iniciais, história deρ,
gates/canais,EOS e screening são configuração exata e selada. Saída guarda
trajetória completa deρ,V,T,Y,extensões/contagens,energia total e por volume,
Q/Qν/Qretido,W e potências com unidades explícitas. Sonda usa só índices
calculados0..240. Não reinterpretar joules antigos comoJ/m³ nem migrar
silenciosamente um checkpoint isocórico.

Processo auxiliar isolado,Python real com−S/bibliotecas fixadas eJobObject
KILL_ON_JOB_CLOSE; PID real conferido,sem threadPython de vigilância. Manter
state e quit responsivos,uma operação mutável admitida e respostas porID.
Em falha,prazo ou domínio,o filho deve encerrar antes da resposta e não
publicar resultado tardio. Artefato/fonte/view anteriores permanecem válidos.

Primeiro cálculo científico Radau mediu171,239s no caso de compressãoN14
completo. Esse dado não é um compromisso de velocidade do produto nem mede
duas redes. Orçamento operacional inicial:600s por operação de cálculo,
transporte660s. A ponte de produto futura deve exceder esse prazo; espera
e cancelamento ficam explícitos. Não aumentar limites físicos/tolerâncias
para reduzir tempo. Prazo de teste menor só força a recusa operacional,
sem mudar configuração científica. Medir duração e responsividade reais.

Referência completa compartilha os mesmos parâmetros iniciais,história,
EOS e screening; varia apenas atuação/canais. Quando as duas redes são
idênticas,pode reutilizar a mesma solução completa validada. Alterar só
visibilidade/índice não recalcula nem altera digest. Ler/salvar/exportar
preservaρ/V/E/W e toda a procedência; restaurar em outro processo valida
fontes,geração,selos e modelo antes de assumir o artefato.

Aceite próprio:criação física,constant/compressão/expansão/cycle,gates e
EOS/screening separados,índices0/120/240/curvas,baryon_count fixo e balanço
Δ(VU)=Qretido+W. Canais desligados não removem o trabalho externo. Testar
fatores,energia com sinal,save/load/ramos/novo processo/exportação,32ramos,
locks transitórios/permanentes Windows,arquivo adulterado/tipo antigo/
campos e guardas inválidos. Medir state≤1s/recusa concorrente≤2s/quit≤2s
durante cálculo e prazo reduzido sem substituição do último resultado.
Morte abrupta do dono deve encerrar o auxiliar peloJobObject. Arquivar
fontes e entradas antes de executar; não reutilizar aceite do trabalhador0150.

Nenhum aceite de interface,desempenho nativo,hidrostática,transporte ou
gravidade dinâmica é inferido deste protocolo. Produto exige contrato,
candidata isolada,CEF/visual/perfis próprios após trabalhador aceito.
