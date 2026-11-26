# C2-14 — contrato da lente pontual, antes dos dados

O próximo recorte obrigatório é mover fonte, lente e observador e medir
separação, deflexão e amplificação (ESCOPO-CIENTIFICO.md§5). O produto
entregue0.28.4 permanece selado. Este contrato prepara uma implementação
separada; não declara aceite de núcleo, serviço, interface ou C2-14 completo.

## Formalismo e fontes

A aproximação de lente fina e deflexão pequena usa
`alpha_hat=4GM/(c² b)`, `beta=theta-(Dls/Ds)alpha_hat` e
`thetaE²=(4GM/c²)Dls/(Dl Ds)`. Referência: Bartelmann/Schneider,
[seção3.1, Eqs3.1,3.6 e3.14](https://arxiv.org/pdf/astro-ph/9912508).
A amplificação assinada vem do inverso do determinante da transformação
angular. A paridade negativa representa inversão da imagem, não fluxo
negativo. Para uma fonte deslocada existem duas imagens; seu fluxo total
usa a soma dos módulos das amplificações. O alinhamento de fonte pontual
é singular nesta aproximação. Referência: Wambsganss,
[Eqs17–21 e discussão da caústica](https://arxiv.org/pdf/astro-ph/9812021).

Campo gravitacional fraco não exige amplificação próxima de1. Esta bancada
não representa apenas o regime observacional chamado weak lensing.

## Escolhas operacionais desta implementação

São posições cartesianas estáticas em metros: O(observador), L(lente) e
S(fonte), mais GM em m³/s². A direção O→L define o eixo. O plano da fonte
é perpendicular a ele e passa por S. `Dl=|L−O|`,
`Ds=(S−O)·n` e `Dls=Ds−Dl`. Usar fundo euclidiano declarado;
`Dls=Ds−Dl` não é uma regra de distâncias cosmológicas. Não converter
redshift nem herdar época, objetos ou movimento do Atlas.

A base transversal é ortonormal e determinística. Os dois componentes de
`beta` são as coordenadas transversais de S divididas por Ds. Esses ângulos
são paraxiais; registrar também o ângulo geométrico `atan(|beta|)`. O mesmo
vale para as imagens: a direção normalizada é `n+theta_x e1+theta_y e2`.
Não apresentar a polilinha O→plano da lente→S como integração geodésica.

Entradas devem ser números reais finitos, sem bool, com campos exatos.
GM>0; cada coordenada tem módulo≤1e25m, e Dl e Dls são≥1m. Lente e fonte
precisam estar à frente do observador, com Ds>Dl. Para cada imagem exigir
`b/rs≥1000`, `|theta|≤0.01rad` e desvio paraxial da fonte≤0.01rad.
Esses são limites conservadores operacionais, não uma estimativa medida de
erro físico. Recusar geometria fora deles, inclusive quando somente a
imagem secundária sair do domínio. Não omiti-la nem renormalizar seu fluxo.

Para imagens finitas admitir `1e-6≤u=|beta|/thetaE≤1e4`.
Desalinhamento não nulo menor que esse limite recebe recusa explicada de
precisão perto da caústica; isso não limita fisicamente a amplificação.
No alinhamento matemático exato retornar o raio do anel de Einstein,
amplificação indefinida e estado explícito de limite singular. Não inventar
duas direções preferidas, fluxo finito ou teto de brilho. A UI precisa
explicar a fonte pontual e permitir afastar a fonte. Fonte extensa, óptica
ondulatória, ocultação, absorção, spin e múltiplas lentes ficam fora deste
recorte, sem receber aceite por ele.

Converter entradas binárias finitas para Decimal e calcular geometria,
raízes e Jacobiano com80dígitos, usando contexto local. Isso reduz perda
por cancelamento em referenciais oblíquos; não cria precisão nos dados de
entrada. Registrar a resolução binária das coordenadas como diagnóstico.
Converter resultados finitos para JSON; nenhum NaN/Infinity. Calcular a
raiz interna pela relação de produto, não por subtração quase igual.
Conservar também o excesso de amplificação sobre1 sem subtrair floats
quase iguais. O núcleo é estático, de custo limitado, sem worker externo,
acesso à rede ou gravação de sessão. Fontes e constantes ficam identificadas.

Suprimir a deflexão é intervenção explícita: mesma geometria e GM, uma
imagem direta, amplificação1 e desvio0. A referência completa permanece
disponível. Visualização não muda o núcleo nem a impressão física. O anel
da referência pode ser singular mesmo quando a intervenção direta é finita.

## Aceite preparado, ainda não executado

1. Comparar raízes com busca numérica independente a100dígitos nas duas
   semirretas e amplificações com derivadas numéricas do mapa angular.
   Varredura logarítmica de u entre1e-6 e1e4 e diferentes GM/distâncias;
   diferença relativa≤5e-12 em resultados finitos, incluindo imagem fraca
   e excesso de amplificação. Sem filtrar casos depois dos dados.
2. Verificar sinal/paridade, ordem das imagens, equação vetorial e produto
   das raízes, planos/ramos dos raios e identidade da fonte. Resíduos
   geométricos são comparados com a resolução de serialização, e o resíduo
   angular é normalizado por thetaE, sem dividir por beta na caústica.
3. Permutações/reflexões exatas das coordenadas, escala conjunta de comprimentos
   e GM, e translação com registro da resolução das entradas. Não atribuir
   invariância perfeita a coordenadas arredondadas após transformação.
4. Alinhamento→anel sem amplificação finita; pequeno deslocamento não nulo
   fora do domínio→recusa; intervenção direta→imagem única sem mudar GM.
5. Tipos/campos, NaN/Infinity, observador coincidente, ordem dos planos,
   ângulos, impacto insuficiente de qualquer imagem e limites de u recusados.
   Repetição determinística e ausência de efeitos na sessão atual.
6. Comparação suplementar da deflexão assintótica com o integrador nulo
   Schwarzschild existente para b/rs=1000,3000,10000: diferença relativa<1%
   e redução da diferença na direção do limite fraco. Isso não valida a
   geometria finita inteira nem remove a aproximação de lente fina.

Arquivar contrato/fontes antes dos dados. Publicar recibo com todos os
casos/recusas e versões de Python/mpmath. Só depois conectar serviço e UI,
conferir comportamento original em100/150%, recuperação, proveniência,
retorno e preservação do dono. Novo perfil só se a implementação e seu
escopo exigirem; não repetir o perfil de órbitas já aceito.
