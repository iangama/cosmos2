# Percurso 0.27.0 — serviços científicos antes da janela

Contrato de 13/11/2026, anterior à execução. Preservar a candidata 0.27.0,
seu inventário e todos os executores anteriores. A cópia da aplicação segue
byteidêntica à 0.26.2. Usar somente armazenamento novo sob output.

Um worker orbital real cria e salva os 16 centros na época fixada
2026-10-11T12:00:00Z. Criar depois a cópia4 na mesma época; manter essa fase
pausada, incluindo identidades, época, posições, velocidades, GM, origem,
revisão e intervenções durante todos os instrumentos. Restaurar16 ao final
exatamente, renovando apenas a identidade de edição prevista pelo leitor.

A receita magnética, de espécies e nuclear vem do journey-inventory.json
selado. Fixar também o ângulo da partícula em60graus e quatro comandos
de64passos, conforme os controles já existentes. Os parâmetros iniciais
devem ser calculados pelo método real ParticleLaboratory._initial a partir
da leitura real IGRF14/JRM33. Workers de partículas reais executam, amostram,
salvam, retomam e recusam guard antigo. A fase local, o tempo independente,
os controles, a origem e o futuro de mais64passos devem coincidir exatamente
após reabertura em outro worker. Exercitar o Store real, ramo/filho e
visibilidade separada da ciência. Não simular sucesso de renderização.

Para Terra e Júpiter, recomputar malha e amostra magnética reais, admitindo
o par pelo contrato atual. Malha simples65×96,1–8Rref,planoXY,ampliação200;
par composto65×96,1–3Rref,planoXY,ampliação200. Salvar/restaurar no Store
atual do produto, ramo/filho/exportação e quatro visibilidades, conservando
os mesmos bytes científicos. Trocar população ou fase da referência deve
ser recusado antes de gravar. Esta parte verifica ciência/armazenamento;
a posse e limpeza da cena ficam para a jornada nativa posterior.

O Client/worker nuclear real calcula a configuração prescrita selada com
18canais,forte/fraca/EM ativos,Coulomb/screening. Consultar120/121, salvar,
restaurar,ramificar/filho,exportar e reabrir em outro processo, exigindo
artefato/amostra/origem exatos. Ocultar neutrinos conserva o artefato.
Recalcular com fraca desligada cria outro artefato; restaurar o original.
Usar os limites existentes600s/cálculo,660s/transporte,750s/jornada;
nenhuma dessas durações constitui medição de desempenho.

Recusar fontes16 nos instrumentos4,guarda orbital antiga após restauração,
guardas antigas de partícula/zona e arquivos orbitais interpretados como
referências compostas ou partículas. Verificar estado confirmado e bytes
dos arquivos após recusas. Selar configuração,execução,fontes e dependências
antes dos cálculos. Gravar recibos progressivos e conservar falhas.

Sem alteração numérica, não repetir a comparação orbitalCPU30dias nem os
perfis anteriores. Este ensaio não aceita interface,câmera,nós,imagens,
residência conjunta,IS6 ouV1. Não instalar,promover,enviar aoGitHub ou
editar sessões/favoritos/atalhos do dono. Não usar subagentes.
