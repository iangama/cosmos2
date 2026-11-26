# IS6 — artefato da malha e persistência, contrato prévio01/11/2026

Após ciênciaC e fontesA aceitas, criar estágio próprio
`output/is6-spatial-artifact-staging`. Preservar modelos/receitas/aceites
anteriores; não criar produto nativo por esse estágio. Reutilizar por mérito
conceitos de arquivo selado/rename atômico já verificados, com tipo novo.

Artefato imutável:IDhex32,geração própria/científica, fase solar arquivada,
binding de corpo, configuração completa e malha exata. Configuração contém
limites radiais em múltiplos de Rref,33/65/129/257anéis,96setores,orientação
ortonormal e ampliação vertical0–1000. Múltiplos finitos:1≤interno<externo≤100;
domínio SI continua o científico. Centro vem do corpo, nunca de input gráfico.
Default65anéis,96setores,1–8Rref,planoXY e ampliação200 explícita.

View separada:visible bool,índices radial/azimutal inteiros em0..N−1 e
índice radial do observador receptor. Sonda lê raio calculado do anel escolhido,
métrica/K/relógio,comprimento próprio desde o limite interno e comparação
emissor selecionado/receptor escolhido. Posições físicas e exibidas ficam
relativas à fonte; a ampliação não altera a leitura intrínseca. Ocultar malha
ou mover sonda não recalcula nem muda o artefato.

Checkpoint JSON limitado16MiB:tipo/schema exclusivos,artefato+view juntos,
ramo/linhagem e SHA256 de conteúdo canônico. Recusar arquivos antigos,campos
extras,NaN,bool indevido,chaves duplicadas,seal/geração/binding/valores alterados.
Na restauração, verificar origem e geração, recalcular a malha e comparar tudo
exatamente antes de devolver candidato. Nunca promover parcialmente view ou
artefato se falhar. Exportação inclui payload/procedência exatos.

Salvar atômico com temporário novo,fsync e replace; preservar registro anterior
em falhas. Até32ramos,IDshex32,nome1–80caracteres,parent existente ouNone.
Checkpoint principal deve guardar explicitamente o pai de linhagem:novo
processo não pode esquecê-lo porque o arquivo principal não é um ramo. Novo
ramo usa o pai atual e passa a ser o pai das próximas alterações. Nenhum input
de arquivo pode escolher caminhos fora da pasta de trabalho sob output.

Aceite prévio:quatro corpos e1–8Rref contra binding/malha aceitos; índices
iniciais/intermediários/finais,visibilidade e ampliação independentes; inputs
e outputs não compartilham dados mutáveis. Criar/restaurar default e resolução
máxima≤2s por operação em Windows; medir antes de aceitar. Save/load/ramos/
novo processo/export idênticos,32ramos,recusa33 e nomes/IDs/pais inválidos.
Adulterações de seal,tipo,geração,época,configuração,view e um vértice são
recusadas; janela principal permanece byte a byte em tentativas recusadas.
Testar duplicatas,budget e atomicidade sob bloqueio Windows. Arquivar código,
contratos,fixtures e limites antes da execução. Não inferir aceite de ponte,
CEF,cena,visual,perfil ou toda IS6.
