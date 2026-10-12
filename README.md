# Mouse Invisível

**Treine seus próprios gestos para controlar o mouse pela câmera.**

Aplicação desktop com processamento local, coleta de exemplos, treinamento e configuração
de entrada para macOS, Windows e Linux. A interface abre com a câmera fechada e o controle
pausado. O projeto está em estágio experimental: os builds e testes automatizados passam,
mas a usabilidade com câmera e entrada reais ainda precisa de validação em cada plataforma.

## Como funciona

O **MediaPipe Hand Landmarker** usa redes neurais pré-treinadas para localizar 21 pontos da
mão (*landmarks*). Esses pontos alimentam um **classificador tradicional treinado nos seus
exemplos**: regressão logística ou Gaussian Naive Bayes, com características de pose e
movimento ao longo do tempo. A calibração do cursor usa uma regressão contínua separada.

Você define os gestos e seus mapeamentos. É necessário fornecer um arquivo `.task`
licenciado e coletar sessões pessoais; o aplicativo não inclui um modelo de gestos pronto.
Confiança e estabilidade são guardas de execução, não regras geométricas que substituem
o classificador aprendido. Detalhes em [arquitetura](docs/ARCHITECTURE.md).

## Funcionalidades

| Área | Implementado |
| --- | --- |
| Coleta | Prévia local, clipes e sequências contínuas com rótulos explícitos; exportação e exclusão de sessões |
| Aprendizado | Exemplos de gestos, `neutral` e `confusing`; validação por sessão/pessoa e comparação de classificadores |
| Controle | Movimento do cursor, clique principal/secundário, arrastar/soltar e rolagem |
| Configuração | Perfis, mapeamentos, mão, câmera, monitor, sensibilidade, suavização e rejeição por confiança |
| Persistência | Modelos e perfis JSON versionados, parâmetros numéricos e limites de tamanho validados |
| Verificação | Replay sem entrada, diagnósticos, testes de segurança e builds nativos nos três sistemas |

## Plataformas e estado de suporte

| Ambiente | Caminho de entrada | Evidência atual |
| --- | --- | --- |
| Windows x64 | `SendInput`, coordenadas físicas e DPI por monitor | Build e testes nativos em CI; hardware pendente |
| macOS | Quartz e permissões de Acessibilidade | Build e testes em macOS ARM; hardware e build Intel pendentes |
| Linux x64 / X11 | XTest e XRandR | Build e testes nativos em CI; hardware pendente |
| Wayland com portais compatíveis | RemoteDesktop, ScreenCast e GlobalShortcuts com consentimento | Protocolo testado com portal simulado; compositor físico pendente |
| Sway / backend wlr atual | Sem os portais necessários para controle nativo | Prévia/coleta/treino disponíveis; entrada nativa bloqueada |

Consulte [plataformas e permissões](docs/PLATFORMS.md) e a
[matriz de validação](docs/VALIDATION.md) antes de considerar um ambiente pronto para uso.

## Instalação

A aplicação completa está em **`main`**. A branch padrão do repositório ainda é `dev`;
selecione `main` explicitamente.

