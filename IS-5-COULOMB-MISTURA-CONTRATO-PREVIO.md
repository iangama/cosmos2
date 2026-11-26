# IS5/C2-20 — EOS Coulomb de mistura: contrato anterior ao código, 28/10/2026

Etapa seguinte à fundação DH/FD B aceita. Nova construção isolada em
`output/is5-coulomb-mixture-staging`, sem alterar fontes aceitas anteriores.
Escopo: energia livre não ideal de plasma totalmente ionizado, não magnético,
no recorte solar já adotado. Ainda não é evolução, trabalhador ou produto.

## Modelo e procedência

`fC = nb kT [Σ Yi fii(Γi) + Σ Yi fie(Zi,rs,Γe)
              + Ye fee(rs,Γe) + (ΣYi) Δfmix]`, em J/m³.
Usar `Ye=ΣZiYi`, `ne=nb Ye`, `ae=(3/(4πne))^(1/3)`, `rs=ae/aBohr`,
`Γe=e²/(4π ε0 ae kT)`, `Γi=Γe Zi^(5/3)`.

- `fii`: ajuste OCP clássico de Potekhin e Chabrier (2000), na seleção de
  coeficientes ajustados a Caillol usada por FITION9 e reproduzida em
  Potekhin et al. (2009), equações 5–6. A1=−0,907347; A2=0,62849;
  B1=0,0045; B2=170; B3=−8,4e−5; B4=0,0037;
  A3=−sqrt(3)/2−A1/sqrt(A2). Integrar uii/Γ para a energia livre.
  Não misturar com a seleção DeWitt de coeficientes da rotina Skye atual.
- `fie`: ajuste de polarização eletrônica de Chabrier/Potekhin, com a
  função h1 atualizada do apêndice C.1 de Potekhin e Chabrier (2013).
  Adaptar a expressão escalar de
  `ocp_liquid_screening_free_energy_correction` do MESA 26.4.1, sem
  correções quânticas de íons, extrapolação de fase ou limiar de abundância.
- `fee`: expressão EXCOR7 (Tanaka/Ichimaru e Perrot/Dharma-wardana),
  adaptada da energia livre escalar no mesmo MESA. θ=0,543 rs/Γe é a
  convenção arredondada desse ajuste; não confundir com solução FD exata.
- `Δfmix`: correção polarizável publicada no adendo de 2009, equações
  9–12, com δ da equação 10b, médias sobre número de ÍONS. Usar a fórmula
  completa e derivar também suas médias de composição. A equação 10b é
  exata no limite não degenerado e aproximação para degenerescência parcial;
  isso é limitação física do ajuste, não resolvida por testes numéricos.

Fontes primárias (consultadas nesta data):

- https://arxiv.org/html/0812.4344 (2009, texto e coeficientes OCP).
- https://arxiv.org/pdf/0909.3990 (adendo de 2009, 4 páginas).
- https://arxiv.org/pdf/1212.3405 (2013, versão arXiv v3 de 2018).
- https://github.com/MESAHub/mesa/releases/tag/26.4.1 e arquivos
  `eos/private/skye_coulomb.f90`, `skye_coulomb_liquid.f90`, fixados nessa
  versão. Originais e LGPL-3.0 preservados na pasta de pesquisa; a adaptação
  permanece sob LGPL-3.0-ou-posterior, com atribuição e fonte modificável.
- Código público dos autores: http://www.ioffe.ru/astro/EIP/eos22.f.
  Arquivo completo de 96.740 bytes adquirido para referência local após
  HTTPS falhar na cadeia TLS; nenhuma desativação da verificação TLS.
  Não integrar esse código ao produto. Revisar antes de compilar somente
  as rotinas FITION9/FSCRliq8/EXCOR7/CORMIX, com entrada local e sem rede.

## Termodinâmica

Todas as derivadas devem vir da energia livre escalar acima por
diferenciação automática de segunda ordem em `(lnT, lnnb, Y1..Yn)`.
Não aproximar o gradiente de composição por médias constantes.

