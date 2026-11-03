# IS-3 — maré passiva integrada, campos dos corpos em construção

A candidata está em `output/is3-tides-product`, derivada dos87arquivos da
IS-1/2 cujo perfilB foi aprovado. A base foi arquivada antes das mudanças;
IS-1/2,instalado3.13 e sessões do dono continuam preservados. Não houve promoção.

## Resultado verificado

- Função passiva:72casos contraDecimal70dígitos, zero exato e refinamento
  linear passaram.25recusas de guard/vetores passaram sem mutação.
- Processo físico:quatro leituras comparadas comDecimal,19recusas de
  comandos, fase antiga/token após restauração recusados, checkpoint IS-1/2
  lido por cópia e marcado como geração diferente, sem reescrever a origem.
- Jornada nativaB:API eCEF retornaram a mesma leitura na fase confirmada;
  soma vetorial e campo próprio excluído; nove recusasHTTP sem mutação;
  deslocamento editado marcado como amostra anterior; zero exato; avanço,
  pausa,save/load e nova leitura apósrestauro; recargaCEF limpa derivadas;
  época/estados do Atlas e owner preservados.100/150% e capturas executados.

Recibos: `evidence/is3-tides-staging-20261023a.json`,
`is3-tide-guards-20261023a.json`,`is3-tide-worker-20261023a.json` e
`is3-native-tide-20261023b.json`,todos accepted=true nos respectivos escopos.
Fontes/fixtures foram arquivadas antes de cada execução. Não repetir essas
suítes sem mudar a fonte pertinente ou encontrar uma preocupação concreta.

A jornadaA encontrou um defeito real de rótulo: ao focarTerra isoladamente,
a etiqueta ainda diziaTerra/Lua, herdada da visão geral. A seleção agora
restaura o nome individual na candidataIS-3. A evidênciaA permanece recusada;
IS-1/2não foi reescrita nem recebeu esse conserto silenciosamente.

No exemplo de11/10/2026 12hUTC, offsetJ2000(6378137,0,0)m daTerra, o módulo
da maré externa total é1,413267e−6m/s²; contribuições solar4,899403e−7 e
lunar9,369176e−7m/s². Somam-se os vetores, não os módulos. O deslocamento é
um exemplo nos eixos inerciais; não significa longitude/latitude geográfica.
IGRF/JRM33 ainda não estão ligados à cena; não há maré oceânica ou resposta
material neste instrumento. A configuração do formulário/leitura é local ao
CEF e ainda não foi incluída no protocolo de checkpoint.

## Imagem e limites

As duas capturas foram revistas: texto do instrumento legível em100/150%,
sem rolagem horizontal. O quadro do corpo ainda usa marcadoresciano ampliados;
não é aceite visual final do SistemaSolar. Confirmação de nome/âncora e dez
frames renderizados antecedeu a captura. Um marcador próximo pode aparecer
parcialmente no alto; geometria/texturas físicas continuam pendentes.

## Próximo passo autorizado

Ligar a consultaIGRF14 ao centro terrestre evoluído e à época inicial+t em
TDB, com conversãoUTC/ano decimal, orientação terrestre fixada e vetores nos
referenciais declarados. Examinar e adquirir somente o PCK EOP datado
necessário; preservar o PCK genérico, a poolSPICE e as bancadas antigas.
Fixar contrato/limites antes de verificar a ligação. Sem forçaEM sobre os
centros neutros. JRM33 e ambiente externo seguem separados.


## Continuação — IGRF14 ligado à Terra evoluída

A candidata passou a consultar o campo principal interno em um pontoWGS84
construído em eixosITRF93, usando o centro terrestreEVOLUÍDO e a época
ET0+t do solver. Vetores retornam emITRF93,J2000 eGALACTIC, sem força no
centro neutro. A rotação visual de um marcador não altera esse provedor.
Os coeficientes e a síntese antiga foram preservados; corrigiu-se somente
a resolução deROOT da cópia para alcançar os dados científicos da raiz.

