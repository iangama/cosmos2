# IS6 — revisão0.18.2,02/11/2026

0.18.1 permanece congelada: nativoE aceito5grupos/10recusas/9PNG/zeroJS,
visualE aceito no escopo das9capturas,exit0. O suplemento de persistênciaA
com novo host passou6de7checagens: fase preservada,sonda exata,arquivo inválido
sem alterar câmera/artefato,CEF de ramos/export e dono íntegros. Falhou o
controle de corpo: ao restaurar uma fase arquivada,ID antigo não está nas
opções da fase atual,ficando vazio embora a legenda identifiqueSol.

0.18.2 adiciona opção arquivada explícita ao controle desabilitado durante
essa referência;ao fechar,reconstrói opções da fase atual. Não remapear o
artefato/fase antigos aos novosIDs. Provar restauração em outro host/fase.

Evitar trabalho repetido na publicação: digest/amostra imutáveis calculados
antes de commit,catálogo de ramos reutilizado enquanto nomes/tamanhos/mtimes
dos arquivos não mudam. Arquivo restaurado sempre passa pela validação e
recomputação científica completas; cache é só apresentação do catálogo.
Alterar um ramo invalida esse cache no próximo comando. Não duplicar a geração
do renderer ao montar resumo de cena. Guard/revisão/cancelamento/rollback e
ciência permanecem inalterados; serviço e nativo próprios obrigatórios.

Perfil ainda não executado. Medir nesta revisão após provas de persistência
e visual;manter limites deIS-6-PERFIL-PREVIO.md. Sem promoção nem aceite de
todaIS6,camadas simultâneas ou dinâmicaGR.