Para densidade de energia livre f, `u=f−f_lnT`, `P=f_lnnb−f`,
`Cv=(f_lnT−f_lnTlnT)/T`,
`∂u/∂Yi=f_Yi−f_lnT,Yi`, `μCi=f_Yi/nb` (derivada neutra).
Somar à EOS ideal FD não relativística aceita, íons clássicos e radiação
LTE confinada. Não acrescentar outra entropia de mistura ao ideal;
Δfmix é apenas a parte não ideal. Fixar a composição na derivada de volume.
Retornar separadamente ii/ie/ee/mistura e o total, com procedência.

O modelo não inclui ionização parcial, pares, magnetização, sólidos,
correlação quântica dos íons ou transporte/hidro. Não chamar de MESA,
Skye completo, precisão de Monte Carlo ou modelo observado do Sol.

## Guardas anteriores à execução

T=10–30 MK; ρ=1e4–3e5 kg/m³. Listas 1–64 espécies, tipos SI estritos,
A/Z inteiros 1≤Z≤A≤300 e Z≤26; composição conserva ΣAiYi dentro de1e−8.
Yi≥−1e−20; resíduos negativos dentro do orçamento são continuados
analiticamente, preservados e identificados, sem clamp. Toda espécie com
Yi>0 participa das guardas; nenhuma espécie positiva é descartada.

Restringir Γi≤20, `Tp,i/T≤0,1`, `ni λi³≤0,01`, `pF/(me c)≤0,1`,
`kT/(me c²)≤0,01`, `0,01≤rs≤2` e `0,01≤θ≤1e3`.
São guardas conservadoras de recorte e de omissões, não precisão física.
Verificar Tp,i com o OCP da espécie na MESMA ne (`ni,ocp=ne/Zi`).
Não misturar temperatura de plasma OCP com abundância de um traço.

A fórmula de mistura contém 0/0 na composição de carga única. Para vetores
com cargas distintas, exigir variância `D−1≥1e−6`, com
`D=<Z²>/<Z>²`. Não apagar o gradiente de traços por uma decisão abrupta
de que a correção é zero. O ramo em que TODAS as cargas fornecidas são
idênticas tem Δfmix identicamente zero e pode ser tratado exatamente.
Estados com espécies de outra carga ausentes e D≈1 são recusados até
derivar o limite de composição completo. O H/He solar não cai nesse limite.

## Verificação antes de evolução

1. Componentes escalares e derivadas AD contra mpmath 50 dígitos, pelo
   menos 12 estados em T/ρ/composição, erro ≤2e−9 relativo à escala do
   componente (ou escala total declarada para componentes quase nulos).
   Verificar também uii por derivada da integral de uii/Γ independente.
2. P/U/Cv por componente contra as rotinas Fortran dos autores, nos mesmos
   rs/Γe/composição: erro ≤5e−5 relativo, permitindo constantes legadas
   arredondadas. Não comparar o ideal FD exato ao ajuste ideal dos autores
   como se fossem implementações idênticas.
3. Diferenças finitas de Cv e gradientes individuais, inclusive espécies
   inicialmente zero: ≤2e−6 em escala explícita; Maxwell na correção e
   total ≤2e−6. Testar separação ii+ie+ee+mix, permutação, divisão de uma
   espécie em duas com mesmo A/Z e redução exata da mistura para carga única.
4. Limite DH polarizável fraco de ii+ie+ee+mix, tratado como limite
   matemático das fórmulas (não extensão do domínio da zona); mistura linear
   sem correção não pode substituir esse limite. Expor o efeito de Δfmix.
5. Recusas de tipos/domínio/limite puro/traços; fontes e bases aceitas
   intactas por hash; arquivo de execução e falhas preservados.

Só após aceite: contrato de screening termodinâmico e evolução térmica
própria. Para a rede, manter Q/ν e Be7EC aceitos; screening de entrada deve
usar o composto com Z1+Z2, sem multiplicar EC/β. A mudança de correlação
entra em U e em suas derivadas, não como novo Q inventado.
