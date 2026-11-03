# IS5 — perfis solares na interface,contrato29/10/2026

Próxima etapa após aceite próprio funcional,visual e de desempenho da
candidata Coulomb0.15.0. Criar candidata0.16.0 isolada,sem promoção nem
alteração de0.15.0,dos dados B23 e das fontes científicas aceitas.

O plano C2-20 requer comparação com perfis estelares de referência. Os
perfis B23v1.2 e a comparação EOSideal já foram importados/auditados,mas
hoje estão em arquivos e figuras. Disponibilizar uma consulta radial
interativa desses resultados na interface,sem novo cálculo evolutivo.

O instrumento deve identificar Herrera/Serenelli,GarStEC,B23v1.2 e DOI
10822316. Oferecer as seis composições já importadas,2001linhas por modelo,
sem interpolar,renormalizar frações ou inicializar a zona calculada.
Raio selecionado por índice0..2000,com r/Rsun tabulado,temperatura,
densidade,pressão,ne livre e abundâncias originais. Curvas de T/rho/P
contra r/Rsun devem indicar unidades,escala e ponto selecionado.

Preservar e mostrar flags de qualidade. As três amostras centrais excluídas
da comparação EOS continuam consultáveis e identificadas como tal.
Auxiliares assinados de neutrinos/dm não são produção local calculada;
não convertê-los em fluxo da zona. Não apresentar modelos GarStEC como
dados observados ou resultados evoluídos pelo Cosmos2.

Para GS98/AGSS09,mostrar o intervalo ideal A≥1 exatamente como auditado
em713pontos,sem recalcular EOS. Demais modelos/linhas sem resultado têm
ausência explícita. Não estender esse intervalo a Coulomb: a correção
aceita exige composição iônica neutra totalmente ionizada; a tabela não
fixa todos os isótopos e estados de ionização. Não atribuir exclusivamente
a Coulomb a diferença de1,7–2,3% da comparação ideal anterior.

Backend somente leitura,com modelo e parâmetros estritos. Empacotar cópias
dos JSONs aceitos e manifesto com hashes/procedência; conferir antes de
servir. Não importar bibliotecas científicas nem integrar ODE em GET.
Consulta não altera órbita,artefato nuclear,ramos ou sessão do dono.
Sem dependência de rede para abrir os perfis; link DOI é informativo.

Verificação de dados compara integralmente12006linhas com os arquivos
aceitos e713intervalos com a auditoriaB. Cobrir seleções inválidas,arquivos
alterados,flags centrais,limites de índice e modelos sem intervalo.
CEF seleciona modelos e raios,confere números/unidades/procedência,
abre/fecha consulta com e sem zona ativa e confirma cena/fonte imutáveis.
Rever PNGs100/150%,navegação por teclado,rolagem e curvas sem cortes.
Zero errosJS. Perfil próprio com a consulta visível e seleção radial ativa;
não herdar automaticamente desempenho da candidata0.15.0.

Esse instrumento amplia o acesso a comparações já aceitas; não acrescenta
hidrostática,transporte,luminosidade evoluída,calibração ou EOS de ionização
parcial. IS5/C2-20 continua sem aceite integral por essa etapa isolada.
