# IS6/C2-14 — preparação da primeira malha relativística

Preparação durante os testes da compressão. Não há implementação ou aceite
desta malha. Finalizar primeiro os aceites próprios da candidata de compressão.
Base de escopo: `CAMADAS-QUATRO-FORCAS.md` e a seção C2-14 do roadmap; preservar
os modelos nucleares, os produtos aceitos, o instalado e as sessões do dono.

O relatório de 18/10 registra sondas de curvatura/relógio e um percurso de luz,
mas nenhum botão de malha espacial. O primeiro passo será um módulo científico
isolado em `output/is6-spatial-staging`, antes de ligar qualquer cena ou botão.
Não declarar C2-14, C2-20 ou IS6 completos por essa fatia.

## Escolha científica preliminar

Exterior esférico estático, sem carga/rotação, uma fonte de cada vez. Usar
GM em m³/s² da fonte arquivada e c=299792458 m/s exato; raio areal r em metros.
O corte será t constante e θ=π/2 nas coordenadas de Schwarzschild, com

    Rs = 2 GM/c²
    ds² = -(1-Rs/r)c²dt² + dr²/(1-Rs/r) + r²dΩ²
    dl² = dr²/(1-Rs/r) + r²dφ²

A derivação própria do embedding euclidiano compara dl² com
dr²+r²dφ²+dz²: dz/dr=√[Rs/(r-Rs)] e z=2√[Rs(r-Rs)] mais uma constante.
Um único ramo descreve o exterior desta fatia; não acrescentar outro universo.
No limite GM=0, malha plana, razão de relógios1 e curvatura0.

Comprimento radial próprio vem da integral de dr/√(1-Rs/r), não da distância
euclidiana entre vértices de um desenho ampliado. Circunferência areal é 2πr.
Relógio estático tem dτ/dt=√(1-Rs/r). Comparar dois observadores estáticos com
√[(1-Rs/r1)/(1-Rs/r2)]; identificá-los como sustentados, não em órbita.
Usar o escalar de Kretschmann K=12Rs²/r⁶, em m⁻⁴, para mostrar curvatura;
o escalar de Ricci nulo no vácuo não significa espaço-tempo plano.

Todo ponto precisa estar fora do raio material adotado e de Rs. A associação
a um corpo real é uma aproximação exterior isolada: não somar funis de Sol,
Terra, Lua e Júpiter nem chamar o resultado de solução relativística conjunta.
O GM e a época ficam arquivados; órbitas newtonianas não mudam ao mostrar a
referência. O raio gráfico ampliado do marcador não define o domínio físico.

## Pesquisa primária e cuidado com a referência anterior

As [notas OIST, aula8, seções V/VII](https://www.oist.jp/sites/default/files/2024-10/Lecture8.pdf)
foram consultadas e arquivadas, com hash e URL em
`output/is6-spatial-research-20261101/acquisition.json`. Elas sustentam a métrica
exterior e a distinção de tempo próprio para observadores estáticos.

O [código documentado do EinsteinPy](https://docs.einsteinpy.org/en/stable/_modules/einsteinpy/hypersurface/schwarzschildembedding.html)
foi inspecionado pela consulta web: seu raio de embedding r/√(1-2M/r) é de
uma geometria óptica, diferente do raio areal do corte espacial proposto aqui.
O exemplo apontado no escopo não deve ser copiado como se fornecesse a malha
de Flamm deste contrato. A tentativa de arquivar esse domínio falhou no DNS.
A aquisição da aula de Gourgoulhon também expirou; não declarar cópias locais
dessas duas fontes ou depender delas para executar um teste.

## Antes de implementar

Fixar contrato de validação próprio com fixtures e tolerâncias antes do solver:
comparação independente em alta precisão de métrica, relógios, comprimentos,
embedding e curvatura; limite plano, unidades, transformação de corte,
refinamento da discretização e recusas de tipos/domínios. Não escolher os
limites olhando resultados. Separar geometria calculada e ampliação gráfica.

Somente após ciência aceita: ponte/cena, controle “Malha espaço-temporal” com
subtítulo “corte espacial do modelo”, seleção de fonte/plano, ampliação explícita,
sonda com r/comprimento/relógios/K e restauração da câmera. Sessões e ramos
precisam guardar o modelo e a visualização. Percurso CEF, imagens100/150% e
perfil próprio com camadas simultâneas permanecem etapas futuras.
