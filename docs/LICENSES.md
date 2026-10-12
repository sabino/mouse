# Licenças e distribuição

[Índice](README.md) · [Aquisição dos modelos](MODELS.md) · [Roadmap](ROADMAP.md)

## Código original e referência

O Mouse Invisível é uma implementação original e independente. O repositório está público,
mas nenhuma licença geral para o código original foi escolhida em nome do proprietário.
Visibilidade pública não substitui a definição dos direitos de uso/reutilização.
As dependências mantêm seus próprios termos. A referência ao vídeo e os limites de
atribuição estão em [REFERENCE](REFERENCE.md); nenhum código ou ativo sem licença foi copiado.

## Dependências diretas e runtime

Este quadro é um inventário de engenharia. Confirme os arquivos e módulos efetivamente
incluídos no pacote da plataforma antes de aprovar uma distribuição.

| Componente | Versão utilizada | Termos upstream / papel |
| --- | --- | --- |
| Python | 3.11/3.12; CI usa 3.12 | PSF; runtime empacotado pelo PyInstaller |
| NumPy | 1.26.4 | BSD-3-Clause; inferência numérica |
| SciPy | 1.15.2 | BSD-3-Clause e notices nativos; regressão/dependências |
| scikit-learn | 1.6.1 | BSD-3-Clause; classificadores pessoais |
| PySide6 / Qt | 6.8.3 | LGPL-3.0/GPL-3.0/comercial conforme módulo |
| MediaPipe | 0.10.21; 0.10.32 em macOS ARM | Apache-2.0 para o código; extractor de landmarks |
| OpenCV contrib | 4.11.0.86 | Apache-2.0 e notices de bibliotecas incluídas |
| pynput | 1.8.1 | LGPL-3.0; entrada/stop nativos |
| platformdirs | 4.3.7 | MIT; caminhos locais |
| dbus-next | 0.2.3, somente Linux | MIT; protocolo de portais |
| JAX / jaxlib | 0.4.35 | Apache-2.0 e notices nativos; dependência transitiva |
| PyInstaller | 6.12.0 | GPL-2.0 com exceção de bootloader; build nativo |

`uv.lock` e `requirements-dev.lock` fixam o grafo com marcadores por plataforma e hashes.
MediaPipe 0.10.21 tem tag interna Intel no wheel macOS; ARM seleciona 0.10.32. O projeto
não modifica metadata upstream nem suprime `pip check` para tratar essa diferença.

Cada build de CI gera `dependency-licenses.json` com textos de licença e o inclui no
arquivo nativo. Metadata de pacotes Python não comprova, sozinha, todos os termos de
FFmpeg, BLAS, Qt e outras bibliotecas embarcadas.

## Pesos externos

A licença Apache do código MediaPipe, a licença de um exemplo e o footer do site não são
adotados como prova dos termos separados de um `.task` binário. O arquivo não é baixado
nem redistribuído pelo projeto; obtenção permitida e confirmação com o provedor continuam
requisitos. Detalhes e o bloqueio de transporte observado estão em [MODELS](MODELS.md).

O modelo de gestos JSON contém parâmetros aprendidos nas sessões locais do usuário.
Ele não é um modelo pré-treinado externo ou um conjunto fictício de exemplos distribuído.

## Artefatos de CI e aprovação de release

Pacotes experimentais são públicos em Actions, têm retenção limitada e não constituem
uma release aprovada. Windows está unsigned; macOS usa assinatura ad-hoc, sem notarização.
Não há release publicada ou certificação de conformidade/distribuição concluída.

Antes de aprovar uma release ou distribuição comercial, é necessário:

- definir a licença do código original com o proprietário;
- conferir módulos Qt incluídos e suas obrigações; remover ou tratar qualquer módulo GPL-only;
- revisar notices e obrigações das bibliotecas nativas, além do inventário Python;
- atender às obrigações aplicáveis de LGPL, incluindo notices, fonte apropriada e
  possibilidade de substituir/relinkar bibliotecas; o formato com diretório/shared libs
  ajuda na implementação, mas não comprova conformidade por si só;
- confirmar termos de pesos que venham a ser incluídos ou compartilhados;
- concluir assinatura/notarização pretendida e aprovação do proprietário.

O [plano de entrega](ROADMAP.md) mantém esse marco separado de builds/testes e de aceitação
física. A disponibilidade de download não encerra a revisão de licenças.

## Fontes primárias

- [Licenciamento Qt](https://doc.qt.io/qt-6/licensing.html)
- [Qt for Python](https://www.qt.io/qt-for-python)
- [Licença do código MediaPipe](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE)
- [Licença OpenCV 4.11.0](https://github.com/opencv/opencv/blob/4.11.0/LICENSE)
- [Licença scikit-learn 1.6.1](https://github.com/scikit-learn/scikit-learn/blob/1.6.1/COPYING)
- [Licença pynput 1.8.1](https://github.com/moses-palmer/pynput/blob/v1.8.1/COPYING.LGPL)
- [Licença dbus-next 0.2.3](https://github.com/altdesktop/python-dbus-next/blob/v0.2.3/LICENSE)
- [Licença e exceção PyInstaller](https://pyinstaller.org/en/stable/license.html)
