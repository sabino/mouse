# Mouse Invisível

Aplicação desktop local para treinar gestos pessoais e controlar o cursor por câmera.
macOS, Windows e Linux X11 são os alvos de entrada; Wayland nativo oferece prévia e treino.
Começa **pausada**, sem gravação de vídeo e sem upload de imagens ou landmarks.

O MediaPipe extrai landmarks com redes neurais pré-treinadas. O modelo de gestos é
**aprendizado de máquina tradicional**, treinado nos seus exemplos: regressão logística
ou Gaussian naive Bayes sobre poses e movimentos temporais. Não há modelo de gestos
pronto, dados de treino inventados ou alegação de acurácia real. O cursor usa uma regressão
de calibração contínua separada dos gestos.

## Executar do código

Python 3.11 ou 3.12, sistema desktop de 64 bits. Com [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/sabino/mouse.git
cd mouse
git switch feat/desktop
uv sync --locked --extra dev
uv run --locked mouse-invisivel
```

Alternativa com pip (ative a venv conforme seu sistema):

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
mouse-invisivel
```

Linux: bibliotecas do sistema Qt/X11 (libgl1, libegl1, libxcb-cursor0, libxkbcommon-x11-0)
são necessárias. Se evdev precisar compilar, use um compilador C e headers Python/Linux;
neste Cloud, `CC=gcc` resolveu a ausência de clang. Não é usado uinput para controlar mouse.

## Primeiro uso

1. Obtenha por um canal permitido um arquivo **MediaPipe Hand Landmarker `.task` licenciado**
   da [documentação oficial](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker).
   Selecione na aba Prévia. Pesos não são baixados/bundled pelo app; a licença de
   redistribuição e o HTTP 403 observado neste Cloud estão em [LICENSES](docs/LICENSES.md).
2. Abra a câmera; escolha Right/Left conferindo a prévia espelhada. Grave múltiplos exemplos
   de cada gesto, `neutral` e `confusing`. Dê nomes aos gestos e mapeie depois; não há poses
   impostas por regras geométricas. Salve/exporte cada sessão JSON e crie novas sessões em
   dias/condições diferentes. Apenas landmarks, rótulos e metadados são persistidos.
3. Adicione duas ou mais sessões em Treinar. Escolha uma sessão inteira (ou pessoa) reservada
   e o classificador ANTES de avaliar. Confira relatório, rejeição, precisão/recall de
   episódios e falsas ativações por minuto neutro. Veja [protocolo de treino](docs/LEARNING.md).
4. Salve/recarregue o modelo JSON; configure ações/perfil, mão, monitor, sensibilidade,
   suavização e confiança. Calibre cinco pontos do alcance confortável do indicador.
   Salve o perfil/calibração JSON. Prévia mostra previsões sem entrada.
5. Verifique a entrada; pressione **Esc global uma vez** para testar o stop. Ative somente
   depois dos testes na prévia. Mostre `neutral` para armar e entre episódios de ação.
   `pointer` move; `click`/`secondary` clicam; `drag` segura; `release` solta; `scroll_up`/
   `scroll_down` rolam. O mapeamento é configurável. Esc/stop, perda de mão, atraso, mudança
   de perfil e erros pausam e tentam liberar apenas botões pressionados pelo app.

É possível exportar e excluir sessões pela interface. Modelos/perfis são JSON locais
independentes; exclua-os no gerenciador de arquivos se quiser remover parâmetros derivados.
Nenhuma permissão permanente é concedida automaticamente. O app exige teste físico do Esc
antes de ativar; no macOS, conceda permissões manualmente se desejar usar controle.

## Verificação e builds

```sh
uv run --locked python -m pytest -q
uv run --locked python -m ruff check src tests scripts
uv run --locked mouse-invisivel --diagnostics
uv run --locked python scripts/build.py
```

O workflow testa e gera artefatos nativos nos runners Windows/macOS/Linux. Cada build deve
ser executado no próprio sistema; não é cross-compile. Artefatos unsigned/ad-hoc estão na
aba Actions do repositório privado, sem publicar release. Pesos `.task` e dados pessoais
não entram no pacote. CLI `--smoke-test` abre/fecha a interface sem câmera/entrada.

[Estado de validação](docs/VALIDATION.md) separa testes sintéticos/simulados, GUI headless,
CI, build nativo e câmera/entrada física. [Plataformas](docs/PLATFORMS.md) cobre DPI,
monitores, permissões, falhas e Wayland. O Cloud não tem prova de usabilidade física.

Referência: [vídeo MW Informática](https://youtu.be/zmfJ6iwbW70). A análise por timestamps
continua bloqueada por transcrição inacessível; nenhum detalhe foi inventado e nenhum
código sem licença foi copiado. [Registro da referência](docs/REFERENCE.md).

O primeiro branch remoto foi `dev`; `main` foi criado depois no commit mínimo para PRs.
Nenhum PR foi merged e nenhuma release foi publicada. A implementação desktop completa
fica em `feat/desktop` enquanto os dois draft PRs empilhados são revisados.
