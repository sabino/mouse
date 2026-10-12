# Instalação e downloads

[Índice](README.md) · [Primeiro uso](QUICKSTART.md) · [Plataformas](PLATFORMS.md)

## Requisitos

- Sistema desktop de 64 bits, câmera acessível e monitor.
- Um arquivo **MediaPipe Hand Landmarker `.task` de origem confiável e com termos confirmados**.
  Ele é um requisito separado do pacote; veja [modelos](MODELS.md).
- Para executar pelo código: Git, Python **3.11 ou 3.12** e uv ou pip.
- Permissões de câmera/entrada conforme o sistema. Builds e CI não confirmam essas permissões
  no computador de quem instala.

Os alvos com builds de CI são Linux x64, Windows x64 e macOS ARM. macOS Intel exige um
build local e ainda não tem essa evidência de CI. Wayland precisa de um backend compatível
com os portais usados; Sway/wlr atual permite prévia e treino, mas não controle nativo.

## Opção A — pacote nativo experimental

1. Abra [Actions filtrado por `main`](https://github.com/sabino/mouse/actions?query=branch%3Amain).
   Escolha uma execução bem-sucedida da branch `main` e confira o commit.
2. Baixe o artefato `MouseInvisivel-<sistema>-<arquitetura>-<sha>` adequado.
   O GitHub pode exigir login. Os artefatos expiram após a retenção configurada, hoje 14 dias.
3. Extraia o ZIP externo de Actions para uma pasta. Dentro dele estão o pacote nativo,
   `artifact-index.json`, `BUILD-INFO.json` e `SHA256SUMS.txt`.
4. Com Python 3.11/3.12 e um checkout de `main`, verifique os bytes e a origem:

   ```sh
   python scripts/verify_artifact.py PASTA_EXTRAIDA_DO_ACTIONS
   ```

   O script verifica checksum, tamanho, manifesto, launcher e exclusão de pesos `.task`/
   `.tflite`. Sem Python, confira o SHA256 do pacote com uma ferramenta do sistema e
   compare com `SHA256SUMS.txt`; isso não executa todas as validações do script.
5. Extraia também o pacote **interno**: `.tar.gz` no Linux/macOS ou `.zip` no Windows.
   Preserve a pasta inteira e as permissões/symlinks do tar; não copie somente o executável.

| Sistema | Launcher após extrair o pacote interno |
| --- | --- |
| Linux | `./MouseInvisivel/MouseInvisivel` |
| Windows | `MouseInvisivel\MouseInvisivel.exe` |
| macOS | `MouseInvisivel.app` ou `./MouseInvisivel.app/Contents/MacOS/MouseInvisivel` |

Pacotes são builds de engenharia: Windows não está assinado e macOS usa assinatura ad-hoc,
sem notarização. Se o sistema recusar a execução, registre o diagnóstico; não desative
as proteções para contornar a recusa. A execução pelo código é uma alternativa, sujeita
às próprias permissões. Não há instalador oficial ou release publicada.

## Opção B — código com uv

A aplicação completa está em `main`; a branch padrão ainda é `dev`.

```sh
git clone https://github.com/sabino/mouse.git
cd mouse
git switch main
uv sync --locked --extra dev
uv run --locked mouse-invisivel
```

`--extra dev` inclui as ferramentas de teste e build. O lock mantém versões e marcadores
por plataforma. Para um checkout existente, confirme que está em `main` e atualize por
fast-forward, preservando suas alterações locais.

## Opção C — código com pip

Depois de clonar e selecionar `main`, crie uma venv e ative-a.

Linux/macOS:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
mouse-invisivel
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
mouse-invisivel
```

Se a política do PowerShell impedir a ativação, use diretamente
`.\.venv\Scripts\python.exe` nos comandos Python e
`.\.venv\Scripts\mouse-invisivel.exe` para abrir o aplicativo. Não é necessário alterar
uma política permanente para usar a venv.

## Dependências de sistema no Linux

Em Debian/Ubuntu, o CI instala:

```sh
sudo apt-get install libgl1 libegl1 libxcb-cursor0 libxkbcommon-x11-0 dbus
```

Em outras distribuições, instale os equivalentes via gerenciador de pacotes. Se `evdev`
precisar compilar, são necessários compilador C e headers Python/Linux. Uma compilação
que procura `clang` pode usar `CC=gcc uv sync --locked --extra dev` quando GCC estiver
disponível. `evdev` como dependência não habilita um backend `uinput` no aplicativo.

## Conferência inicial

Pelo código, estes comandos não abrem câmera nem injetam entrada:

```sh
uv run --locked mouse-invisivel --check-libraries
uv run --locked mouse-invisivel --diagnostics
uv run --locked mouse-invisivel --check-portal
```

`--check-portal` consulta capacidades; a autorização por diálogos só acontece ao solicitar
entrada na interface. No pacote nativo, acrescente as mesmas flags ao launcher.
Depois siga o [primeiro uso](QUICKSTART.md).
