# Desenvolvimento, testes e builds

[Índice](README.md) · [Arquitetura](ARCHITECTURE.md) · [Plano de entrega](ROADMAP.md)

## Estrutura do repositório

```text
README.md                 apresentação e início rápido
docs/                     guias, evidências e roadmap
src/mouse_invisivel/       aplicativo e componentes
tests/                    fixtures sintéticos e regressões
scripts/                  build, smoke do pacote e arquivos nativos
.github/workflows/        CI nos três sistemas
pyproject.toml            projeto, dependências e entrypoint
uv.lock                   lock com marcadores por plataforma
requirements-dev.lock     exportação com hashes para pip/CI
```

Saídas locais (`.venv/`, `build/`, `dist/`, `artifacts/`, `local-data/`, caches e `.task`)
são ignoradas pelo Git. Não versionar dados pessoais, pesos externos sem termos confirmados,
tokens, screenshots privados ou binários gerados.

| Módulos | Responsabilidade |
| --- | --- |
| `camera.py`, `features.py` | Captura local, landmarks, timestamps e features temporais |
| `dataset.py`, `storage.py` | Sessões rotuladas, schemas, limites e JSON atômico |
| `model.py`, `evaluation.py` | Treino tradicional, split independente e métricas |
| `calibration.py`, `profile.py` | Regressão contínua e configurações/mapeamentos |
| `runtime.py`, `safety.py`, `replay.py` | Inferência, política compartilhada e replay sem entrada |
| `input_worker.py`, `platforms.py`, `wayland.py` | Posse/cleanup de botões, watchdog e adaptadores |
| `gui.py`, `__main__.py` | Interface em português e CLI |

Não mova esses caminhos somente para reorganizar a apresentação: build, imports e CI usam
essa estrutura. Os detalhes internos estão em [ARCHITECTURE](ARCHITECTURE.md).

## Preparar o ambiente

Siga a [instalação](INSTALLATION.md), com um checkout de `main` e Python 3.11/3.12:

```sh
git switch main
uv sync --locked --extra dev
uv run --locked mouse-invisivel --help
```

Para alterações, crie uma branch a partir de `main`. A branch padrão ainda é `dev`; não
assuma que um clone inicial contém a versão desktop completa antes de selecionar `main`.
Preserve alterações locais de outras pessoas e faça mudanças com escopo revisável.

## Verificação local

```sh
uv run --locked python -m ruff check src tests scripts
uv run --locked python -m pytest -q
uv pip check
uv run --locked mouse-invisivel --check-libraries
uv run --locked mouse-invisivel --diagnostics
uv run --locked mouse-invisivel --check-portal
uv run --locked mouse-invisivel --check-worker
```

Essas verificações não abrem câmera nem injetam entrada. `--check-worker` usa um adaptador
de gravação simulada; os testes Wayland usam D-Bus privado/portal simulado. Linux precisa
de `dbus-run-session` para os cenários de protocolo.

Smoke da janela sem dispositivos, em shell POSIX:

```sh
QT_QPA_PLATFORM=offscreen uv run --locked mouse-invisivel --smoke-test
```

No PowerShell, defina `$env:QT_QPA_PLATFORM = "offscreen"` antes de executar a mesma flag
e use `Remove-Item Env:QT_QPA_PLATFORM` ao terminar, antes de abrir a interface normal.
Para treino/replay pela CLI com arquivos reais, veja [LEARNING](LEARNING.md). Os testes
sintéticos não devem se transformar em modelos de demonstração distribuídos.

## Dependências

Atualize `pyproject.toml`, mantenha os marcadores de plataforma e regenere os dois locks
no mesmo escopo. Revise hashes, licenças e imports nativos depois de uma atualização:

```sh
uv lock
uv export --locked --extra dev --format requirements-txt --no-emit-project --output-file requirements-dev.lock
```

CI instala o lock pip com `--require-hashes`, em venv isolada, e instala o projeto com
`--no-deps --no-build-isolation`. `pip check` não é suprimido. Mudanças em features ou
persistência precisam de versão/schema coerentes e testes de compatibilidade/rejeição.

## Build e arquivo nativo

Execute no sistema de destino; não há cross-compilation. **O checkout precisa estar limpo
e permanecer no mesmo commit durante build/empacotamento**, inclusive a documentação.
Conclua e revise as alterações antes de gerar um pacote associado a um SHA.

```sh
uv run --locked python scripts/build.py
uv run --locked python -m piplicenses --format=json --with-license-file --no-license-path --output-file=dist/dependency-licenses.json
```

Use o launcher nativo produzido para as verificações `--check-libraries`, `--diagnostics`
e `--smoke-test`. O smoke do pipeline congelado recebe esse caminho:

```sh
# Linux; substitua pelo caminho correspondente no Windows/macOS.
uv run --locked python scripts/check_package.py dist/MouseInvisivel/MouseInvisivel
uv run --locked python scripts/package_artifact.py
uv run --locked python scripts/verify_artifact.py artifacts
```

Windows usa `dist/MouseInvisivel/MouseInvisivel.exe`; macOS usa
`dist/MouseInvisivel.app/Contents/MacOS/MouseInvisivel`. O launcher Linux em `dist/` é o
mesmo do exemplo. O script `check_package.py` roda treino/reload/replay com fixtures
explicitamente sintéticos e um probe de worker sem entrada nativa.

Saídas de build ficam em `dist/`; arquivos de entrega ficam em `artifacts/`. Tar preserva
permissões/symlinks em Linux/macOS; Windows usa ZIP. O manifesto identifica commit,
plataforma, arquitetura e limites da evidência. O arquivo inclui inventário de licenças e
exclui pesos `.task`/`.tflite`. Revise [LICENSES](LICENSES.md) antes de aprovar uma release.

## CI e revisão

O [workflow](../.github/workflows/verify.yml) roda em PRs e pushes para `main`, `dev` e
`feat/**`. A matriz atual usa Ubuntu 22.04 x64, Windows 2022 x64 e macOS 14 ARM com Python
3.12. Cada job verifica código, dependências, imports, GUI sem dispositivos, testes,
licenças, build, pipeline congelado e o arquivo nativo antes do upload.

Revisões devem conferir escopo, comandos/links, segurança e regressões relevantes. Um
check verde com upload ausente/pulado não comprova entrega: confira artefatos e download.
Guarde o SHA e o tipo de teste efetuado. O checklist físico de [VALIDATION](VALIDATION.md)
permanece separado de CI. Não publique dados pessoais ou alegações de acurácia real com
base nos fixtures matemáticos.
