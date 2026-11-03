# IS5 — perfil próprio Coulomb0.15.0,29/10/2026

Contrato registrado antes da medição. Exigir recibos CEF e visual próprios
aceitos, com hashes atuais do aplicativo, ciência e trabalhador conferidos.
Quatro janelas: fraca ligada/desligada × gráficos visíveis/ocultos.
Configuração:15MK/rho1,5e5/H0,34/CNO0,01/O16/10kyr/1m³,modoisochoric,
Coulomb e screening ligados,18canais habilitados,βNUBASE2020 fixa.
As soluções térmicas são calculadas antes de cada janela; medir somente
reprodução de instantes, interface, IPC e cena, sem throughput do integrador.

Cada janela tem30s de aquecimento e60s de quadros SGCT,1920×1080,
CEF100%,2instantes calculados/s. body.inert somente ao aquecer/medir;
gráficos continuam renderizados. Sem outros testesCPU concorrentes.
LimitesG0 inalterados:mediana16,7/p9525/p9950ms/zero intervalos>100ms,
RAM8GiB/GPU5,5GiB,ritmo medido/solicitado entre0,9e1,05.
Usar todos os intervalos após o primeiro, sem eliminar picos.

Fonte orbital pausada e fase imutável; marcador e rótulo arquivados visíveis.
GPU66amostras cobrindo integralmente UTC de cada janela; inventário de
processos próprios e RAM/DXGI em0/20/40/60s. ExpectedWorkerpaused refere-se
ao trabalhador ORBITAL; trabalhador Coulomb separado permanece reproduzindo.
Guardar resultado completo e digest antes do aquecimento. Conferir geração,
guardas, fonte, flags/cena, curvas e valores por índice antes de aceitar.

Auditoria independente confere24estados×2redes×(15escalares+2×16espécies+
2×18canais+18fatores)=4848valores exatos. Inclui U_Coulomb negativo e
screening de cada canal;4β eBe7EC fator adicional1. Verifica conservação
ν=e+produzidos+e−capturados e νatual=0 quando fraca desligada.
Não usar esse último caso para exigir fatores de screening iguais a1:
eles descrevem o plasma, enquanto gates determinam taxas efetivas.

Arquivar aplicativo, dependências científicas transitivas, dados/licenças,
recibos, receitas, auditor, motor e ponte de perfil antes de medir.
Conferir sessão candidata própria e ponteiro de sessão do dono inalterado.
Auditor recalcula percentis, ritmo, relógios, memória e todos os limites;
falha de qualquer janela reprova o conjunto, sem afrouxar o contrato.

Não herdar perfil0140 nem alegar calibração observacional, estrutura solar,
transporte, MHD, ionização parcial ou correções quânticas iônicas. O perfil
aceita apenas esse percurso de reprodução da candidata0.15.0, sem promoção.
Encerrar host normalmente por toggleShutdown e arquivar logs.