O PCK datadoearth_000101_270118_261022.bpc foi adquirido5.151.744bytes,
SHA0d7b251eacf1f3136aa9d9dd7d5f7c9b060a97bc1ab07de5635f9445d0fa923b,
idêntico ao alias oficial. Não haviaaa_checksums.txt no diretório (HTTP404),
fato registrado sem inventarchecksum publicado. Cobertura medida2000-01-01
a2027-01-18(00hUTC),frameITRF93/código3000, último datum2026-10-22.
Trechos após o datum são identificados como previsão. O PCK genérico e o
Atlas não foram substituídos. Dados e fontes emstaging e recibo próprio.

Verificações accepted=true:
- is3-earth-field-check-20261023a:58fixturesBGS,erro máximo0,0145434nT;
  30combinações época/ponto, erro de matriz≤5,56e−16, posição ida/volta
  ≤14,64µm,norma deB≤6,78e−21T; rotação6h, vínculo ao centro evoluído,
  previsão e12recusas. PoolSPICE/estadoSSB/IAU/owner preservados.
- is3-earth-worker-20261023a:comando real,25recusas sem mutação,
  fonte/época/geração corretas, evolução/restauração/guards, regressão da
  maré e leitura por cópia do checkpoint anterior, sem mudar a origem.
- is3-native-earth-20261023a:API/CEF iguais, leitura100/150%, polo,
  corpo errado indisponível, dez recusasHTTP sem mutação, amostra fixa
  após avançar/restaurar, recargaCEF limpa derivada, data prevista e época
  fora da cobertura recusada; Atlas,IS12 eowner preservados.

Fontes/fixtures foram arquivadas antes das verificações. Depois da jornada,
removeu-se uma expressão inoperante do harness e atualizou-se apenas uma
frase antiga daUI que ainda chamava todoEM de bancada separada. Nenhum
algoritmo/estado científico mudou nessas duas limpezas; o recibo nativo
conserva exatamente a geração de fonte arquivada que executou.

Exemplo efetivamente executado:11/10/2026 12hUTC, latitude−23,55°,
longitude−46,63°, altura1km. |B|=22.776,537674nT; componentes norte/leste/
baixo=15.964,431396/−6.420,199493/−14.922,755679nT. São valores do modelo,
sem barra de erro local propagada, não medição naquele local.

Capturas revistas: texto legível100/150%. A cena ainda usa marcadores
ampliados; não existem neste recorte mapa/linhas/vetorB nativos, aplicação
deLorentz, tempestades ou transporte de partículas. A configuração da
consulta é local à página; o checkpoint conserva fase/fontes/geração e as
leituras derivadas exigem nova consulta. Sem aceite final deIS-3 ou promoção.

Próximo:seguir contrato de campos paraJúpiter/JRM33 emstaging, fixando
coeficientes, convenções, normalização, domínio e referência independente
antes de ligar à cena. Visualização espacial do campo terrestre permanece
uma entrega própria, usando a mesma fonte/época; não desenhar uma sonda
real sobre um marcador ampliado e apresentar isso como geometria física.

## JRM33 ligado à cena — continuação23/10

A síntese joviana própria passou160casosPSH e a ligação à cena passou72
casos de rotação/posição em seis épocas, worker e jornadaCEF/API100/150.
Detalhes, limites e recibos: IS-3-JRM33-RESULTADO-20261023.md e contrato
IS-3-JRM33-ORIENTACAO-CONTRATO.md. Consulta passiva, internoestático2019;
centro599evoluído e relógioET0+t. Nenhuma força em centros neutros.
Captura150 teve ausência transitória do marcador; diagnóstico de quatro
focos posteriores mostrou câmera estável/marcador visível. Causa não
estabelecida; visual final continuaPARCIAL. Linhas/mapas nativos eLorentz
ainda pendentes. Próximo: preflight diagnósticoJ antes de camadasEM novas.
