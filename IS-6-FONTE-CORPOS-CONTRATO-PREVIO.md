# IS6 — fontes da referência esférica, contrato prévio01/11/2026

Depois do aceite científicoC da malha, construir binding isolado em
`output/is6-body-binding-staging`. Não alterar o modelo0.1.1, seus aceites ou
o produto0.17.2. Esta etapa não aceita cena, interface ou desempenho.

Adotar do PCK00011 local já fixado os três raios de Sun10,Earth399,Moon301,
Jupiter599. Extrair somente dados ativos pelo kernelpoolSPICE, não exemplos
comentados. Arquivar hash do PCK,versãoSPICE,receita,unidade originalkm e
conversão×1000. Para guardar o domínio exterior esférico, usar o maior semieixo:
Sol695700000m,Terra6378136,6m,Lua1737400m,Júpiter71492000m. Não chamar esse
valor de raio observado exato:é fronteira de referência adotada; incerteza não
fornecida. Não substituir por raio de colisão,marcador gráfico ou WGS84 sem
outro modelo explícito. Sol/plasma e corpos reais não se tornam vácuo esférico.

Binding exige cópia solar pausada de quatro centros físicos,padrãoJ2000
baricêntrico e escala aceita. Reusar por mérito o validador imutável de fase
solar0.17.2,sem modificar seu código. Seleção por body_id exato,com guarda de
system_id/edit_token/revision/time/frame; recusar bool nos campos numéricos,
campos extras,identidade/época/escala/fase/centros incompatíveis.

GM da referência vem da massa atual do corpo na escala física do cenário,
registrando procedência/counterfactual. Não usar o GM do baricentro5 como
planeta599. Relógios são de observadores estáticos sustentados do modelo
isolado,não relógios do corpo em movimento. Orientação inicial em GALACTIC,
com plano definido pelo usuário; rotação do corpo,J2,outros corpos e plasma
ficam fora desta referência. Alterar/ocultar malha não muda atuação gravitacional,
época,velocidades,massa ou órbita newtoniana.

Descriptor selado deve guardar corpo/IDreferência,GM,raios/fronteira/procedência,
fase completa e seu hash,épocaUTC/TDB,centro/velocidadeJ2000,matrizJ2000→GALACTIC,
centro renderizado,catálogo e geração científica. Manter vértices relativos à
fonte,translação em metadado,sem subtrair posições globais grandes. Fronteira
adotada precisa estar fora de1,01Rs; recusar configuração incompatível sem
mover automaticamente o domínio ou trocar o modelo.

Validação antes de aceitar:quatro corpos×duas épocas pausadas e dois raios
exteriores1R/2R,comparação de centros/rotação/GM com fixture original e métrica
80dps; identidade/época/escala e origem preservadas. Conferir raios contra
literal de fixture independente das quatro entradas doPCK. Guardas de tipo,
mutação do descriptor,geração/PCK/catálogo divergentes e corpo não suportado
devem ser recusados sem alterar a fase. Metas:centro render≤1e−3m absoluto
contra transformação independente;GM e raios exatos às entradas double;
sondas≤3e−13rel,limite de domínio sem clamping. Fonte/descriptor devolvidos
são cópias independentes. Arquivar fontes/fixtures antes de executar.

Depois desse aceite,contratar artefato próprio com tipo,generation,configuração,
visibilidade/sondas e restauração selada. Produto/candidata,cena nativa,capturas
100/150% e perfis próprios continuam etapas posteriores.
