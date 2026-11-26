# Marés de equilíbrio: pesquisa pontual, sem integração

J2 exterior está instalado na3.9; marés materiais ainda não. Referências
primárias e hashes em reference.json, sem instalar REBOUNDx ou copiar código.

Próximo: conferir Eggleton1998 eq31/33 e a convenção Love k2 versus constante
apsidal k (k2=2k). O PDF Lu2023v1 eq7 contém termo estático6Gm/d8; o C pinned
5.1.0 usa3Gm/d8, com potencial -Gm²k2R⁵/(2d⁶). Não afirmar equivalência sem
resolver essa diferença. Distinguir potencial de interação com quadrupolo
prescrito, derivada com quadrupolo fixo e energia efetiva após resposta induzida.

Lu eq1 relaciona tau e sigma; eq4 dá Q^-1~2n*tau apenas no limite indicado.
Não usar a fórmula tipograficamente inconsistente da documentação online.

O candidato deverá evoluir spin com inércia SI e reação de torque, contabilizar
calor não negativo, usar energia mecânica+reservatório e L órbita+spin, preservar
unidades/procedência e checkpoint das variáveis adicionais. Começar com2corpos,
resposta quadrupolar pequena e domínio exterior explícito. Não converter spin
cinemático existente em estado material automaticamente. Não combinar J2 de
eixo prescrito com spin material evoluindo sem contrato consistente de eixo.
Verificar gradiente, trabalho+calor, torque, rotação, sincronismo, convergência
DOP853 e casos de referênca antes de promover qualquer operador ao produto.

## Convenção candidata resolvida por referências independentes

Usar **Love potencial k2**, duas vezes a constante apsidal, como definido em
Ragozzine & Wolf2009, eq1/5/6. Energia efetiva induzida por uma maré:
Ueq=−G k2 m² R⁵/(2r⁶); sua força radial é −3G k2 m² R⁵ r/r⁸.
A metade inclui o custo da resposta induzida. A energia de um quadrupolo
prescrito inteiro contra o companheiro é outra grandeza. A precessão esperada
é (15/2)k2 n(m/M)(R/a)⁵(1+3e²/2+e⁴/8)/(1−e²)⁵ por corpo deformável.

O atraso τ usa segundos na convenção de Leconte2010, eq5/9 e apêndiceA:
com r do corpo deformável ao companheiro, v relativo e u=v−Ω×r,
Fd=−3G k2 m² R⁵ τ/r¹⁰ [2r(r·v)+r²u].
Torque no spin=−r×Fd; calor=−Fd·u≥0. Assim, Eórbita+Ueq+I|Ω|²/2+calor
e Lórbita+IΩ são os balanços. Essa normalização produz, na órbita circular,
I dΩz/dt=3G k2 m²R⁵τ/r⁶(n−Ωz), sem fator2 adicional.
Em excentricidade/obliquidade gerais, conferir médias completas Leconte,
sem usar série truncada em e² para calcular a evolução.

Não afirmar que eq7 de Lu2023 e o operador C pinned sejam equivalentes;
o candidato escolhe a convenção acima e deve ser identificado por ela.
Sem conversão automática Q↔τ, sem bulbo rotacional ou resposta térmica do raio.

## Campo de um snapshot material — derivação candidata

Q é o tensor de segundo momento sem traço, em kg m². Defina n=r/r,
A=k2 m R⁵/r³ e vr=n·v. Resposta atrasada de primeira ordem no referencial
material, transformada aos eixos inerciais:
Q=A[(1+5τvr/r)nn −(1+3τvr/r)I/3 −τ(un+nu)/r].
Para um ponto x exterior, Φq=−3G(x·Qx)/(2|x|⁵). Derivar g e T deste mesmo
potencial com Q congelado. No companheiro, m g coincide com Feq+Fd.
Uma leitura passiva não induz outra resposta; não há reação de sonda.
Ueq da evolução é separado desse potencial específico de snapshot.

