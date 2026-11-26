# Derivadas para trabalho de pressão — nota29/10/2026

Nota de implementação antes de executar o novo modelo. As fórmulas abaixo
são derivadas nas convenções do Cosmos2; não constituem aceite numérico.
Contrato e limites:IS-5-COMPRESSAO-CONTRATO-PREVIO.md. Preservar os módulos
aceitos e implementar somente um wrapper em estágio novo depois do perfil0160.

## Coordenadas e unidades

Usar Y_i=n_i/n_b e neutralidade Y_e=ΣZ_iY_i. Derivadas emρ mantêm T e todos
osY_i constantes; logo n_e e n_i variam proporcionalmente aρ. Derivadas emT
mantêmρ eY_i constantes; logo n_e é constante. U tem unidadeJ/m³,Cv tem
J/(m³K),P_T temPa/K eU_lnρ temJ/m³. Não misturar essas derivadas com as que
mantêm pressão constante ou usam energia específica.

## Parte ideal já aceita

O módulo is5_eos.mixture fornece Cv_e e a derivada deU emY_e. Na EOSnão
relativística, U_e=3P_e/2; portanto, a densidade eletrônica fixa,

    P_T,e = (2/3) Cv_e.
    U_lnρ,e = Y_e (∂U/∂Y_e)T,ρ.

Para íons clássicos, P_T,i=n_i k_B eU_lnρ,i=U_i. Para radiaçãoLTE,
P_T,rad=4U_rad/(3T) eU_lnρ,rad=0. Assim,sem nova quadratura FD,

    P_T,ideal = n_i k_B + (2/3) Cv_e + 4U_rad/(3T).
    U_lnρ,ideal = U_i + Y_e du_delectrons_per_baryon_J_m3.

Essas duas expressões usam campos independentes do modelo aceito. Não
calcularU_lnρideal usando a identidade deMaxwell e depois chamar a mesma
identidade de uma verificação independente.

## Correlação de Coulomb

F é densidade de energia livre de Helmholtz, τ=lnT eℓ=lnn_b. Para cada
componente ii/ie/ee/mistura e para a soma,

    P = F_ℓ − F;                  U = F − F_τ;
    P_T = (F_τℓ − F_τ)/T;         U_lnρ = F_ℓ − F_τℓ.

Um Jet de duas coordenadas basta para essas novas derivadas. O wrapper
também deve obter o estado completo pela APIaceita,para manter sua validação,
Cv,gradientes de composição e geração. O segundo cálculo não altera a energia
livre nem os guardas. Conferir valores e derivadas com mpmath50dps e diferenças
centradas da EOSpublicada,conforme contrato; a igualdade algébrica deMaxwell
nas expressões deF é somente uma verificação de consistência.

## Integração posterior,fora do primeiro aceite

Com N_bfixo,V=N_b/n_b,a primeira lei usa energia totalE=VU:

    dE/dt = V q_retida − P dV/dt.

Uma referência BDF deve evoluirE e inverter a EOS comρ(t),Y(t) ao calcularT.
Não integrarU como se V fosse constante. A forma por temperatura é a do
contrato,com termoT P_T dlnρ/dt e gradientes completos de composição.
LedgerW=−∫P dV e energia nuclear retida usamjoules; a densidadeq usaW/m³.
Uma expansão sem reações pode reduzirE sem produzir neutrinos: essa energia
é trabalho externo e não pode ser lançada como perda nuclear/fotônica.

## Procedência

[MESA:equações de energia e termo de composição](https://docs.mesastar.org/en/latest/reference/controls.html#eps-grav-form)
é referência de formulação e de cautela sobre conservação versus convergência.
HTML consultado está arquivado emoutput/is5-compression-research-20261029/
mesa-controls-latest-20261029.html,SHA256
dd12219e172a0f58409bd16585f3e5c839642ed93172e7b92e1a1b1e1a92c62f.
Acquisition.json fixaURL/data/tamanho. Não foi executado/copiado códigoMESA;
as dependências científicas existentes mantêm suas licenças e limitações.
