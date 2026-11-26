# C2-14 — serviço e controles antes da nova coleta

Partir da CPU aceita c214-orbits-numerics-20261114a. Conservar seu módulo,
fontes e dados. Preparar0.28.0 em namespace próprio, herdando a interface
0.27.0 sem alterar essa origem. Dados science1,5MiB devem existir no namespace
novo: os módulos de forças resolvem dados/proveniência relativamente ao produto.

## Atuação, comparação e relógio

Nova bancada: órbitas e tempo próprio, fonte esférica idealizada sem rotação,
com GM solar nominal de referência explícito. Os parâmetros de campo fraco
e o domínio CPU permanecem. Círculo e elipse são opções separadas; no círculo
não mostrar precessão ou período radial inexistentes. Comparação Newton usa
posição e tangente coordenadas iniciais comuns; sua elipse não é imposta igual àGR.

Atuação orbital ligada: geodésica CPU aceita. Suprimir atuação orbital:
reta nas mesmas coordenadas e mesmo t, com posição/velocidade iniciais idênticas.
É intervenção hipotética, sem alegar que a reta seja geodésica Schwarzschild.
A referência Newton e a geodésica completa ficam imutáveis em todos os controles.

Relógio ligado: τ calculado sobre a trajetória efetivamente escolhida, usando
a métrica de referência. Com A=1-r_s/r e velocidades coordenadas v_r e v_φ:

```
(dτ/dt)² = A - v_r²/(c² A) - v_φ²/c²
```

Na geodésica usar os tempos já validados. Na reta integrar o atraso t-τ
independentemente do desenho, sem subtrair clocks quase iguais. A intervenção
orbital torna essa trajetória não geodésica; o relógio continua sendo o de
uma linha de mundo temporal na métrica de referência. Suprimir efeito de
relógio aplica ritmo1 como hipótese e conserva τ de referência nos dados.
Desligar atuação gravitacional suprime ambos os operadores. Visualização
altera apenas camadas/legendas; resultados físicos e referências devem ser idênticos.

Integrar o atraso da reta em t/T0 por DOP853, rtol2e-12/atol2e-14, e conferir
por quadratura independente. Diferença de atraso≤2e-11·max(1,T_final),
taxa calculada da métrica≤2e-13 absoluta. Rejeitar linha não temporal,
interna à fonte ou orçamento excedido. Referências não são recalculadas com
os operadores hipotéticos. Toda órbita usa grade comum de t, nunca índice como tempo físico.

## Serviço e ciclo

Um cálculo assíncrono por bancada: parâmetros/controles congelados porjob,
ID de requisição e token de edição novos, revisão monotônica. Estado busy
não publica resultado parcial. Cancelar exige token atual, sinaliza evento
do solver e só libera a próxima execução depois do encerramento. Conservar
último resultado completo ao cancelar ou recusar. Ignorar conclusão obsoleta
por prova de identidade, sem substituir resultado de outra requisição.

Publicar status, submit e cancel em rotas próprias locais. Avaliação/exportação
sincrônica por forças mantém os mesmos limites15s/300milRHS e recusa resultados
incompletos. Salvar/retomar conserva controles, configuração e geração científica;
mudanças de geração são comunicadas. Registros e exportações do novo produto
usam pastas próprias; não sobrescrever sessões do dono ou da0.27.

Antes da UI nativa: testar quatro combinações orbital/relógio, atuação geral,
visibilidade, referências imutáveis, orçamento/cancelamento, busy e tokens
obsoletos, persistência/alteração de geração e HTTP malformado. Fixar receitas
e fontes antes de executar. Nenhum desses aceites substitui capturas revistas,
jornada nativa, ciclos de processo ou perfil próprios da nova bancada.
