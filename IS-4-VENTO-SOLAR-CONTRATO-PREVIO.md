# IS4 — vento solar prescrito: contrato prévio25/10/2026

Staging separado; preservar0.8.1, motor e sessões. Cenário cinemático de Parker,
duas polaridades, estacionário e axisimétrico, velocidade radial constante
prescrita. Sem resolver plasma/MHD, aceleração do vento, ondas, espalhamento,
CME, magnetosfera/aurora ou reação da carga nas fontes.

Referências: Dalla et al.2013, seção2.1 eqs1–6 e seção2.2,
https://doi.org/10.1002/jgra.50589, autor https://arxiv.org/abs/1307.2165.
NOAA https://www.spaceweather.gov/phenomena/solar-wind dá contexto do vento
lento~400km/s e polaridades opostas; nenhuma observação atual é importada.
O artigo usa unidades Gaussianas. Aqui SI: E=−u×B, sem fator1/c.

Origem estática no Sol da cópia de quatro centros pausada. EixosIAU_SUN
congelados na época e tratados como inerciais da bancada. Guardar rotaçãoSPICE
completa. Sem termo fictício, centro móvel ou relógio orbital implícito.
Definir r=|x|, A=Bref*AU², k=(0,0,1), p=polaridade*sign(z):

    u = u0*x/r
    B = p*A*(x/r³ − (Omega/(u0*r²))*(k×x))
    PhiE = −p*Omega*A*z/r
    E = −grad(PhiE) = −u×B

Equivalente: Br=p*A/r², Btheta=0, Bphi=−p*Omega*A*sin(theta)/(u0*r).
No mesmo hemisfério E é conservativo e B tem divergência zero fora da origem.
Polaridades opostas cancelam fluxo global ideal; folha equatorial não resolvida.
Não inserir fator(r−rs) emBphi mantendo E estacionário sem rederivar indução.

Parâmetros didáticos explícitos, sem ajuste a medição: AU=149597870700m exata,
Bref=3e−9T radial, u0=400000m/s, Omega=2*pi/(25,38*86400)s−1, polaridade±1.
Aceitar u0=1e4..2e6m/s,Bref=1e−12..1e−6T,Omega=0..1e−4/s; bool recusado.
Domínio raio0,1..10AU, |latitude|≥5°. Cortes computacionais Terra100*6378137m,
Lua10*1737400m,Júpiter100*71492000m; Sol já excluído por0,1AU. Esses cortes
não predizem magnetopausas/choques. Não somar/extrapolar campos internos
planetários. g soma quatro monopolos fixos, sem subtrair aceleração da origem.

Validar todo drift: raio máximo nos endpoints; mínimo por projeção na reta.
Endpoints no mesmo cone norte/sul convexo não atravessam banda equatorial.
Verificar exclusões de todas fontes antes consultar campo. Recusar sem clamp
e preservar última fase válida. Mantém regime≤0,01c e limites já adotados.

Critérios antes do código/teste:

- Grade de polos/longitudes/latitudes± e raios, ambas polaridades. Comparar
  cartesiano com fórmula esférica independente B/E rtol3e−14,atol1e−24T e
  1e−18V/m. E=−u×B,E·B=0. DivergênciaB/curlE por diferença central h=1e−5r:
  erro normalizado≤2e−8. UnidadesSI e potencial elétrico emV.
- Trabalho por quadratura independente em segmentos =−qDeltaPhiE,
  rel1e−10+1e−24J. Diferenças de potenciais estáveis. Comparar g emJ2000 e
  rotação de volta2e−13rel+1e−12m/s². Entradas/descritores imutáveis.
- Seis trajetórias físicas: próton/elétron, norte/sul, polaridade±, raios
  0,3/1/5AU e latitudes±10/30/60°. Dez períodosgiro iniciais, N2000/4000/8000;
  DOP853 em deslocamento comrtol1e−11,atolposição1e−7m/velocidade1e−7m/s,
  passomáximoT/12,40instantesiguais. Convergência3,4–4,6 acima do piso;
  erro fino≤5e−4rho+1e−4m,velocidade≤5e−4escala.
- EnergiaK+qPhiE+mPhiG converge com passo. Residual trabalho discreto≤1e−12
  escalaK+|trabalhos|. CasosEoff/Boff/goff/neutral comODE independente;
  campos prescritos não mudam com atuação.
- Recusas de cruzamentos/domínios, parâmetros, matriz/época/identidade,
  sem consulta indevida nem mutação. Arquivar fontes/fixtures/receita.

Depois da ciência: sondaE/B/u/potenciais e trajetória no mesmo estadoSI,
procedência/limites UI,save/load/ramos/export/restart,jornadaCEF eperfil
próprios. Não herdar aceite IGRF/JRM nem declararIS4concluído.

Esclarecimento antes da rodadaC de campos: tolerâncias vetoriais acima usam
norma Euclidiana (erro absoluto <=rtol*norma referência+atol), sem alterar
3e−14/1e−24T/1e−18V/m. A usou seno(pi) para um polo que deveria ser exato;
B comparou individualmente uma componente quase nula de um produto vetorial
com cancelamento. Preservar ambas. Não houve mudança do provedor Parker.

Antes da primeira rodada de trajetórias: diagnosticar diferenças de potenciais
com deslocamentos pareados, sem perder deslocamento menor que ULP da posição
heliocêntrica. Comparação com Decimal80dígitos: erro relativo≤5e−12+1e−18V
(elétrico),≤5e−12+1e−18J/kg(gravitacional). Campos continuam em double SI.
Energia física pode ficar no piso de arredondamento: adotar piso1e−11*K0,
sem exigir razão de erros abaixo desse piso. Acrescentar caso SINTÉTICO
q/m=3000C/kg,m=1kg,1AU,lat30°,vrel=100km/s,pitch60°,polaridade+1,um período
giro inicial para variação espacial mensurável. Nesse caso exigir ambas razões
energéticas3,4..4,6 acima do piso, além do futuro/ODE. Não é espécie física.
Velocidades iniciais são u radial+componente relativa com pitch declarado;
rho inicial refere-se a essa velocidade relativa. Seis casos físicos: próton
0,3AU/+10°/P+,elétron0,3AU/−10°/P+,elétron1AU/+30°/P−,próton1AU/−30°/P−,
próton5AU/+60°/P+,elétron5AU/−60°/P−.
