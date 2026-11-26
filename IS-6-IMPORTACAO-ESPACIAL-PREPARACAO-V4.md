# Preparação v4 antes do perfil — 05/11/2026

P3 recusou antes do preflight porque o coletor novo traduz um desaparecimento
em ValueError, enquanto o executor v3 esperava exceções psutil antigas.
Criar executor v4, preservando v3 e seus recibos. A preparação pode repetir
fotografias completas por até 45 segundos, a cada segundo, e exige cinco
fotografias válidas consecutivas idênticas. Erro transitório reinicia a contagem;
registrar cada tentativa no recibo imediatamente, inclusive a causa nativa.
Ciclos, geração de fonte alterada e outros erros estruturais não são repetidos.
Uma tentativa que ultrapassa o prazo não é aceita mesmo se trouxe fotografia.

Essa espera ocorre somente antes da prévia pausada. O coletor, RAM e auditor
continuam os mesmos de P3 e recusam qualquer identidade ausente ou alterada
em coleta. Não eliminar candidatos do inventário nem aproveitar amostras
recusadas. Prévia pausada PDH e seu validador continuam obrigatórios antes das
quatro janelas. Plano novo deve selar helper, verificador e executor novos.
Nenhum limite de quadros, comandos, RAM, GPU ou cobertura temporal muda.
