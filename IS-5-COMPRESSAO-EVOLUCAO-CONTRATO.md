# IS5 — zona com densidade prescrita, contrato29/10/2026

Contrato antes do solver. Exigir is5-eos-cross-20261029a aceito e fontes
idênticas. Preservar esse wrapper, sua verificação e os modelos/produtos
anteriores. Criar módulo separado; nenhuma mudança de EOS, taxas, Q, neutrinos,
screening ou tolerâncias científicas já aceitas para obter esta extensão.

## Modelo e intervenção

Uma zona neutra, totalmente ionizada, íons clássicos, elétrons FD não
relativísticos e radiação LTE confinada. Mesmos 16 núcleos/18 canais e
aproximações fracas/Be7EC da rede aceita. N_b=ρ0V0/m_u é constante. Volume
V(t)=V0ρ0/ρ(t), com densidade bariônica prescrita como intervenção externa.
Não é solução hidrodinâmica, hidrostática ou resposta gravitacional do Sol.

Programas explícitos, parâmetros estritos:

- constant: ρ(t)=ρ0, sem campos adicionais;
- exponential, ratio: ρ=ρ0 exp[ln(ratio)t/τ];
- cycle, ratio: ρ=ρ0 exp[ln(ratio)sin²(πt/τ)].

τ é a duração nuclear solicitada. ratio deve ser número real, sem bool,
entre0,8e1,2. Para cycle é razão no meio do ciclo; a densidade final éρ0.
Validar extremos deρ antes do solver e todos os estados intermediários
contra os guardas aceitos. Não clamp, extrapolação ou resultado parcial.

Evoluir Y, extensões por bárion, temperatura e trabalho mecânico acumulado.
Equação térmica do contrato anterior com Cv e gradientes completos:

    Cv Tdot = n_b (Q−Qν)·flux − U_Y·Ydot + T P_T (lnρ)dot.
    Wdot = P V (lnρ)dot;              E = V U.

Trabalho W em joules, positivo na compressão. Balanço ΔE=Qretido+W. Exportar
ρ,V,E,W,Q disponível/Qν/Qretido em unidades explícitas. Contagens globais e
extensões totais usam N_b; densidades instantâneas usam n_b(t). Nunca chamar
extensão por volume atual de contagem acumulada em volume inicial fixo.
Não somar Q de aniquilação novamente. Não incluir W como energia nuclear.

Controles forte/fraca/EM e18canais permanecem independentes. EOS/screening
são bool explícitos; screening exige Coulomb. Desligar todos os canais não
remove o trabalho externo: T pode evoluir com compressão/expansão. EMoff
permite p+p quando forte/fraca estão ligadas, como na rede aceita.

## Verificação previamente fixada

Radau em T,rtol1e−9,atol da rede mais1e−12 emT/1e7 e1e−13 emW/E0.
Referência BDF emE/E0 com inversão numérica da EOS, sem usar P_T ou U_Y;
fluxos montados manualmente. Refinamento Radau rtol2e−10.241amostras.
Comparações: erroY absoluto≤1e−8,T relativo≤1e−7,W/E0 absoluto≤1e−8.
Em cada resultado: balanço de energia normalizado≤1e−8,bárions≤1e−8,
catalisador relativo≤1e−8,carga nuclear+léptons por bárion≤1e−10;
resíduos negativos brutos permitidos somente até−1e−20, sem corte de traços.

Três casos completos, cada um com Radau/BDF/refinamento:

1.N14,15MK,ρ0=1,5e5kg/m³,V0=1m³,1000anos,exponential ratio1,05,todos ligados.
2.O16,mesmos T/ρ/V/duração,exponential ratio0,95,todos ligados.
3.N14,14MK,ρ0=1e5kg/m³,V0=1m³,1ano,cycle ratio1,05,todos os operadores
  nucleares desligados,EOS Coulomb/screening ligados. Y/ν imóveis,ρ/V
  retornam ao início,|ΔT|/T0 e|Wfinal|/E0≤1e−8; temperatura cresce no meio.

Controles adicionais:constant N14/1000anos contra caso isocóricoCoulomb
aceito e arquivado, após hash/configuração iguais;constant semCoulomb/
screening contra EOSideal aceita (100anos);weakoff eEMoff completos com
exponential ratio1,03/10anos. νatual=0 no weakoff; p+p/ν não devem ser zerados
por EMoff. Conservar balanço E e manter trabalho externo nos dois controles.
Sem reintegrar casos históricos aceitos quando seu arquivo completo serve
de referencial e hashes/configuração possam ser conferidos.

Recusar histórias/tipos/campos desconhecidos,ratio fora do intervalo,
extremosρ inválidos,screening semCoulomb,tolerâncias inválidas. Verificar
recusa de toda uma trajetória que começa válida e cruza o domínioT,sem
publicar curva parcial. Usar forças completas nos pedidos de teste.

Mesmo erro de energia pequeno não prova precisão física do plasma. Este
aceite é científico local; não aceita worker,interface,desempenho,transporte,
estrutura/luminosidade estelar ou o marcoC2-20 completo. Depois dos recibos,
contratar worker/artefato próprios e só então candidata de produto isolada.
