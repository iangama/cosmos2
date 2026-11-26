# Cópia dinâmica dos16centros físicos

Próxima construção do IS6, após o perfil composto da cena0.25.1. Contrato
prévio em12/11/2026UTC; ainda sem resultado numérico ou implementação na UI.
O Atlas16 atual já fornece estados, GMs e procedência. A cópia dinâmica
atual continua limitada a três/quatro corpos. Ampliar o Atlas não ampliou
automaticamente as fontes da dinâmica.

Criar formato próprio solar_sixteen_physical_centers/0.1.0, schema3, em
fontes novas. Preservar integralmente os importadores e arquivos3/4corpos.
Os16IDs são10,199,299,399,301,499,599,699,799,899,501,502,503,504,602,606,
na ordem fixada no catálogo0.3.0. Não incluir partículas independentes dos
baricentros1–8. Cada GM é o parâmetro do corpo físico fixado no catálogo,
com sua fonte integral; não usar GM de sistema e acrescentar suas luas.
Luas/asteroides não presentes continuam omitidos e identificados como tal.

Primeira fatia: importador CPU isolado e fixture16na época
2026-10-11T12:00:00UTC, extraída somente dos dados já aceitos. O importador
valida IDs, ordem, época ET/TDB, unidades, frame J2000/ICRF, origem SSB,
estado geométrico simultâneo e hashes. Guarda catálogo e geração completos,
origens de posição/velocidade do baricentro escolhido e contrato científico.
Transforma para as mesmas unidades canônicas fixadas da bancada: G=1,
massa canônica=GM/GMunidade, posições e velocidades relativas ao baricentro
ponderado pelos GMs. GM não é uma medida de massa em kg.

Adotar massas pontuais newtonianas recíprocas, IAS15 epsilon1e−9, colisões
desabilitadas e softening zero. Não repor posições por efemérides durante a
evolução. Guardar as limitações: relatividade, multipolos, dissipação de
maré, outras luas, asteroides, plasma e forças não gravitacionais omitidos.
Campos magnéticos e bancadas nucleares não são aplicados automaticamente a
este novo formato. A geometria PCK permanece referência e não ativa colisões
ou torque sem um contrato posterior.

Verificar conversão nas cinco épocas já fixadas no contrato das luas,
incluindo limites da cobertura. Ida/volta SI deve ficar≤1mm por componente
de posição e≤1e−8m/s de velocidade. Rejeitar IDs ausentes, duplicados,
baricentros trocados por planetas, booleanos numéricos, NaN/infinito,
GM alterado, frames/épocas/procedência adulterados, campos extras e hash
recalculado sobre ciência inválida. Não gravar nem mudar o Atlas ao recusar.

Propagação própria de30dias,121amostras comuns a cada6h, preservando
toda a série. Comparar IAS15 de produção e refinado1e−12 (saída intermediária
a cada3h) com SciPy/DOP853 SI independente. A ODE calcula cada par por
a_i=Σ_j GM_j(r_j−r_i)/|r_j−r_i|³, sem chamar avaliador do produto. Usar
rtol2e−13, atol posição1mm/velocidade1e−9m/s, passo máximo3600s.

Manter os limites do IS2: diferença IAS15/DOP853≤10m e≤1e−5m/s por
componente; refinamento≤1m; deriva relativa de energia≤1e−9, deriva de
momento linear e angular normalizada≤1e−10. Normalizar por Σm|v| e
Σm|r×v| iniciais, nunca pelo momento total quase zero. Registrar deriva do
baricentro e número de passos. Testar atração recíproca de todos os120pares
com diferenças centrais de velocidade de±1s e±0,5s, extrapolação de
Richardson(4a_0,5−a_1)/3 e limite1e−10m/s² por componente. Os dois passos
retêm diagnóstico de truncamento, relevante para as luas de período curto.

Verificar invariância por translação/velocidade uniforme após retirar o
movimento da origem, sob os mesmos limites10m/1e−5m/s ao longo da série.
Fixar a transformação no executor antes de executar. Comparação posterior
com JPL mede diferença de modelo e não herda limites de erro numérico.
Uma recusa fica registrada antes de revisar código ou receita.

Só depois do aceite CPU: candidata própria para botão explícito, relógio,
sonda/contribuições, pausa/avanço, persistência/ramos, legado3/4, limpeza e
reabertura. Exigir capturas revistas e perfil próprio; manter0.25.1aberta
durante a preparação. Não mudar o atalho principal ou promover dados pelo
simples aceite do conversor. V1segue7/21; IS6permanece incompleto.
