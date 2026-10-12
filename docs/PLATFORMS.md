# Plataformas e permissões

[Índice](README.md) · [Instalação](INSTALLATION.md) · [Aceitação física](VALIDATION.md)

## Matriz de suporte

| Ambiente | Implementação | Estado de validação |
| --- | --- | --- |
| Windows x64 | `SendInput`, DPI por monitor e desktop virtual | Testes/build/package em Windows CI; câmera e entrada físicas pendentes |
| macOS ARM | Quartz e bridge de Acessibilidade | Testes/build/package em macOS CI; permissões e hardware pendentes |
| macOS Intel | Dependências com marcador Intel e adaptador Quartz | Precisa de build e validação nesse hardware |
| Linux x64 / X11 | XTest, XRandR e stop global | Testes/build/package em Linux CI; hardware pendente |
| Wayland com backend compatível | Portais RemoteDesktop, ScreenCast e GlobalShortcuts | Protocolo com backend simulado; compositor físico pendente |
| Sway / wlr atual | Portais necessários ausentes | Entrada nativa indisponível; prévia/coleta/treino disponíveis |

O aplicativo não concede permissões persistentes automaticamente, eleva privilégios ou
modifica configuração de compositor. Diagnóstico é uma consulta de capacidades, não um
teste físico nem uma autorização de entrada.

## Windows

O processo solicita DPI per-monitor v2 antes de criar a interface. Os monitores usam
retângulos físicos; movimento absoluto é normalizado pelo desktop virtual, incluindo
origens negativas. `SendInput` tem retorno verificado.

Aplicativos de integridade maior, telas bloqueadas e desktops seguros podem rejeitar a
entrada. Não há elevação automática ou bypass de UIPI. Pacotes são diretórios unsigned.
Teste escala 100/150/200%, monitores mistos e mudança de layout na aceitação física.

## macOS

Quartz usa coordenadas globais em pontos, inclusive em Retina. A leitura de
`AXIsProcessTrusted` não solicita nem concede Acessibilidade. O usuário pode precisar
autorizar Câmera, Acessibilidade e Monitoramento de Entrada para o processo que está
executando. Trocar/recompilar o binário pode exigir rever essas permissões.

O bundle contém explicação de uso da câmera e assinatura ad-hoc local; não está notarizado.
Denial/revogação/erro deve pausar a entrada. Verifique o stop global fisicamente com outro
aplicativo em foco; a presença da bridge em CI não comprova a permissão no computador.

## Linux X11

Entrada exige display X11 e extensão XTest. XRandR fornece os monitores; servidores mais
antigos usam fallback para o retângulo total do desktop virtual. Não há backend `uinput`,
alteração de grupos/permissões de dispositivo ou necessidade de executar o app como root.

## Wayland por consentimento

`WAYLAND_DISPLAY` ou `XDG_SESSION_TYPE=wayland` seleciona o worker de portais. Mesmo com
um `DISPLAY` de XWayland disponível, ele não é usado como fallback de controle nativo.

Ao clicar **Autorizar portal / testar parada global**, o aplicativo solicita:

1. **RemoteDesktop:** somente ponteiro, `persist_mode=0`, sem restore tokens.
2. **ScreenCast:** seleção de monitores para metadados de coordenadas/identidade.
3. **GlobalShortcuts:** uma parada global escolhida pelo desktop; sugestão Ctrl+Alt+Shift+Esc.

O diálogo pode pedir compartilhamento de monitor. O aplicativo nunca chama
`OpenPipeWireRemote` nem lê pixels da tela; não pede injeção de teclado. É possível recusar
o consentimento e continuar em prévia/treinamento. Confira o atalho retornado e teste-o
fisicamente antes de ativar; Esc com a janela em foco é apenas uma parada local adicional.

As três interfaces, permissão de ponteiro, coordenadas válidas de monitor e um binding de
stop descrito são necessárias. Cancelamento, timeout, recusa, sessão revogada, serviço
reiniciado/desaparecido ou binding alterado bloqueiam o controle. Mudanças de layout/DPI
observadas pelo Qt param o worker e invalidam a calibração.

Movimento absoluto usa coordenadas do compositor e ID do stream selecionado, preservando
origens negativas e identidade de monitores espelhados. Enquanto a sessão remota for
válida, o aplicativo tenta liberar seus botões por esse canal. Depois que o compositor
destrói a sessão, a limpeza do dispositivo virtual pertence ao compositor: esse caso
precisa de validação física. Alguns backends podem recusar a identidade de um interpretador
standalone; a recusa é reportada, sem forjar identidade ou contornar a política.

### Limitação atual do Sway

O backend upstream `xdg-desktop-portal-wlr` anuncia somente Screenshot e ScreenCast.
RemoteDesktop e GlobalShortcuts não estão nessa lista. Instalar ou forçar outro backend
não demonstra suporte no compositor Sway. Controle nativo exige uma implementação que
realmente ofereça essas capacidades; não há esse aceite registrado no projeto.

Verifique o ambiente sem solicitar consentimento:

```sh
uv run --locked mouse-invisivel --check-portal
```

O resultado informa interfaces faltantes ou indisponibilidade do serviço/bus. Os testes
do repositório usam um D-Bus privado real com portal simulado; não são testes de Sway.

## Falhas e parada

Mão ausente/errada/ambígua, frames antigos/fora de ordem, landmarks degenerados e erros
de inferência interrompem ações. Erros de câmera ou desconexão aparecem na prévia e
pausam o controle. Buffering do driver e latência total precisam de medição real.

O worker tenta liberar somente botões que o aplicativo possui. Liberações que falham
permanecem pendentes e são tentadas novamente; o fechamento pode aguardar limpeza.
Nenhum timeout força o encerramento desse processo. Término forçado, falha do sistema
e revogação que também impeça liberar entrada não têm garantia de recuperação por software.

Registre sistema, câmera, escalas, monitores, permissões e resultados conforme o
[protocolo de aceitação](VALIDATION.md).

## Fontes primárias

- [Limitações do pynput](https://pynput.readthedocs.io/en/latest/limitations.html)
- [Windows SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [RemoteDesktop](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html)
- [GlobalShortcuts](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)
- [ScreenCast](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html)
- [Interfaces do backend wlr](https://raw.githubusercontent.com/emersion/xdg-desktop-portal-wlr/master/wlr.portal)
