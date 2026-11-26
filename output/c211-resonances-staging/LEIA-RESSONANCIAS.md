# Instrumento de ressonância — preparação isolada, 16/10

O produto3.10 material está em medição formal. Nenhum código deste diretório
está instalado, e nenhum teste científico deve rodar junto com suas janelas.

## Contrato proposto

Um quociente de períodos perto de2:1 não basta para declarar ressonância.
O instrumento deverá expor períodos osculantes relativos ao MESMO primário,
ângulos críticos, duração e cadência física da janela. Não criar forças de
“ressonância”: as massas já interagem pelo integrador aprovado.

Primeira fatia: dois orbitadores ligados, prógrados e coplanares em torno de
um primário explicitamente selecionado. Razões de primeira ordem j:(j−1),
j=2…9. Referencial do plano definido por normal+direção de referência,
persistido. Os IDs e o mesmo snapshot confirmado devem definir todos os dados.
Fases astrocentricas, não elementos Jacobi implícitos. Cada par usa
mu=G(Mprimário+Mcorpo). Exibir esse contrato; não tratá-lo como ação canônica
de um Hamiltoniano médio nem como previsão de trajetória.

Para o2:1, theta_i=2lambda_exterior−lambda_interior−varpi_i.
Generalização de primeira ordem candidata: jlambda_exterior−(j−1)lambda_interior−varpi_i.
É uma aplicação explícita da combinação angular, ainda por testar nos casos
dinâmicos. O índice interior/exterior vem do semieixo osculante atual e deve
permanecer estável na definição; não trocar IDs silenciosamente ao cruzarem.

Excentricidade quase zero torna varpi indefinido. Lambda pode continuar
disponível, mas o ângulo que usa aquele periastro precisa de lacuna/motivo.
Órbita radial, parabólica/hiperbólica, retrógrada ou fora do plano ficam fora
da primeira fatia com motivo explícito. Não inventar varpi=0 para completar
um gráfico. Degenerescência de nó num plano não invalida a longitude média.

Uma janela finita não prova captura permanente. Não reduzir os centros a0/π:
soluções assimétricas existem. Lacunas/intervenções/trocas de plano reiniciam
qualquer análise contínua. Sem cobertura temporal e cadência suficientes,
não desempacotar ângulos nem declarar circulação/libracão. Inicialmente mostrar
amostras embrulhadas e cobertura circular, sem classificador automático.
Um círculo quase preenchido pode ser circulação amostrada; um arco curto
também pode ser um trecho curto de circulação. Não transformar isso em selo.

## Fontes primárias consultadas

- Beaugé, Ferraz-Mello & Michtchenko2003, resumo e artigo:
  https://arxiv.org/abs/astro-ph/0210577 (v1,25/10/2002).
  Define theta1 do2:1 e famílias alinhadas, antialinhadas e assimétricas.
- Goldreich & Schlichting2014, v2 de21/11/2013:
  https://arxiv.org/abs/1308.4688v2. Captura e libracão podem ser transitórias;
  proximidade ao quociente exato não é um diagnóstico suficiente isolado.
- REBOUND5.2.2 instalado, particle.py/orbit.py: comparar explicitamente com
  particle.orbit(primary=...), nunca depender da ordem padrão Jacobi.
  A página antiga orbitalelements redirecionou à raiz atual; não foi usada
  como prova de convenção pinada.

## Provas necessárias

Kernel: Kepler elíptico conhecido, lambda uniforme, circular/periastro
indefinido, rotação/translação/boost, troca de ID/ordem, validação de plano.
Comparar com elementos REBOUND5.2.2 e cálculo independente em SI.
Dinâmica: três massas ativas em caso2:1 com libracão e controle circulante,
semipasso/solver independente e séries suficientemente longas. Nenhuma
medição formal deve se sobrepor a esses ensaios.

Antes da promoção: definição/histórico/checkpoint/replay/worker/CEF e curvas
com lacunas, todos sem reiniciar o solver de força. Só depois avaliar
classificação quantitativa mais forte, com critérios e limites próprios.

## Provas isoladas concluídas

Kernel240comparações, dinâmica3massas500períodos com caso2:1(span0,603rad)
econtrole1.8(94voltas), oráculoNewtonianoDOP853 independente20períodos até
refino240passos/período (diferençaIAS15≤1,887e-12;ângulo≤6,111e-13rad).
Recibos resonant-{angles,dynamics,oracle}-prototype-check.json.
Figura resonant-validation-prototype.svg/png revista. A contagem de reversões
locais inclui termos rápidos, não é contagem de cicloslentos/capturapermanente.
Material3.10 encerrou perfil formal e motor foi fechado. Próximo é integração
read-only das definições e séries, mantendo o solver de força exatamente.
