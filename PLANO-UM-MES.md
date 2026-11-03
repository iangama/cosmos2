# Cosmos2 — meta de um mês e orçamento real de cota

Revisão 4.1, 12/10/2026. O dono estabeleceu duração de um mês e pediu a conta
pela quantidade semanal disponível. Meta de calendário:12/11/2026.
Este documento substitui as previsões de horas/meses da revisão4.0.

## Correção da previsão

As estimativas anteriores de 965–1.665 h na v1 e 1.455–2.545 h no roteiro completo
não foram calibradas por produtividade real do agente. Sua conversão para
9–55 meses foi inadequada para prever este projeto. Retirar essas previsões
do acompanhamento atual; conservá-las apenas como histórico explícito.
Não transformar horas hipotéticas de engenharia em quantidade de allowance.

O prazo de um mês é um objetivo do dono, não evidência de que todos os marcos
restantes cabem nele (23 após o aceite localC2-19 em13/10). As funcionalidades e critérios científicos continuam
no ROADMAP-GERAL.md. Reorganizar a execução e reaproveitar os dez modelos/base
existentes; não reduzir qualidade, prometer ciência não calculada ou marcar
um marco completo só para cumprir o calendário. Informar a entrega concreta
que coube e o trabalho que restar, se houver, sem prorrogar o prazo silenciosamente.

## Conta pela telemetria

Origem: eventos rate_limits da sessão/conta, sem usar tokens/contexto/tempo
decorrido. Saldo observado2026-10-13T01:33:39.213Z:8%na janela 300min e7%na
semanal 10080min. Percentuais são apresentados arredondados; a relação abaixo
é aproximação empírica, não regra oficial fixa do plano.

| Janela observada | Consumo cota 300min | Consumo cota semanal | Equivalência100%da cota 300min |
| --- | ---: | ---: | ---: |
| 12/10 12:40–15:59UTC | 98 pontos (1→99) | 16 pontos (47→63) | 16,33 pontos semanais |
| 12/10 17:41–20:32UTC | 99 pontos (1→100) | 16 pontos (63→79) | 16,16 pontos semanais |
| 12/10 23:01–13/10 01:34UTC, parcial | 92 pontos (0→92) | 14 pontos (79→93) | 15,22 pontos semanais |

Conta:100÷(15,22–16,33)≈6,1–6,6 cotas completas equivalentes da janela de5 h
por cota semanal. Usar **cerca de seis por semana** como orçamento conservador.
Uma cota completa equivalente é100 pontos da janela 300min; não são cinco
horas de trabalho executado, nem uma quantidade garantida de tarefas/mensagens.

Próximo reset semanal observado:18/10/2026 11:34:14America/Sao_Paulo.
Mantendo o calendário semanal, resets seguintes previstos25/10,01/11 e08/11.
Até12/11 existem quatro renovações mais os7%atuais:407 pontos percentuais
semanais disponíveis em tese.407÷(15,22–16,33)≈24,9–26,7cotas300min completas
equivalentes. Portanto **aproximadamente25–27 no mês; orçamento-base25**.
O primeiro saldo é parcial e os resets são os observados/esperados, não
quatro semanas novas disponíveis imediatamente. Conferir telemetria novamente.

A projeção pressupõe padrão semelhante ao observado, limites inalterados e
dedicação desse saldo ao Cosmos2. Outros usos da conta e mudança de tarefas
podem alterar a relação. Revisar após cada janela completa e reset real;
não usar essa relação para contornar esgotamento.

[OpenAI Docs: limites de uso](https://learn.chatgpt.com/docs/pricing) confirma
que modelo/tarefa/contexto/ferramentas/caching afetam consumo e que o painel
mostra limites/reset atuais. Os seis por semana são inferência dos eventos locais,
não uma capacidade universal estabelecida pela documentação.

## Orçamento de execução por semana

Os25 ciclos abaixo são orçamento de cota equivalente, redefinido para esta
revisão. Não comparar com os ciclos de horas hipotéticas da4.0. Os grupos
semanais são metas de entregas; só a evidência do avanço permite afirmar
quantos marcos fecharam. Trabalhar continuamente no escopo autorizado até
esgotamento real ou conclusão, registrando progresso útil por janela.

| Bloco do mês | Cotas equivalentes alvo | Resultado prioritário |
| --- | ---: | --- |
| Semana 1 | 6 | Instrumento nuclear AME2020, fraca ampliada, contratos/fontes e caminho Atlas→experimento |
| Semana 2 | 6 | Edição gravitacional/EM, sondas e campos 3D ligados à cena; comparação e resposta estelar |
| Semana 3 | 6 | Navegação e qualidade visual, expansão de conteúdo/superfícies e relatividade conforme provas |
| Semana 4 | 6 | Integração, histórico/saves, desempenho, pacote offline e experiências completas |
| Margem do mês | 1 | Correções concretas, recuperação ou maior gargalo demonstrado |

As frentes quânticas, neutrinos, plasma, galáctica e cosmologia do roteiro
continuam registradas; considerar provas aproveitáveis quando sustentadas
pela integração, sem afirmar que seisfrentes de pesquisa estarão completas
em uma janela. Não mover silenciosamente requisitos pedidos para um futuro
indefinido. Reestimar alcance pela quantidade de resultados entregues em cada
semana; se houver conflito de escopo/prazo, apresentar o conflito concreto.

Primeiro passo permanece o instrumento AME2020 de NUCLEOS.md. Já existem
contrato e fonte primária; aquisição/parser completo/mapa/UI ainda pendentes.
Salvamento em≤8%é checkpoint, não parada antecipada. Não alterar plano/modelo
de assinatura nem comprar créditos para cumprir a meta.

## Atualização após renovação observada13/10

Saldo atual observado2026-10-13T21:06:47.999Z:55%na janela300min e93%na semanal.
Reset semanal agora2026-10-20T19:32:47Z (16:32:47SãoPaulo). A projeção anterior
7%+quatro resets=407pontos/25–27cotas é histórica, não saldo atual. Mantendo
o novo calendário, resets seguintes previstos27/10,03/11 e10/11, quatro antes
da meta12/11. Saldo93%+400=493pontos semanais em tese;493÷(15,22–16,33)≈30,2–32,4
cotas300min equivalentes adicionais. Usar orçamento-base30, com os cinco
ciclos além dos25 anteriores para integração/validação/refinamento sem reduzir
conteúdo. Essa previsão depende do saldo ser dedicado ao projeto, da cadência
dos limites e da calibração histórica; não são horas executadas, allowance
imediatamente disponível ou garantia de fechar25marcos. Conferir telemetria
em cada retomada e após reset real. Trabalho segue até esgotamento real.

C2-01 aprovado localmente13/10, após contratos solares/propriedades, dezpacotes
verificáveis e cópia com checkpoint/fontes. Restam25marcos no roteiro,19da v1.
C2-18 e C2-19 foram concluídos posteriormente em13/10. Decisões próprias
por marco; saldo não é aceite. Restam23marcos,17da v1. O orçamento-base30
acima foi definido na renovação13/10; não é saldo
restante nesta atualização. Consultar a telemetria corrente no handoff.
