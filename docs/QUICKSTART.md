# Primeiro uso

[Índice](README.md) · [Treinamento](LEARNING.md) · [Modelos](MODELS.md)

Prepare um `.task` licenciado e instale o aplicativo antes de começar. O fluxo abaixo é
uma orientação para validação pessoal; não é evidência de que o hardware já foi testado.

## 1. Abrir a prévia

Na aba **1 · Prévia e controle**, selecione o Hand Landmarker `.task`, a câmera e a mão
`Right` ou `Left`. Abra a câmera e confira a prévia espelhada: a mão selecionada deve estar
identificada corretamente e entregar landmarks estáveis. O controle continua pausado.

Se houver erro de câmera, permissão, mão ambígua ou tracking, corrija-o antes de coletar.
Trocar câmera/mão invalida a calibração e exige conferir novamente a prévia.

## 2. Coletar exemplos pessoais

Na aba **2 · Exemplos locais**, escolha um identificador de pessoa e um rótulo para cada
exemplo. Além dos gestos que pretende mapear, inclua sempre:

- `neutral`: postura ou movimento neutro, usado para rearmar o controle;
- `confusing`: transições, poses parciais, gestos parecidos e movimentos sem intenção de comando.

Use clipes para exemplos isolados. Para avaliar episódios, inicie uma sequência contínua,
mude explicitamente o rótulo ao mudar o gesto e inclua `neutral` entre ações. Mantenha cada
rótulo por pelo menos dois segundos. O aplicativo não decide os rótulos por você.

Exporte a sessão JSON e crie outra sessão independente. Colete cada classe nos dois
conjuntos, variando condições e movimentos. Uma divisão de clipes da mesma sessão não
substitui uma sessão reservada independente.

| Limite | Valor |
| --- | --- |
| Classes do modelo / mapeamentos do perfil | Até 32, incluindo `neutral` e `confusing` |
| Clipes por sessão | Até 1.000 |
| Frames coletados pela interface por sessão | Até 6.000; cerca de 200 s a 30 fps |
| Arquivo JSON | Até 32 MiB em UTF-8 |

Ao atingir o orçamento de frames, a coleta para e preserva segmentos válidos em memória.
Exporte e crie uma nova sessão. Cancelamentos ou segmentos curtos/irregulares podem
descartar o trecho atual. Uma exportação inválida mantém o arquivo anterior intacto.

## 3. Treinar, avaliar e recarregar

Na aba **3 · Treinar e avaliar**, adicione pelo menos duas sessões JSON, reserve uma
sessão inteira ou pessoa e escolha `logistic` ou `gaussian_nb` antes de examinar os scores.
Treine e veja a matriz de confusão, rejeições, métricas por classe e diagnósticos de
episódios/tempo neutro. Use o [protocolo de treinamento](LEARNING.md) para interpretar esses
resultados e planejar uma avaliação final independente.

Salve o modelo JSON, recarregue-o na prévia e teste movimentos neutros, transições e gestos
parecidos. Confiança alta do modelo não é uma probabilidade validada de segurança.

## 4. Configurar o perfil e calibrar o cursor

Na aba **4 · Perfil e calibração**, configure ações, monitor, sensibilidade, suavização,
confiança, margem e estabilidade mínima. O modelo de gestos e a calibração do cursor
têm funções separadas. Calibre cinco pontos do alcance confortável do indicador e salve
o perfil JSON; ele contém os parâmetros da calibração.

| Ação configurável | Efeito |
| --- | --- |
| `none` | Não gerar entrada |
| `pointer` | Mover o cursor enquanto o estado permitir |
| `click` / `secondary` | Clique principal / secundário |
| `drag` / `release` | Segurar / soltar o botão do aplicativo |
| `scroll_up` / `scroll_down` | Rolar por um episódio de gesto |

Os rótulos `neutral` e `confusing` permanecem sem ação. Os demais nomes de gestos podem
ser pessoais; associe-os às ações desejadas. Ajustar mão, modelo ou perfil pausa a entrada.

Em Wayland, autorize o portal antes de selecionar os monitores consentidos e conferir a
calibração. Se os portais necessários estiverem ausentes, continue em prévia/treino.

## 5. Verificar a parada global

Solicite **Verificar entrada / testar Esc global** no Windows/macOS/X11. Pressione Esc
com outro aplicativo em foco e confira a confirmação do stop. O teste é exigido antes
da ativação de cada novo processo de entrada.

Em Wayland, use **Autorizar portal / testar parada global**. O desktop apresenta os
diálogos de ponteiro/monitor e de atalho. Confira e teste o atalho informado; a sugestão
é Ctrl+Alt+Shift+Esc. Esc dentro da janela é uma parada local adicional, não o atalho
global Wayland. Leia [plataformas](PLATFORMS.md) para entender a limitação atual do Sway.

## 6. Ativar em um ambiente de teste

Confira a prévia, o monitor e os mapeamentos. Escolha um aplicativo de teste sem conteúdo
crítico, ative o controle e mantenha `neutral` estável para armar. Mostre novamente o estado
neutro entre episódios discretos. Movimento contínuo e arraste seguem a política do
perfil; `release` e as guardas de segurança podem soltar um arraste sem novo comando neutro.

Use o botão **PARAR AGORA** ou o stop global diante de comportamento inesperado. Perda de
mão, atraso ou erro pausa e tenta liberar botões do aplicativo. Se a liberação falhar, o
fechamento pode permanecer pendente aguardando limpeza; não há garantia sob término
forçado do processo, falha do sistema ou permissão que impeça a liberação.

## Arquivos e privacidade

Sessões, modelos, avaliações e perfis são salvos localmente por escolha explícita. A pasta
sugerida segue `platformdirs`; `MOUSE_DATA_DIR` pode alterar a pasta de dados. Vídeo bruto
e áudio não são persistidos. Excluir uma sessão não remove automaticamente parâmetros
de modelos já treinados: exclua-os ou treine novamente se quiser remover os dados derivados.