Guardas propostas: dois corpos ativos, deformação pequena, atraso pequeno,
Ω²R³/(GM) pequeno, separação exterior. Limites são políticas do candidato,
não precisão universal comprovada. h2/deslocamento de superfície exigem
parâmetro/prova próprios; k2 sozinho não define material nem altura superficial.

## Integração ainda por decidir

REBOUND5.2.2 integrator_bs.c documenta que ODEs de usuário usam BS. Quando o
N-corpos usa BS, trata tudo como sistema conjunto; IAS15 mais ODEs de usuário
não fornece automaticamente o mesmo acoplamento. Não anexar spin como se
IAS15 já o integrasse nos estágios nem reutilizar aceite pontual/J2 para isso.
Primeiro validar o kernel e oráculo conjunto isolados. Qualquer contrato
numérico material diferente deve ser explícito e provar persistência completa.

## Núcleo isolado implementado — 15/10

equilibrium_tide.py e scripts/verify-equilibrium-tide-kernel.py passaram.
Campo do quadrupolo atrasado contra a força ativa difere1,551e-16;
trabalho órbita+spin+calor fecha3,614e-16. Gradientes de Φ/g/Ueq≤8,553e-10.
Covariância rotacional3,289e-16. Atraso zero elimina calor/torque; órbita
circular síncrona não aquece. Médias completas Kepler e=.1/.3/.6 com média
apsidal/obliquidade batem Leconte2010≤7,295e-15 e taxa de precessão estática
RagozzineWolf2009≤1,840e-15. Isso confere a normalização escolhida, não
resolve as discrepâncias de notação dos demais artigos.

Guardas: maré pequena≤.01, atraso adimensional≤.05, rotação≤.01,
separação exterior, velocidades≤3e6m/s e G(M+m)/(rc²)≤1e-6. São limites
de domínio deste candidato. A matrizQ e o campo passivo ficam separados da
energia efetiva induzida. Sem h2, superfície, bulbo rotacional, térmica ou J2.
O teste torque usa |r||F| como escala de cancelamento da força total: o termo
radial é muito maior que o torque dissipativo. Não dividir só pelo torque
pequeno e exigir precisão além do arredondamento dos operandos.

Dinâmica conjunta em scripts/verify-equilibrium-tide-dynamics.py: DOP853 e
Radau sobre as mesmas equações verificadas,20órbitas, spin dinâmico e calor.
Conferir recibo próprio. Isso não comprova acoplamento/cache de REBOUND;
nenhum solver do produto mudou.

## Dinâmica conjunta e persistência candidatas — 16/10

Refinamento DOP85340→120passos/órbita passou contraRadau1e-13 em20órbitas:
erro final8,801e-8→3,028e-12. Energia+calor fina4,085e-14 eLtotal1,830e-14.
Recibo tides-dynamics-prototype-check.json; falhas anteriores preservadas.

material_driver.py escolhe uma única ODE de10dimensões (órbita relativa,
spin ecalor) emBS5.2.2 com tolerâncias absolutas/relativas1e-13 e escalas
adimensionais próprias. Não depende da ordem de callbacks entre ODEs.
Centro de massa é analítico. A simulação de partículasIAS15 é somente espelho
confirmado para instrumentos/cena, nunca avançada no modo material.

O arquivoBS sozinho omite ODEs. O candidato sela o vetor e as escalas junto
combinaryBS e religa somente callback conhecido. Prova isolada passou futuro
exato em3alvos,20órbitas E+calor1,963e-13/Ltotal7,760e-14 eBSvsDOP853 deRHS
independente3,008e-11.12corrupções/domínios recusados; trial que cruza domínio
exterior não publica fase nemcalor inválidos. Sem aceiteSession/worker/CEF.
Cópia de integração emoutput/c211-tides-product/app; produto3.9.1 preservado.
