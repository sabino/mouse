# Validação e critérios de aceitação

[Índice](README.md) · [Plataformas](PLATFORMS.md) · [Roadmap](ROADMAP.md)

## Evidência disponível

Referência funcional: commit `26f02722c1882777c3839426f8d4dea00f2242ca` de `main`,
verificado em 12 de outubro de 2026. A [execução pós-integração](https://github.com/sabino/mouse/actions/runs/38200339111)
passou nos três sistemas, incluindo build, testes do pacote, validação do arquivo e upload.
Para estados posteriores, consulte [Actions de `main`](https://github.com/sabino/mouse/actions?query=branch%3Amain).

| Tipo de evidência | O que foi verificado | O que não demonstra |
| --- | --- | --- |
| Unitários / ML sintético | Features, separação de dados, parâmetros JSON e equivalência numérica com scikit-learn | Acurácia com mãos reais ou generalização |
| Runtime / entrada simulada | Neutral/rejeição, staleness, watchdog, posse/liberação, falhas e fechamento atrasado | Resposta física do dispositivo/compositor |
| Replay | Sessões no formato persistido, política e releases em gaps/timestamps fora de ordem | Dataset real já capturado ou latência do sensor |
| GUI headless | Coleta/rotulação/treino/preview, orçamento de frames, perfis e reload | Uso com câmera, permissões ou monitor físicos |
| Protocolo Wayland | Onze cenários em D-Bus privado real com portal simulado e worker de produção | Funcionamento no Sway ou em outro compositor real |
| Diagnóstico nativo | Bridge macOS e ABI/coordenadas Windows sem injeção | Permissão de câmera/entrada concedida ou uso real |
| Build / pacote nativo | Imports, GUI sem dispositivos, worker de gravação simulada, treino/reload/replay e arquivos | Usabilidade física ou aprovação para release |
| Entrega | Três uploads e downloads de artefatos via GitHub concluídos | Execução pós-download no computador do usuário |

Na referência acima, Linux x64 passou **43 testes** e pulou dois checks de outra plataforma.
macOS ARM e Windows x64 passaram **33 testes** e pularam doze checks esperados de outra
plataforma, incluindo os cenários Linux. Os skips não são aceites físicos.

Os downloads retornaram referências ZIP utilizáveis. A transferência dessas referências
para o ambiente Cloud foi bloqueada; não se afirma execução pós-download nesse ambiente.
Os executáveis foram testados em seus respectivos runners nativos.

## Regressões cobertas

- Release/desarme em landmarks degenerados, troca de mão, tracking perdido e frames antigos.
- Replay preservando releases após arraste em lacunas e timestamps fora de ordem.
- Cleanup do worker de produção com liberação atrasada/falha temporária; janela aguarda confirmação.
- Limites exatos de UTF-8, 32/33 classes/mapeamentos e 1000/1001 clipes, preservando arquivos anteriores.
- Persistência finita de Gaussian NB com exemplos de features constantes.
- Coleta limitada com sessão recarregável e perfil recarregável para modelo de 32 classes.
- Recusa/cancelamento/revogação de portais, ativação do serviço, parada e coordenadas de monitores.

## O que continua pendente

Não há dataset de mãos reais, replay desses dados, medição de acurácia real, câmera/entrada
física, teste de revogação em hardware, monitor/DPI real ou latência completa aceitos.
O `.task` licenciado ainda precisa ser obtido por canal permitido. O Sway/wlr atual não
oferece os portais necessários. Termos dos pesos, revisão final de distribuição/assinatura
e transcrição da referência permanecem pendentes.

## Protocolo físico por ambiente

Antes da avaliação, defina limites pessoais de erro/latência e registre sistema/versão,
arquitetura, câmera, iluminação, mão, monitores/escalas, commit, arquivos/versões e permissões.
Não registre uma etapa como aprovada sem observação real.

| Etapa | Procedimento | Critério de aceitação |
| --- | --- | --- |
| Inicialização | Abrir app/preview e conferir handedness, sem ativar | Câmera/landmarks corretos; nenhuma entrada antes da ativação |
| Dados e modelo | Sessões independentes com positivos/negativos; treino, holdout, save/reload | Métricas e erros registrados sem reutilizar holdout para uma alegação final |
| Calibração | Cinco pontos; monitor escolhido, origens negativas, escalas e Retina/misto | Cursor testado dentro do alcance/limites previamente definidos |
| Parada | Stop global com outro app em foco; teste antes de ativar | Stop recebido e botões do app liberados; reativação explícita |
| Ações | Pointer, cliques, arraste/release, scroll e mapeamentos em aplicativo de teste | Ações observadas, repetição/neutral e falsos comandos registrados |
| Falhas de câmera | Cobrir/desconectar/reconectar, negar/revogar acesso, mão errada/ambígua | Pausa visível e limpeza observada; recuperação explícita |
| Falhas de execução | Carga de CPU, hang de inferência/UI, sleep/resume e fechamento durante arraste | Watchdog/cleanup observados; limitações do sistema documentadas |
| Mudança de ambiente | DPI/layout/monitor, foco/integridade Windows, permissões macOS, display X11 | Pausa/diagnóstico e liberação observados, sem bypass de segurança |
| Wayland | Capacidades e consentimento, binding, revogação, encerramento de sessão e hotplug | Backend real suportado e teardown físico confirmado; Sway não presumido |

## Registro de resultado

Guarde versão/commit, configuração, IDs das sessões reservadas, relatório, observações
por etapa e falhas reproduzíveis. Informe limitações e o que não foi exercitado. Landmarks
e modelos pessoais permanecem locais; compartilhar dados para investigação é uma escolha
separada do usuário. O plano para encerrar essas pendências está em [ROADMAP](ROADMAP.md).