Com Python **3.11 ou 3.12**, Git e [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/sabino/mouse.git
cd mouse
git switch main
uv sync --locked --extra dev
uv run --locked mouse-invisivel
```

Também há pacotes experimentais em execuções bem-sucedidas de
[Actions para `main`](https://github.com/sabino/mouse/actions?query=branch%3Amain).
Escolha o sistema e a arquitetura corretos, confira a origem e o checksum e extraia
o pacote nativo. São artefatos de CI com retenção limitada; nenhuma release foi publicada.

O [guia de instalação](docs/INSTALLATION.md) reúne downloads, comandos com pip,
dependências de sistema e lançamento dos pacotes.

## Primeiro uso

1. **Prepare os landmarks:** obtenha um Hand Landmarker `.task` por um canal permitido,
   confirme seus termos e selecione-o na prévia. Veja [modelos e licenças](docs/MODELS.md).
2. **Colete exemplos:** confira a mão na prévia espelhada. Grave seus gestos, movimentos
   neutros e exemplos confusos em pelo menos duas sessões independentes.
3. **Treine e avalie:** reserve uma sessão ou pessoa inteira e escolha o classificador
   antes de olhar os resultados. Salve/recarregue o modelo e confira as previsões.
4. **Configure e calibre:** mapeie as ações, selecione o monitor e calibre cinco pontos
   do alcance confortável. Salve o perfil, que inclui a calibração do cursor.
5. **Teste a parada e ative:** verifique o stop global com outro aplicativo em foco.
   Só depois ative o controle e mostre `neutral` para armar. Ações discretas exigem novo
   estado neutro entre episódios; a prévia permite conferir tudo sem injetar entrada.

O [passo a passo](docs/QUICKSTART.md) explica as abas, os limites de coleta e o comportamento
da parada. O [guia de treinamento](docs/LEARNING.md) orienta a avaliação pessoal.

## Segurança, privacidade e limites

- Processamento local; nenhum vídeo bruto é gravado e nenhum frame ou landmark é enviado
  pelo aplicativo. A coleta salva somente landmarks, rótulos e metadados quando solicitada.
- Controle pausado por padrão, ativação explícita, rejeição de baixa confiança, rearmamento
  neutro, watchdog e tentativa de liberação dos botões pressionados pelo aplicativo.
- Perda de tracking, atraso, erros ou mudanças de configuração pausam a entrada. A parada
  global precisa ser verificada fisicamente antes de cada novo processo de entrada.
- Permissões dependem do sistema e do consentimento do usuário. Wayland usa portais e
  não recebe um fallback por XWayland, `uinput` ou elevação de privilégios.
- Ainda faltam testes físicos, métricas com dados reais, confirmação dos termos do modelo,
  suporte efetivo no Sway e revisão final de distribuição/assinatura. Testes sintéticos e
  CI não demonstram acurácia real, latência da câmera ou segurança sob falhas do sistema.

O [roadmap e plano de entrega](docs/ROADMAP.md) organiza esses próximos marcos por dependência
e critério de aceitação, sem datas prometidas.

## Documentação

| Quero… | Guia |
| --- | --- |
| Instalar ou baixar um pacote | [Instalação](docs/INSTALLATION.md) |
| Fazer a primeira sessão | [Primeiro uso](docs/QUICKSTART.md) |
| Melhorar os dados e interpretar métricas | [Treinamento](docs/LEARNING.md) |
| Entender os componentes | [Arquitetura](docs/ARCHITECTURE.md) |
| Conferir permissões e Wayland | [Plataformas](docs/PLATFORMS.md) |
| Obter o `.task` e revisar licenças | [Modelos](docs/MODELS.md) · [Licenças](docs/LICENSES.md) |
| Desenvolver, testar ou gerar builds | [Desenvolvimento](docs/DEVELOPMENT.md) |
| Avaliar o que já foi comprovado | [Validação](docs/VALIDATION.md) |
| Acompanhar os próximos marcos | [Roadmap](docs/ROADMAP.md) |

O [índice completo](docs/README.md) reúne os caminhos de leitura.

## Inspiração e créditos

O vídeo **[“CRIEI UM MOUSE INVISÍVEL E FUNCIONA DE VERDADE”](https://youtu.be/zmfJ6iwbW70)**,
do canal **MW Informática**, inspirou a proposta. Esta é uma implementação original e
independente. A transcrição não pôde ser consultada; não são atribuídos ao vídeo algoritmos,
gestos específicos ou detalhes internos não verificados. Nenhum código ou ativo sem licença
foi copiado. O [registro da referência](docs/REFERENCE.md) documenta os créditos e limites
dessa análise.

A visibilidade pública do repositório não substitui a escolha de uma licença para o código
original. Os termos das dependências e dos modelos estão no [guia de licenças](docs/LICENSES.md).
