# Modelos: aquisição, uso local e termos

[Índice](README.md) · [Licenças](LICENSES.md) · [Treinamento pessoal](LEARNING.md)

## Dois arquivos com funções distintas

| Arquivo | Origem | Função |
| --- | --- | --- |
| Hand Landmarker `.task` | Provedor externo, termos a confirmar | Extrair landmarks com redes neurais pré-treinadas |
| Modelo de gestos JSON | Treino feito pelo usuário com suas sessões | Classificar poses/movimentos com ML tradicional |

O perfil JSON é outro arquivo: contém mapeamentos, configurações e a calibração contínua
do cursor. Nenhum modelo de gestos ou conjunto pessoal pronto é distribuído pelo projeto.
Pesos `.task`/`.tflite` não entram nos pacotes nativos.

## Obter o Hand Landmarker

1. Consulte a [documentação oficial](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker).
2. Confirme a origem, versão e termos do arquivo binário com o provedor. A licença do
   framework ou de um notebook não comprova, por si só, a licença separada dos pesos.
3. Obtenha o arquivo por um canal permitido e guarde-o localmente. Na aba de prévia,
   selecione o `.task`; o aplicativo não baixa o modelo automaticamente.
4. Antes de compartilhar/redistribuir o arquivo, confirme que os termos permitem esse uso.

O [exemplo Python oficial](https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb)
referencia o ativo versionado:

```text
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

O [model card de Hand Tracking](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20%28Lite_Full%29%20with%20Fairness%20Oct%202021.pdf)
é uma fonte complementar sobre o modelo; não é tratado aqui como confirmação de licença
para redistribuir os pesos.

## Bloqueio observado no ambiente de desenvolvimento

O acesso ao ativo oficial falhou durante a abertura do túnel HTTPS do proxy:

```text
<urlopen error Tunnel connection failed: 403 Forbidden>
```

Não houve resposta HTTP do servidor Google Storage, headers do modelo ou bytes do arquivo.
O registro demonstra uma recusa no proxy desse ambiente; não permite concluir que o
provedor exige credenciais para o ativo. A aquisição foi interrompida, sem bypass de proxy,
espelho não verificado ou tentativa de contornar o acesso negado.

A revisão das fontes primárias não estabeleceu explicitamente os termos do binário.
Disponibilidade de um `.task` licenciado e teste real de extração continuam pendentes.
Uma interface/build que importa o MediaPipe não demonstra inferência com o modelo.

## Persistência do modelo pessoal

Modelo de gestos e perfil são JSON limitados/versionados, com validação de parâmetros
numéricos. Não há pickle/joblib ou classes Python executáveis no arquivo de modelo.
Sessões exportadas contêm landmarks, rótulos e metadados; proteja esses dados e os
parâmetros derivados conforme sua preferência. Excluir a sessão não apaga modelos que
foram treinados nela. Consulte [primeiro uso](QUICKSTART.md) e [licenças](LICENSES.md).
