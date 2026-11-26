# C2-14 — referência CPU de órbitas e relógios aceita

Vinte cenários ligados passaram com execução base e refinada, incluindo oito
e dezesseis ciclos, excentricidades0,05–0,8 e L/r_s de1.000a100.000.000.
A quadratura independente por anomalia conferiu precessão e períodos em t/τ.
Maior erro de precessão por ciclo:1.7209e-12rad; maior erro
relativo de período coordenado:3.72626e-11, próprio:3.72633e-11.
O maior tempo base medido entre esses casos foi0.645201s no Windows.
São tempos dessa coorte, não perfil de interface.

A referência Newton por Kepler foi comparada a uma ODE cartesiana independente.
Círculo conserva raio/fase/relógio analíticos e não inventa periastro ou período
radial. Escala de massa×10 e orientação invertida passaram. Vinte e três
recusas cobrem domínio, tipos, parâmetros, orçamento e cancelamento.

Contrato:C2-14-ORBITAS-CONTRATO-20261114.md. Código imutável aceito:
output/c214-orbits-staging/timelike_orbits.py. Recibo:
evidence/c214-orbits-numerics-20261114a.json. Receitas anteriores à execução,
ZIP de fontes e quarenta arquivos brutos base/refinados estão em
output/c214-orbits-numerics-20261114a. Python3.12.10/NumPy2.5.4/SciPy1.18.1.

O estado inicial comum usa posição e velocidade coordenadas, não velocidades
locais iguais. A geodésica é exata Schwarzschild dentro do domínio fraco
adotado; a fonte é estática/idealizada e não reage. Não acoplar aos16corpos.
Interface, serviço, controles, persistência e residência desta nova bancada
ainda não foram aceitos. V1segue7/21;IS6/C2-14incompletos. ResidênciaF0.27
segue aceita e não precisa de repetição.
