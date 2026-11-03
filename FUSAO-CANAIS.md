# Fusão, canais e composição — contrato prévio

Fatia C2-18, 13/10/2026. Complementar o acervo AME2020 e as energias Q com
seis misturas manipuláveis: D+T, D+D (dois ramos concorrentes), D+p,
He3+He3, Li7+p e C12+He4. Sete taxas diretas REACLIB fixadas da instalação
pynucastro3.1.0; preservar coeficientes/arquivo original, fonte por canal,
Q arredondado do fit e comparação independente de Q com AME2020.

Zona homogênea, Maxwelliana, temperatura e volume prescritos, sem screening,
reações inversas, canais secundários dos produtos, transporte, reação ao
aquecimento ou confinamento. O n/T produzido é apenas contado: não evoluir
decaimento, captura ou queima secundária implicitamente. Não é rede completa
de plasma, rendimento de reator ou descrição de QCD. A energia disponível
acumulada não é deposição local, luminosidade ou temperatura calculada.

Domínio operacional: T=10–1000MK, densidade inicial do primeiro combustível
1e16–1e24m⁻³, razão segundo/primeiro 1e-3–1e3 (somente combustíveis distintos),
duração 1e-6–1e20s. É o recorte de avaliação dos fits, sem acurácia
observacional uniforme garantida nessa faixa. Quando combustíveis idênticos,
há uma só densidade e a razão não se aplica. Duração permanece fixa ao
alterar T/densidade. Não acelerar a física trocando automaticamente o tempo.

R_j = prefactor_j * <sigma v>_j * n_a*n_b; prefactor=1/2 para pares idênticos.
Dois ramos D+D compartilham n_D; dn_D/dt=−(k_n+k_p)n_D². Extensões por ramo
proporcionais às taxas ativas, sem fixar razão 50/50. Misturas distintas
admitem n_a0!=n_b0 e solução exata de dn_a=dn_b=−k*n_a*n_b. Usar expm1
para exposições pequenas e calcular população remanescente sem subtração
entre números quase iguais no limite de esgotamento. Cada curva mostra
fração mássica convencional A*n_i/soma(A*n_i0); unidades e densidades
numéricas completas ficam na sonda/exportação. Sem massas atômicas como
pesos que fariam a soma variar pelo Q.

Atuação forte e gates de cada canal independentes; capturas D+p e C12+alpha
exigem também atuação/efeito radiativo EM. Barreira Coulomb e propriedades
dos núcleos ficam incorporadas nas taxas de referência quando um operador é
suprimido. Referência com todos os canais ligados preservada; ocultar muda
somente a apresentação. Intervenção é contrafactual, não universo físico
autoconsistente sem EM/forte. Não mostrar controles sem efeito na mistura.

Leituras por instante: abundâncias, taxas por canal, proporções dos ramos,
extensões, energia disponível e fótons contados nas capturas radiativas.
Q/ligação AME preservam incerteza/estimativa; erro do fit ausente não vira0.
Persistência da geração científica e exportação JSON real em user/exports,
inclusive no CEF; ligação direta ao acervo e ao instrumento de Q.

Critérios prévios: sete taxas contra pynucastro em cinco T (<1e-12rel),
composição/extensões contra ODE independente adimensional (<1e-9 da densidade
inicial), balanços A/Z (<1e-13rel), energia/extensões (<1e-13rel), limites
de esgotamento/exposição pequena/razões quase iguais e ramos D+D. Conferir
todos os gates relevantes e quatro combinações atuação/referência; salvar,
retomar/exportar, entradas inválidas sem alterar cena. Edge720/CEF com
interação real, zero erros JS e capturas revistas antes do aceite.

Fontes: [REACLIB](https://reaclib.jinaweb.org/),
[pynucastro, fator de pares idênticos e estequiometria](https://pynucastro.github.io/pynucastro/_modules/pynucastro/rates/rate.html),
[Gómez Iñesta, Iliadis e Coc (2017), D+D](https://arxiv.org/abs/1710.01647),
[NACRE2, registro REACLIB nac2](https://reaclib.jinaweb.org/labels.php?action=viewLabel&label=nac2).
Q original e convenções AME seguem NUCLEOS.md/ENERGIAS-NUCLEARES.md.

Implementado e aprovado no recorte C2-18 em13/10; C2-18-DECISAO.md reúne os
critérios e evidências. O botão de condições comparativas aplica explicitamente
300MK/1e22m⁻³/razão1 e duração específica por mistura; fora desse botão,
alterar T/densidade conserva a duração escolhida. Não tratar o botão como
previsão de plasma completo. Legendas de tempo finais e rodapé de gráfico
foram corrigidos após inspeção visual, com recaptura Edge/CEF.
