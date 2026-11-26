# C2-14 — cancelamento com configuração preservada

Antes de dados novos, a revisão 0.28.2 corrige uma referência compartilhada no JavaScript. Após um resultado completo, config apontava para response.configuration; a próxima edição podia modificar a configuração do resultado preservado antes da conclusão do novo job. A revisão clona a configuração concluída, restaura controles/formulário após cancelamento e exporta a configuração efetivamente mostrada quando há resultado C2-14.

Núcleo, serviço, HTTP, dados científicos e símbolos da revisão B permanecem idênticos. A e B ficam imutáveis com seus recibos originais. O aceite B cobriu preservação do fingerprint físico e não a independência do objeto de configuração. O teste novo exige identidade do JSON completo do último resultado após cancelar, além de igualdade de condições do formulário/configuração com esse resultado. Repetir o nativo e as quatro capturas no novo produto.

Para o futuro perfil, a versão 0.28.2 substitui somente a referência à candidata 0.28.1 no contrato. Os limites, as quatro janelas e a receita técnica permanecem. Não coletar perfil antes dos novos aceites e da verificação das recusas.
