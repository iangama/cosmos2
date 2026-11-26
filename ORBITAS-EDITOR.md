# C2-06 — diagnóstico e prévia orbital

Contrato prévio14/10/2026. Ler só esta etapa do roteiro. A integração N-corpos
permanece IAS15 com todas as massas ativas; uma cônica osculante é um
diagnóstico instantâneo de dois corpos, não a previsão exata do sistema.
Não chamá-la de órbitaJPL nem prometer captura/ejeção pelo sinal de energia
de um único par num instante. Captura/ejeção exigem a experiência temporal.

Para corpo e primário escolhidos explicitamente por ID estável, usar r/v
relativos no referencial inercial da sessão e mu=G*(m+M). Não usar índice,
primárioJacobi implícito ou o centro de massa de outra população. Fornecer
distância, velocidade relativa/radial/transversal, energia específica do par,
momento angular específico, vetor excentricidade, e, parâmetro p, semieixo,
periastro, apoastro e período quando definidos. Unidades SI e instante,
sistema/revisão/token/frame em cada leitura. Não preencher ângulos indefinidos
com zeros que aparentem observação: circular não define periastro; plano
equatorial não define nodo; radial não define plano orbital. Perto da
parábola ou de momento angular nulo, marcar a condição numérica e suprimir
os elementos instáveis. Campo ausente é null com motivo.

Prévia geométrica da cônica relativa: amostra no próprio plano vetorial, sem
ângulos singulares obrigatórios, com primário congelado no instante. Limitar
arco de órbita aberta e raio de exibição a um múltiplo declarado da distância
atual; não desenhar através de assíntota ou fingir uma órbita fechada. Circular
usa eixo radial instantâneo como convenção gráfica. Corpo selecionado é
incluído na curva até precisão numérica; retorno cartesiano independente e
comparaçãoCSPICE/REBOUND/DOP853 nos ensaios, com tolerâncias declaradas.
A curva é visualização derivada e não muda nenhuma condição do worker.

Baricentro de todos os corpos ativos, velocidadeCOM, massa total, energia
cinética/potencial/translacional, P e L do referencial fixo. Medir conservação
em relação ao último estado inicial/intervenção física e manter o registro
separado de E/P/L externos. DerivaCOM esperada inclui movimento do centro;
não recentrar para escondê-la. Raio/spin cinemáticos não zeram esse baseline.

Escape do par: sqrt(2mu/r), com hipótese de dois corpos isolados explícita.
Também dar potencial e velocidade de escape de uma partícula-teste do conjunto
instantâneo congelado, sqrt(2*sum(G*mj/rij)), excluindo a própria fonte; não é
critério suficiente de escape real de N-corpos em movimento. Distâncias de
superfície só quando raios definidos; gravidade atual continua pontual.

Prévia de entradas ainda não aplicadas deve validar o mesmo guard e limites do
editor, trabalhar numa cópia e não deixar estado/revisão/checkpoint/câmera
alterados ao falhar. Mostrar antes/depois para massa/fase propostas. Não
integrar uma extrapolação N-corpos ilimitada na threadHTTP; esta fatia começa
com cônica instantânea mais ensaios temporais em cenários controlados.

Fontes primárias consultadas14/10: [NAIF oscelt](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/oscelt_c.html)
para domínio/degenerescências e teste de retorno; [REBOUND OrbitalElements](https://rebound.hanno-rein.de/ipython_examples/OrbitalElements/)
e fonte local5.2.2 para primário explícito e mu incluindo as duas massas.
A implementação vetorial/limites acima é escolha deste produto; não atribuir
às fontes precisão universal ou validade de extrapolação no sistema solar.

Aceite: circular/inclinada/retrograda/excêntrica/elíptica/hiperbólica/parabólica/
radial, troca de primário e IDs após remoção, um corpo sem par, SI/fonte/guard,
conservação com intervenções, massa comparável ao primário, UIreal e curva
3D com transformaçãoAtlas correta. Experiências de encontro/captura/ejeção
incluem influência do terceiro corpo, comparação antes/depois e balances.
