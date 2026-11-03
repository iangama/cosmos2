# Verificação solicitada — gravidade e visualização

18/10/2026. Trabalho interrompido neste relatório, antes de retomar a auditoria
de desempenho e a instalação da versão 3.13, conforme pedido do dono.

| Item | Resultado medido |
| --- | --- |
| Gravidade em todas as direções | Aprovado para o monopolo newtoniano exterior: acima, abaixo e quatro lados apontam para o centro. |
| Cobertura numérica | 1.030 direções em dois centros, incluindo centro deslocado: 2.060 verificações em cada versão, instalada e candidata. |
| Intensidade | Mesmo raio produz mesmo módulo; dobrar a distância reduz a aceleração a um quarto. Erro relativo máximo: 2,094 × 10⁻¹⁵. |
| Movimento no simulador | Seis corpos, inicialmente em ±x, ±y e ±z a 2 × 10⁹ m do centro, chegaram todos a 1.938.110.275,578 m em t=0,7 unidades do modelo, com velocidade para dentro. Posições nativas coincidiram com a simulação. |
| Mostrar/Esconder campo | Aprovado em três ciclos completos pela interface CEF real. As seis camadas nativas responderam: vetores da casca, vetores do corte, borda e três equipotenciais. |
| Efeito de esconder o campo | Posições, velocidades, tempo, revisão e balanços físicos permaneceram iguais. O comando muda a visualização. |
| Referência de curvatura | Aprovado em três ciclos, com a interface instalada servida localmente dentro do CEF nativo: 72 sondas visíveis ao ligar e zero ao desligar; o resultado físico permaneceu idêntico. |
| Atuação física e desvio da luz | Desligar Atuação ou o efeito de desvio suprimiu o termo de curvatura aplicado; religar restaurou-o. A referência visual continuou independente. |
| Botão de malha espaço-temporal | Ausente na interface atual. Há campo vetorial, equipotenciais e sondas de curvatura/relógio; não há uma malha espaço-temporal deformada com botão próprio. |

O teste de atração radial cobre uma fonte esférica no modelo exterior. J2,
marés e outras fontes podem acrescentar componentes que não apontam para o
centro de um único corpo. O teste não valida o interior material de um planeta.

## Ocorrências registradas

A primeira checagem de visibilidade interpretou incorretamente uma tabela Lua
de booleanos: o motor retorna um objeto JSON com chaves numéricas. O teste
percorria essas chaves, em vez dos valores. Corrigido o leitor do teste, os seis
valores nativos alternaram corretamente nos três ciclos. Não houve alteração
no código do produto.

Durante a limpeza da primeira tentativa, o motor encerrou e produziu um dump.
O log contém quadros do driver AMD, mas isso não estabelece a causa. A nova
abertura concluiu os testes e a restauração sem repetir o encerramento.
Essa ocorrência permanece uma pendência de estabilidade, sem atribuição de causa.

A tela Forças fundamentais da candidata isolada não carregou por procurar um
arquivo científico sob `output/c211-cloud-product/data/science`, onde ele não
existe. Os testes de curvatura descritos acima usaram os arquivos da versão
instalada, por servidor temporário na porta 4715 e dentro do CEF real. Esse
resultado não aprova a abertura dessa tela na candidata isolada. Registrar e
resolver a localização dos dados ou verificar o caminho final durante a
retomada; não ocultar a falha com o resultado da versão instalada.

A sessão salva do dono foi preservada byte a byte, SHA256
`ee9c4cc86e0696afde128ec319f98f6ad5b3932f27f8b5bd6a25d57a4025b825`.
Nenhuma promoção da candidata foi executada. O perfil P256 c211p256c2 terminou
as três janelas, mas a auditoria formal fica para depois deste relatório.

## Evidências

- [Gravidade da versão instalada](evidence/requested-gravity-installed-20261018.json)
- [Gravidade da candidata](evidence/requested-gravity-candidate-20261018.json)
- [Movimento nativo e botão de campo](evidence/requested-gravity-recheck-20261018-native-check.json)
- [Controles de curvatura da interface instalada](evidence/requested-spacetime-installed-controls-20261018.json)
- [Primeira tentativa e encerramento](evidence/requested-controls-first-attempt-20261018.json)
- [Falha de carregamento da candidata](evidence/requested-spacetime-candidate-controls-20261018.json)
- [Campo ligado](evidence/cosmos2-requested-gravity-recheck-20261018-field-on.png) / [desligado](evidence/cosmos2-requested-gravity-recheck-20261018-field-off.png)
- [Referência de curvatura ligada](evidence/cosmos2-requested-spacetime-reference-on.png) / [desligada](evidence/cosmos2-requested-spacetime-reference-off.png)
