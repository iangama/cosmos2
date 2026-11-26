# K4 — armazenamento e restauração de referências arquivadas

O envelope CPU original permanece congelado. A revisão 0.2.0 usa nomes
lógicos dos validadores em sua geração, com os mesmos hashes de código,
para permitir mudanças de diretório da candidata sem tratar caminhos como
alterações do modelo. Formatos/gerações diferentes continuam recusados;
não há migração implícita do envelope CPU 0.1.0 ou de saves espaciais antigos.

O armazenamento mantém latest, ramos e exportações na pasta da candidata.
Cada registro tem nome, ID, parentesco, data UTC de gravação, envelope e
checksum. Validar completamente antes de gravar; arquivo temporário único,
flush/fsync e substituição atômica. JSON duplicado/não finito, caminhos
inválidos, geração ou ciência divergentes não substituem registros anteriores.

Após reiniciar, a cópia solar viva tem novas identidades. A referência salva
conserva a fase científica arquivada; o proprietário de câmera/flags captura
os nós da cópia viva atual. Preparar e trocar ambas as referências em conjunto,
sem alterar a dinâmica viva. A interface deve identificar a referência como
arquivada e mostrar sua época. Falha de troca conserva a vista anterior;
fechar restaura câmera/flags da cópia viva, sem usar IDs gráficos obsoletos.

Esses novos caminhos exigem provas CPU, nativas, reinício e UI próprios.
Não transferir o perfil K3 para uma candidata com armazenamento integrado.
