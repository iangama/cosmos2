# Malha espacial — uso da candidata0.18.5

Candidata local isolada, sem substituir a instalação3.13. A revisão0.18.5
corrige encerramento; o perfil medido pertence à base0.18.2 e permanece
identificado assim no recibo consolidado is6-spatial-cut-20261102a.json.

Na pasta Cosmos2 do WSL, abrir com:

```sh
.tooling/python/Scripts/python.exe -Xutf8 scripts/launch-is6-spatial-revision-f.py
```

Na navegação, escolher **Malha espacial** e **Criar cena solar de referência**.
Isso abre a cópia pausada de Sol, Terra, Lua e Júpiter. Escolher o corpo,
limites radiais, quantidade de anéis, plano e ampliação; clicar **Abrir malha**.
Enquanto a candidata prepara, a vista confirmada permanece e o botão de
cancelamento aparece. Após a confirmação, **Recalcular malha** cria outro
artefato usando a mesma referência arquivada.

O centro excluído é o interior fora do modelo. Ciano identifica anéis;
violeta identifica meridianos. A altura usa ampliação gráfica explícita,
inicialmente200. A malha da Terra e da Lua permanece quase plana nessa escala.
Escolher outro plano muda o corte e a câmera acompanha sua orientação.

Em **Sondas exatas da malha**, escolher anel emissor, setor e anel receptor;
clicar **Consultar sonda**. A leitura inclui métrica, curvatura, relógios,
distância própria e posições física/exibida. Os índices selecionam vértices
e anéis calculados; não há interpolação da sonda. **Mostrar malha** muda
somente a visibilidade: as leituras continuam disponíveis.

Em **Salvar, restaurar e ramificar**, **Salvar vista** grava referência e
sondas juntas; **Carregar salva** restaura ambas. **Criar ramo** registra a
linhagem e o novo ramo passa a ser o pai das próximas alterações. Até32ramos.
**Exportar referência e vista** informa o caminho do JSON selado. Os arquivos
ficam em `output/is6-spatial-product0.18.5/spatial-checkpoints`, separados
das sessões do dono. Restaurar não muda a época/fase orbital atual.

**Recolher** fecha somente o painel, mantendo a malha. **Malha espacial**
reabre o painel. **Fechar vista e restaurar cena** remove os nós da malha e
restaura câmera e flags anteriores. Em150%, usar a rolagem do painel para
acessar sondas e persistência. A teclaEscape recolhe o painel e devolve foco
ao botão de navegação.

Em **Fonte, época e limites**, conferir GM, Rref, época e identificação do
artefato. GM vem da massa arquivada do cenário. Rref usa o maior semieixo da
referência PCK; não é o tamanho do marcador gráfico. O modelo é uma referência
esférica exterior isolada: não inclui rotação,J2,plasma ou soma de fontes GR.
O desenho não é uma simulação óptica. Os relógios comparados são estáticos
sustentados; a dinâmica orbital da cópia continua newtoniana e pausada.

Jornada nativa sequencial0.18.5 aceita emJ0E,com10capturas revistas,rodapé
correspondente ao instrumento e sonda nuclear sem rolagemhorizontal.
O perfil0.18.2 mantém seu próprioescopo;não houve perfilnovo0.18.5.
