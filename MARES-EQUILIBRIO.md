# C2-11 — maré material de equilíbrio, produto3.10

Instalada localmente em16/10/2026. Ciência, Session, worker, migração e jornada
CEF passaram. Perfil formal próprio aprovado e auditado em c211tides1; recibo c211-tides-validated.json.
C2-11 continua parcial: ressonâncias e perfis256/10mil permanecem pendentes.

## Modelo físico e parâmetros

Exatamente duas massas ativas: uma esfera deformável isotrópica e um
companheiro pontual. As duas gravitam, com reação linear da força de maré.
Raio material R, Love potencial k2, atraso τ em segundos, inércia I emkg·m²,
spin material inicial emrad/s e procedência são explícitos. Nenhum planeta ou
spin cinemático recebe material automaticamente. Há um par didático sintético
na interface, identificado como modelo e sem identidade observacional.

Normalização: Love potencial k2 é duas vezes a constante apsidal. A resposta
induzida tem energia efetiva Ueq=−Gk2m²R⁵/(2r⁶), distinta da energia de um
quadrupolo prescrito inteiro. A força elástica é−3Gk2m²R⁵r/r⁸.
Comu=v−Ω×r, a força dissipativa é
−3Gk2m²R⁵τ[2r(r·v)+r²u]/r¹⁰. O torque no spin é−r×Fd e
o calor produzido é−Fd·u≥0. O kernel compartilhado também fornece o tensorQ
induzido atrasado; seu potencial congelado determina g e o tensor de campo
das sondas. Uma sonda passiva não induz outra deformação nem exerce reação.

O tensor de campo mede aceleração diferencial. k2 sozinho não define h2 ou
altura de superfície. Esta versão mantém raio e inércia fixos, contabiliza
calor sem converter em temperatura/expansão e não modela bulbo rotacional,
interior ou relevo. Raio geométrico e orientação cinemática continuam
independentes. J2 com eixo prescrito não pode coexistir com este spin dinâmico.
Sem conversão automática Q↔τ e sem equivalência presumida com notações deLu2023.

Domínio declarado do candidato: deformação≤0,01, atraso adimensional≤0,05,
rotaçãoΩ²R³/(GM)≤0,01, separação exterior, movimento lento e campo fraco.
Esses limites são políticas do modelo, não uma precisão universal demonstrada.
Tentativa de sair do domínio rejeita o trial e pausa na última fase válida.

## Integração e persistência

Uma única ODE de dez coordenadas adimensionais contém posição relativa,
velocidade relativa, spin e calor. REBOUND5.2.2/BS avança todos nos mesmos
estágios, com eps_abs=eps_rel=1e−13. O centro de massa segue movimento
inercial analítico. O objeto de partículasIAS15 é somente espelho confirmado
para instrumentos e cena; IAS15 não avança enquanto material está ativo.
Não usar o aceite de IAS15 para caracterizar este contrato numérico diferente.

O arquivo nativoBS não serializa ODEs de usuário. O checkpoint sela também
vetor, escalas, parâmetros, fase inicial, origem e referências, e religa apenas
o callback conhecido. A restauração valida escalas/referências reconstruídas
da origem inicial, fase confirmada e histórico de ativações. Consultar ou
salvar não reinicia o solver. Trial é isolado e só publica estado validado.

Energia auditada inclui translação, resposta induzida, spin e calor; L inclui
órbita mais spin. Ativar/desativar registra energia e momento externos,
incluindo a retirada do reservatório. Desative explicitamente antes de editar
fase/massa/topologia ou parâmetros materiais. Arquivar/restaurar mantém spin,
calor, histórico e solver. Comparação de ramos sinaliza hipóteses materiais
distintas e nunca alinha instantes diferentes por índice/interpolação.

## Evidências

- Kernel: gradientes, campo/força, torque, trabalho/calor, sincronismo e médias
  completas de órbitaKepler. Referências independentes Ragozzine &Wolf2009 e
  Leconte2010; hashes e bibliografia emoutput/c211-tides-staging/reference.json.
- Dinâmica20órbitas: BSfechaE+calor em1,963e−13 eLtotal em7,760e−14;
  diferença final normalizada3,008e−11 contraDOP853 comRHS independente.
  DOP853 refinado converge contraRadau1e−13. Recibos tides-dynamics-prototype-check
  e tides-bs-installed-check. Retomadas futuras exatas em três alvos.
- Session:24guards e6corrupções seladas, além de12domínios/corrupções do driver;
  histórico16registros, campo/sonda/força coerentes e ramos restaurados exatamente.
- Worker:6leituras ao vivo,20pausas≤16,600ms no ensaio instalado, stderr vazio.
  Não confundir essa medida curta com perfil de quadros.
- CEF: preset/formulário SI na identidade oposta, mapa337pontos, histórico,
  salvar/carregar e ramos; zeroerros. Captura cosmos2-tides-material.png revista.
- Dez arquivos reais schema1/3.8/3.9.0/3.9.1 migrados em cópias; originais e
  ponteiro do dono preservados. O hash de definição inicial do legado é uma
  declaração de origem preservada, sem alegar reconstrução pelo código atual.

Backup anterior:output/c211-pre-tides/app. Recibo de promoção com mudanças
posteriores:evidence/c211-tides-promotion.json. Perfis históricos3.9.1 permanecem
congelados; não atribuir seus números à3.10.

## Perfil formal aprovado3.10

c211tides1:3×60s após30s de aquecimento,1920×1080, duas massas ativas com
maré material,16sondas a0,25s,128registros, gráfico de2sondas e569amostras
congeladas. p95≤13,963ms/p99≤14,424ms, zeroquadros>100ms; ritmo≥0,98492u/s
para pedido1u/s.20pausas≤47,664ms. Energia auditada≤4,061e-14/Ltotal≤1,891e-14.
RAMsoma≤1,05463GiB;WDDMsoma≤2,96940GiB;DXGIbudgetmínimo7,19014GiB.
As somas de memória podem contar alocações compartilhadas repetidamente.

Fontes atuais conferidas byte a byte contra a coleta; arquivo de fontes
SHA256c1bad16bc36a3c7079304bcf756a546f08b9e683017e88e5f27bf547fab3c7f7.
Backup aprovadooutput/c211-tides-validated/app. Perfil exclusivo de2massas;
não prova128/256/10mil ou encerramentoC2-11. Nenhuma outra coleta ou teste
científico se sobrepôs às três janelas formais.
