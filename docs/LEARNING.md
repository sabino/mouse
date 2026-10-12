# Treinamento e avaliação pessoal

[Índice](README.md) · [Primeiro uso](QUICKSTART.md) · [Arquitetura](ARCHITECTURE.md)

O aplicativo não inclui dados pessoais de demonstração nem um modelo de gestos pronto.
Os fixtures dos testes são exemplos matemáticos sintéticos: validam cálculos e integração,
sem demonstrar desempenho com mãos reais ou generalização.

## Coleta

Colete pelo menos duas sessões independentes. Para uma avaliação mais útil, planeje de
três a cinco sessões em dias e condições diferentes, mantendo todas as classes necessárias
em treino e avaliação. Isso é uma orientação de coleta, não uma quantidade comprovada
para atingir uma acurácia específica.

Para cada sessão, registre:

- múltiplos exemplos de cada gesto ou movimento que deseja mapear;
- `neutral`, incluindo repouso e movimentos neutros comuns;
- `confusing`, com transições, gestos semelhantes, poses parciais e movimentos sem comando;
- variação de velocidade, alcance, distância, ângulo e iluminação dentro do uso pretendido.

Rotule explicitamente. Use sequências cronológicas `neutral → gesto → neutral` para
avaliar episódios e rearmamento. Mantenha cada rótulo por pelo menos dois segundos.
Clipes isolados ajudam a classificar exemplos, mas lacunas entre eles resetam a política.
Não inclua outras pessoas sem consentimento.

A interface tem orçamento de 6.000 frames por sessão; exporte e comece outra ao atingir o
limite. Modelo e perfil aceitam até 32 rótulos/mapeamentos, incluindo os negativos.

## Separação de dados

Reserve uma sessão inteira antes de treinar. Para avaliar outra pessoa, reserve todas
as sessões dessa pessoa e mantenha dados independentes suficientes para treino. O código
divide sessões/pessoas antes das janelas temporais e ajusta o scaler apenas no treino.

Escolha `logistic` ou `gaussian_nb` antes de examinar o relatório. Os dois classificadores
são comparados descritivamente, mas a seleção não muda automaticamente por causa do
resultado reservado. Ambos os conjuntos devem conter `neutral`, `confusing` e todas as
classes de ação treinadas; o treino exige pelo menos cinco janelas válidas por classe.

Se ajustar poses, mapeamentos, confiança ou outros parâmetros com base nesse relatório,
colete uma nova sessão para a avaliação final. Os modelos são pessoais: um resultado
nesses dados não comprova desempenho em outras pessoas, câmeras ou ambientes.

## Interpretação do relatório

| Medida | O que ajuda a verificar |
| --- | --- |
| Precisão, recall e F1 por classe | Quais rótulos são confundidos ou perdidos |
| Matriz de confusão | Trocas entre classes e rejeições |
| Taxa de rejeição | Quanto movimento não passa pelos guardas de confiança/margem |
| Precisão/recall de episódios | Ações emitidas pelo replay da política de execução |
| Falsas ativações por minuto neutro | Comandos produzidos durante trechos negativos rotulados |
| Latência mediana de episódio | Tempo relativo ao início de um clipe rotulado |

Rótulos de clipe são anotações aproximadas, não timestamps de eventos anotados por
especialistas. A latência do relatório não é latência completa de câmera/sistema.
Métricas podem ser nulas quando falta tempo neutro ou evento suficiente para calculá-las.
Confiança é um score do modelo, não uma probabilidade validada de segurança.

Antes de ativar entrada, use a prévia para movimentos sem comando, transições e repetições.
Registre os limites de erro e latência que considera aceitáveis **antes** da avaliação
física. Nenhuma meta numérica de acurácia está demonstrada neste repositório.

## CLI sem entrada nativa

Execute na raiz de um checkout de `main` com as dependências instaladas. Substitua os
nomes e IDs pelos arquivos reais; o ID reservado é o campo `id` do JSON da sessão.

```sh
uv run --locked mouse-invisivel --train sessao-a.json sessao-b.json --holdout ID_SESSAO_B --classifier logistic --output modelo.json
```

Para reservar uma pessoa, acrescente `--by-person` e use o identificador dela em `--holdout`.
O replay também não abre câmera nem injeta entrada:

```sh
uv run --locked mouse-invisivel --replay sessao-b.json --model modelo.json --profile perfil.json
```

O perfil é opcional no replay; inclua-o quando quiser avaliar os mapeamentos configurados.
Salve/recarregue o modelo e o perfil antes das sessões físicas. A calibração do cursor
permanece uma regressão contínua separada da classificação de gestos.
