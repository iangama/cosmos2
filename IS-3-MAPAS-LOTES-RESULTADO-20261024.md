# IS-3 — mapas corporais em lotes

Candidata local0.7.1 em output/is3-body-points-product, runtime separado
.runtime-node-lifecycle-v2. Sem promoção; instalado3.13, demais candidatas,
Cosmos/Revenant e sessão do dono preservados.

Casca19×37 e corte65×65 de IGRF14/JRM33 usam os mesmos dadosSI congelados
já validados. Costura/polos compartilham614símbolos na casca. O corte tem
810pontos terrestres ou3868jovianos nestas fixtures; máscara continua
indisponível e não vira B=0. Oito faixas usam mínimo/máximo amostrados,
sem alegar extremos globais. A sonda consulta a célula que determinou a cor.

Cada faixa agora usa um lote RenderablePointCloud. Substitui três segmentos
e milhares de objetosGL por atéoito lotes, com posições normalizadas porR;
tamanho é apenas gráfico e tem limite angular explícito. O recibo de cada
lote guarda diâmetro, escala, quantização, células, cor e hashCSV. A geometria
herdada de cruzes continua arquivada como referência; a aparência efetiva
dos pontos é definida pelo recibo RenderablePointCloud. Marcador+ compacto
identifica a célula, e a seta verde/painel identificam a consultaB original.

O crash0.7A ao remover Jupcut revelou uma condição de lifetime em filasCPU/GL
com ponteiroscrus. CorreçãoC++V2 espera inicialização da subárvore, elimina
referênciasGLpendentes, evita deinitGL sem initGL e encerra filhos antes de
pais. Fontes e patches arquivados; resultados separados em
IS-3-CICLO-VIDA-MOTOR-20261024.md. Não atribuir cura geral de crashes ao teste.

## Evidência concluída

- is3-body-points-check-20261024a: quatro mapas, todos os pontosCSV contra
  célulasSI de origem, cores/máscara/costura e quantização≤1e−6R.
- is3-points-checkpoints-20261024a: oito combinações modelo/representação/
  visibilidade, ramo e fase binária exata, dez recusas transacionais de
  células inválidas/mascaradas; checkpoint0.6.1 continua legível.
- node-lifecycle-v2-native-20261024a: folha,pai/filho e padrão removidos com
  CPUpendente confirmada. Mesmo datasetbin0 do crash. Quadros reais depois.
- node-lifecycle-v2-shutdown-20261024a: pedido normal com filhoCPUpendente,
  exit0,servidor encerrado e nenhumdumpnovo. Logs preservados.
- is3-native-body-points-20261024a: quatro mapas noCEF/API/motor, célulaSI
  exata e posição≤1mm, visibilidade independente, recusas sem mutação,
  save/loadoculto, reloadCEF, época antiga, ramo, exportaçãoSI e retornoAtlas.
- is3-body-points-visual-review-20261024a: oitoPNGoriginais100/150revistos,
  painellegível e marcadorcompacto; CPUociosa+quadrosGL antes das capturas.
  ROIs com diferenças pequenas em contagem; cascaTerra idêntica em pixels.
  Não inferir desaparecimento por falhas aparentes na prévia da imagem.
- is3-native-body-points-restart-20261024a: motor/servidor com PIDsnovos,
  mesmafase/leitura/célula/formulários, nós, CPUociosa+quadrosGL e posiçãoSI.

## Desempenho aceito

is3-points-profile-20261024a COMPLETO, auditor independente
is3-points-profile-audit-20261024a ACEITO. Oito janelas30/60s, casca/corte
IGRF14/JRM33 visíveis/ocultos, CEF1920×1080,quatrocentros/ritmo0,1.
p95máximo14,04452ms,p99máximo14,51312ms,nenhumquadro>100ms; RAMproduto
1,21130GiB,GPU2,96039GiB. ColetaWDDM66 por janela válida e cobrindo a
captura inteira, limites e conservação conferidos, guardCEFrestaurado.
Escopo da receita:IGRFaltura1km,JRMgrau13raio1,5Rj,camposcongelados,
trêsvistas; sem herdar aceite para configurações/cargas não medidas.

Sem extrapolar para múltiplas camadas, mapas atualizados continuamente,
Lorentz ou ambiente externo. IS4tem contrato prévio de partículas nos
campos adotados; ciência/worker/cena/perfil dessa etapa ainda pendentes.
