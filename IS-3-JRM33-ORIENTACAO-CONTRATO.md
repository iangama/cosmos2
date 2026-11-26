# IS-3 — orientação e ligação do JRM33 à cena

Contrato fixado antes de implementar e executar o wrapper. O aceite da
síntese em coordenadas do modelo permanece em seu próprio recibo.

## Convenção e provedor

A documentação primária [LASP, versão12, 20/10/2016](https://lasp.colorado.edu/mop/files/2015/02/CoOrd_systems12.pdf),
páginas1–4, associa S3RH aIAU_JUPITER. Define X no meridiano de origem
equatorial, Z no eixo norte de rotação e Y=Z×X. Longitude leste destrógira
é360° menos a longitude oeste tradicional. Colatitude é medida do norte.
Não usar o frame inclinado JUNO_MAG_VIP4 para os coeficientesJRM33.

O documento exige PCK00010 com os termos completos de nutação/precessão.
Oito grupos BODY599/5, incluindo todos os15ângulos, foram comparados
numericamente aoPCK00011 local: todos são exatamente iguais. Fonte e
kernel antigo preservados emoutput/is3-jupiter-orientation-staging;
recibo evidence/is3-jupiter-orientation-acquisition-20261023b.json.
TentativaA ficou incompleta por parser incluir exemplos da seção textual;
B lê somente blocosbegindata. Não reescreverA como aceita.

Usar SPICE pxform(IAU_JUPITER,J2000,ET) noPCK00011 fixado, verificando
hashes dePCK/LSK, identidade doframe e valores efetivos da pool. Recusar
PCKbinário concorrente ou parâmetros diferentes. Não carregar oPCK00010
no produto nem mudar a pool para ocultar um conflito. O giro cosmético de
um marcador não muda a orientação científica.

## Ligação e domínio deste instrumento

Somente Júpiter físico599 da cópia de quatro centros. Centro é a posição
EVOLUÍDA, nunca uma nova posição de efeméride. Época éET0+t×time_unit_s.
Latitude éplanetocêntrica ±90°, longitudeLESTE0..360°, raio geocêntrico
1..20Rj eRj=71.492.000m. Trata-se de raio esférico, sem converter altitude
elipsoidal ou representar superfície achatada. Graus1/13/18 conforme
contrato da síntese;13padrão,18exploratório.

Adotar para esta ligação a faixa de aplicação2000-01-01T00:00:00Z até
2030-01-01T00:00:00Z, inclusive. É limite escolhido do instrumento, sem
afirmar cobertura observacional do campo. Coeficientes permanecem estáticos
da época2019, mesmo em2026: sem previsão secular, correntes externas ou
modelo de magnetosfera. Não apresentar isso como previsão do campo total.

Rotacionar posição relativa eB deSistemaIII paraJ2000 na mesma época;
somar centro somente à posição. RotacionarJ2000→GALACTIC para exibição.
Devolver instante,frame,grau,origem,hashes,incerteza local desconhecida e
limites. Não introduzir força em centros neutros nem alterar órbitas.

## Verificações prévias à API e UI

Arquivar fontes/dados/contrato antes de executar. Em seis épocas cobrindo
2000,2019,ano bissexto,2026 e2030, comparar a matrizSPICE a uma construção
independente pelos ângulosIAU completos. Erro máximo de componente≤1e−10
(arredondamento na avaliação trigonométrica de ângulos acumulados grandes);
ortogonalidade/determinante≤2e−14. PCK00010 e00011 devem produzir a mesma
matriz nessas épocas em processos/pools de teste isolados.

Em seis posições por época, graus13/18, conferirB contra a síntese já
aceita, norma preservada em≤1e−18T e posição ida/volta≤1mm. São testes de
consistência de transformação, não precisão observacional. Verificar polos,
longitude0/360 e que uma direção inercial fixa tem longitude leste
decrescente com o tempo. Intervalo curto deve corresponder à taxa positiva
870,536°/dia, incluindo efeitos de polo sem substituir o provedor.

Verificar evolução de6h com centro atual, translação do centro afetando
apenas posição e preservação da pool/estados/arquivos. Recusar entradas,
corpo,época,frame e fontes incompatíveis sem mutação. Depois disso,
worker/API devem exigir identidade e fase confirmadas e recusar obsoletas.
UI precisa distinguir amostra fixa, coordenadas/grau alterados, época2019
dos coeficientes e relógio da cena; jornadas nativas próprias100/150%.

Aceite visual de linhas/mapas, desempenho com camadas e partículas/Lorentz
continua separado. Parâmetros locais de consulta ainda não compõem o
checkpoint; recarga limpa leituras derivadas.
