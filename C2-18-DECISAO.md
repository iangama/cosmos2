# C2-18 — decisão local de aceite

13/10/2026, Windows nativo / RX7600, build OpenSpace próprio preservado.
**Aprovado localmente o recorte C2-18 do roteiro4.1:** acervo nuclear, ligação,
energias Q/limiares e fusão manipulável com canais avaliados. J12 e a parte
nuclear de J14 foram percorridos na interface; os demais marcos continuam
com seus próprios critérios. Não é aceite de QCD, rede de plasma completa,
evolução térmica/estelar, pacote distribuível ou da v1.

## Entrega observável

- Acervo AME2020 original:3558estados, carta N×Z, curva B/A×A, seleção/sonda,
  duas espécies comparáveis, incertezas, estimativas# e ausências preservadas.
- Instrumento de Q/limiar: nove exemplos e editor A/Z, Sn/Sp/S2n/Salpha,
  cinemática relativística com alvo fixo e curva de energia disponível no CM.
  Covariâncias ausentes e distinção limiar/barreira/taxa explícitas.
- Fusão: seis misturas/sete taxas REACLIB, composição e energia por tempo,
  D+D com ramos concorrentes independentes, combustível compartilhado e
  proporções calculadas pelas taxas. Condições T/densidade/razão/duração
  editáveis; botão explícito de condições comparativas, sem trocar tempo
  automaticamente ao alterar T. Capturas D+p/C12+alpha exigem forte e EM.
- Gates preservam matéria e referência; ocultar preserva resultado/identidade
  científica. Q do fit e diferença de massas AME ficam separados. Salvar,
  retomar, exportar JSON real e abrir o exemplo correspondente de massas
  funcionam no CEF. Atlas/worker permanecem preservados durante a investigação.

## Evidência e limites

Contratos prévios: NUCLEOS.md, ENERGIAS-NUCLEARES.md e FUSAO-CANAIS.md.
Acervo e energias: nuclei-check/UI/native, nuclear-energies-check/UI/native
e revisões visuais preservadas. A diferença de limiar NNDC N14(n,2n), a
ausência de covariâncias e as diferenças de arredondamento continuam
registradas; não foram anuladas para forçar concordância.

Fusão: evidence/fusion-check.json passou sete taxas com erro máximo
7,07e-14rel, composição contra ODE independente1,06e-12 da densidade inicial,
extensões5,30e-13, balanços A/Z4,45e-16rel,66combinações de gates e48limites.
Exposição minúscula produz produtos não nulos; esgotamento não produz
populações negativas. Entradas inteiras grandes do JSON do navegador foram
corrigidas para cálculo float64 e passaram regressão. Source errors do fit
não são estimados pelo resíduo numérico.

Edge720 e CEF reais passaram os seis exemplos, sondagem temporal, dois ramos
D+D, EMoff radiativo, visualização sem efeito físico, save/load da geração,
JSON local igual ao resultado autoritativo do backend e recusa sem mutação.
A cópia JS Number para inspeção não garante a mesma representação decimal
de números grandes; o arquivo local preserva a saída científica do backend.
Capturas finais conferidas em evidence/fusion-visual-review.json; sem
sobreposição após corrigir rodapé/rótulo final do eixo. Onze contratos e
persistência passaram;11pacotes/42arquivos registrados/verificados.

O renderer nativo e seu executável não mudaram. Esta bancada de canvas usa
até cinco curvas, na classe já exercitada por pp/CNO; os nove percursos G0
continuam ligados ao build original, sem alegação de novo benchmark de FPS.
A revisão atual cobre usabilidade e cálculos deste recorte; C2-09/17 ainda
precisam instalar/integrar/medir a entrega completa.

Modelos de fusão são zonas Maxwellianas de T/volume prescritos, sem
screening, inversas, reações secundárias, confinamento ou transporte. Energia
disponível não é calor depositado. Produtos n/T não decaem nem reagem
implicitamente. Ligação total não isola a interação forte. Espalhamento/EFT
mais profundo continua no C2-21 conforme o roteiro, sem reduzir este aceite.

Próximo marco: C2-19, pelo menos oito decaimentos/capturas avaliados, incluindo
beta−/beta+/EC e ramificações/cadeias, produtos e energia/neutrinos por tempo.
