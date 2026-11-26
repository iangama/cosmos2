# Curadoria de Malha espacial e Camadas — revisão separada

A revisão `output/original-flow-hotfix-staging-v2` prepara correções dos
painéis existentes e inclui a textura da Terra que faltava no rascunho de
Forças. Não foi instalada, promovida nem aceita pelo percurso nativo do dono.
Os 137 módulos científicos comparados permanecem byte a byte iguais. A
visualização principal com painel integrado continua pendente para C2-16/17.

## Defeitos reproduzidos e correções preparadas

Os arquivos dos painéis usados como referência são idênticos aos da versão
0.27. A execução isolada reproduziu 16 falhas em 22 verificações. A revisão
passou nas mesmas 22 verificações, com HTML/JavaScript reais e respostas HTTP
de teste. São recortes funcionais; não demonstram o funcionamento pelo atalho.

- Ausência inicial de conexão, perda posterior e leitura inválida deixavam
  controles disponíveis ou sem recuperação clara. A revisão bloqueia as
  ações, explica a indisponibilidade e permite tentar novamente. A retomada
  limpa o erro de conexão, conservando erros de domínio científico.
- Uma fase com 16 corpos ou uma cópia em movimento não tinha caminho claro
  no painel. Os painéis agora explicam a exigência vigente de quatro corpos
  e oferecem os comandos existentes para abrir Explorar ou pausar. Criar a
  cópia continua sendo uma ação explícita. Não houve ampliação do domínio
  científico para 16 corpos nem aceitação de modelos adicionais.
- Abrir um painel não recolhia o outro. A revisão mantém somente o painel
  escolhido aberto e atualiza `aria-expanded`, sem reorganização visual final.
- Na recuperação da Malha sem artefato, o botão de fechar já aparecia, mas
  um controle de visibilidade ainda podia tentar consultar o artefato ausente.
  A revisão expõe a recuperação sem esses controles. A hipótese inicial de
  botão de fechar escondido foi corrigida pela reprodução.
- O bloqueio da navegação durante a Malha dependia de eventos de ponteiro;
  o teclado ainda alcançava ações. A revisão usa bloqueio real dos botões e
  restaura sua disponibilidade ao encerrar a referência.
- Importar um ramo de Camadas mantinha o ramo anterior selecionado. A revisão
  conserva a seleção do novo ramo depois de reconstruir as opções.

## Evidência e limites

| Recorte | Resultado | Registro |
| --- | --- | --- |
| Painéis anteriores, isolados | 6 verificações passaram; 16 falharam como esperado | `evidence/original-panels-ui-offline-20261120e-before.json` |
| Painéis da revisão, isolados | 22 passaram | `evidence/original-panels-ui-offline-20261120f-candidate.json` |
| Layout com escala real de 100% e 150% | 4 verificações passaram; quatro PNG, controles alcançáveis por rolagem | `evidence/original-panels-ui-offline-20261120g-zoom.json` |
| Servidor HTTP separado | 14 verificações passaram; duas saídas 0 | `evidence/original-flow-hotfix-http-20261120a.json` |

O ensaio de layout usa o `scaleInterface` e o manipulador do seletor
`ui-scale` extraídos de `navigation.js`, com o adaptador da cena inerte. As
capturas de 150% do ensaio funcional anterior aplicavam apenas a classe
`large-ui`; elas não são prova de zoom real. Tentativas iniciais com uma
asserção inadequada em `fieldset` e uma espera genérica ficam preservadas,
substituídas pelos recibos acima. Nenhuma tentativa anterior foi reescrita.

O HTTP verificou catálogo de 12 cenários, gravidade, forte, fraca, relatividade,
IGRF14, os estados inativos dos serviços, salvar/retomar com a mesma geração
científica e exportar dentro da pasta privada da candidata. Uma cópia separada
sem textura retornou erro JSON legível e continuou atendendo. A candidata
testada não foi alterada para provocar a falha. Os dois servidores encerraram
com código 0, sem abrir um renderizador. Foram reconferidas as 96 dependências
adicionadas anteriormente nos namespaces legados.

## Próxima validação permitida

Permanece vigente a restrição de testes manuais do dono. A ausência de processos
de uma sessão antiga não indica término desses testes. Foi solicitada somente
a informação sobre seu término; enquanto não chegar, não abrir o aplicativo,
trocar processo/versão ou manipular sua interface.

Depois da indicação de término, conferir processos e preservar qualquer
experimento, câmera, época e favoritos antes de trocar a execução. Validar a
correção pelo atalho e pelos botões originais: abertura, criação da referência,
visibilidade, sondas, salvar/retomar/exportar, falha, tentar novamente e retorno,
em 100% e 150%. A bancada de Forças também precisa desse aceite nativo.

Os três atalhos atuais continuam distintos: `Iniciar-Cosmos2.cmd` usa
`app/server.py`; `Abrir-Planetas.cmd` pede 0.24.0; `Abrir-Planetas-e-Luas.cmd`
pede 0.25.1. Os dois últimos podem ativar uma janela de outra versão já aberta.
Nenhum atalho foi trocado nesta revisão. A coerência do percurso acessível
continua pendente de curadoria, assim como os demais achados manuais.
