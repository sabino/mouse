# Roadmap e plano de entrega

[Índice](README.md) · [Validação](VALIDATION.md) · [Desenvolvimento](DEVELOPMENT.md)

O plano organiza dependências e evidências. Não há datas prometidas: cada marco avança
quando seus critérios forem demonstrados. Código implementado, build disponível e
aceitação física têm estados diferentes.

## Estado atual

| Frente | Estado | Evidência ou dependência |
| --- | --- | --- |
| Captura/rotulação/treino/avaliação/persistência | Implementada | Testes sintéticos, GUI headless e pipeline congelado |
| Perfis, calibração, ações e política de segurança | Implementada | Runtime/worker com regressões e adaptadores simulados |
| Builds Linux x64, Windows x64 e macOS ARM | Disponíveis em CI | Arquivos, checksums, manifests e downloads verificados na referência funcional |
| Wayland por portais consentidos | Implementação de protocolo | Testes com D-Bus real/portal simulado; compositor físico pendente |
| Uso pessoal com câmera e entrada reais | Pendente | Modelo externo licenciado, dados e testes físicos |
| Controle nativo no Sway/wlr | Bloqueado | Backend atual sem RemoteDesktop/GlobalShortcuts |
| Release aprovada | Pendente | Aceitação física, licença/notices, escolha de licença original e assinatura |
| Análise detalhada da referência | Bloqueada | Transcrição acessível e timestamps verificados |

## Próximos marcos

### Marco 1 — modelo de landmarks disponível e documentado

**Entrega:** um caminho permitido de obtenção do `.task`, com origem/versão e termos
registrados, seguido de teste real de extração local. Veja [MODELS](MODELS.md).

**Aceitação:** o arquivo pode ser obtido sem contornar recusa de acesso; o uso pretendido
está coberto pelos termos do provedor; os landmarks e handedness são observados em câmera
real. O bloqueio de proxy 403 e a ausência de inferência física não são encerrados por um
simples import do runtime. Redistribuir pesos exige confirmação específica.

### Marco 2 — fluxo pessoal demonstrado em hardware

**Entrega:** sessões pessoais independentes, modelo/perfil recarregáveis e um relatório
de uso em ambiente de teste.

**Aceitação:** positivos, `neutral` e `confusing` foram coletados; treino/holdout permanecem
separados; limites de erro e latência foram definidos antes do teste; previsões, falsas
ativações, calibração, cliques, arraste/release e scroll foram observados. Stop global,
perda de tracking e fechamento durante arraste devem ter evidência de limpeza. Ajustes
feitos após examinar o holdout exigem uma sessão nova para avaliação final.

### Marco 3 — aceitação por plataforma e compositor

**Entrega:** registros por sistema/arquitetura/câmera/layout/permissão, conforme
[VALIDATION](VALIDATION.md), com falhas reproduzíveis convertidas em correções testadas.

**Aceitação:** câmera/entrada, DPI/monitores, foco, sleep/resume, desconexão/revogação e
latência foram exercitados em Windows, macOS e X11. macOS Intel exige sua própria prova
de build/uso. Wayland precisa de backend real suportado, consentimento, stop e teardown
de sessão confirmados fisicamente. Sway só recebe aceite quando suas capacidades realmente
existirem; não será habilitado por `uinput`, root, XWayland ou redução de segurança.

### Marco 4 — distribuição e release aprovadas

**Entrega:** pacote com licença/notices revisados, proveniência/checksums, assinatura
pretendida e documentação de suporte compatível com a evidência disponível.

**Aceitação:** licença do código original escolhida pelo proprietário; módulos Qt e
bibliotecas nativas auditados; obrigações aplicáveis atendidas; termos dos pesos confirmados
se houver redistribuição; assinatura/notarização e política de suporte definidas.
Uma release exige aprovação explícita. Artefatos públicos de CI continuam experimentais
até esses critérios serem encerrados. Veja [LICENSES](LICENSES.md).

### Marco 5 — experiência de uso refinada

**Entrega:** melhorias de onboarding, coleta/rotulação, mensagens de falha, visualização de
avaliação e gestão de perfis, priorizadas por observações de usuários.

**Aceitação:** mudanças preservam os guardas de segurança e os schemas ou têm migração
definida; o fluxo consegue ser concluído e recuperado após erros observados. Benefícios
de UX ou desempenho precisam de evidência, não apenas de uma nova opção na interface.

## Plano de execução

| Ordem | Trabalho acionável | Resultado para revisão |
| --- | --- | --- |
| 1 | Resolver aquisição/termos com o provedor e preparar hardware de teste | Registro de origem/termos e diagnóstico local |
| 2 | Coletar sessões independentes, treinar e testar primeiro em prévia | Dados locais, IDs de holdout e relatório sem alegação indevida |
| 3 | Verificar stop, calibrar e executar o checklist físico em um ambiente | Observações por etapa e falhas reproduzíveis |
| 4 | Corrigir falhas com regressões; repetir somente os checks afetados e a aceitação necessária | PR com comportamento, evidência e limites claros |
| 5 | Expandir a matriz para sistemas/arquiteturas/compositores disponíveis | Registros separados por ambiente, sem extrapolar CI |
| 6 | Auditar pacote/licenças, definir assinatura e revisar documentação | Checklist de distribuição para aprovação do proprietário |

O usuário fornece o contexto e as observações de hardware; mantenedores implementam e
revisam as correções. Dados pessoais permanecem locais por padrão. Compartilhá-los para
investigação é uma decisão separada, com consentimento.

## Ideias futuras

Estas possibilidades ainda não são compromissos de implementação nem capacidades prontas:

- explorar outros classificadores tradicionais/representações temporais com avaliação independente;
- tornar coleta, balanceamento de exemplos e comparação de sessões mais fáceis de revisar;
- melhorar associação de perfis a modelos/monitores e recuperação guiada de configuração;
- avaliar uma integração EIS/libei consentida quando houver backend/compositor apropriado;
- melhorar acessibilidade e feedback de estado após testes com usuários;
- ampliar a análise da inspiração quando uma transcrição permitida estiver disponível.

Qualquer nova ideia deve manter processamento local, limites de persistência, preview sem
entrada e stop verificável, além de declarar exatamente o que foi testado.
