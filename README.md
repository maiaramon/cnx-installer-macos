# CNX Pack Installer — macOS

> 🇧🇷 Português abaixo · 🇺🇸 English below

Port para **macOS** do `CNX_Installer_v1.1`, originalmente feito para Windows.
Instala o **CNX Pack** (custom firmware Atmosphère) em um cartão SD de Nintendo Switch.

macOS port of `CNX_Installer_v1.1` (originally Windows-only).
Installs the **CNX Pack** (Atmosphère custom firmware) onto a Nintendo Switch SD card.

> **Créditos / Credits:** o CNX Pack é desenvolvido e mantido por **CostelaBR** —
> repositório oficial / official repo: **https://github.com/CostelaCNX/CNX**.
> Este projeto é apenas um instalador não-oficial para macOS. /
> This is an unofficial macOS installer; all firmware content belongs to the original project.

---

## Screenshots

| Idle | Running | Done |
|---|---|---|
| ![Installer](screenshots/installer.png) | ![Installing](screenshots/installer-running.png) | ![Done](screenshots/worked.png) |

---

<a name="portugues"></a>
## 🇧🇷 Português

### O que faz

1. Lista apenas os discos externos/removíveis (nunca toca no disco interno)
2. Formata o microSD selecionado em **FAT32** (exigido pelo CFW do Switch)
3. Baixa o CNX Pack mais recente direto do [release oficial](https://github.com/CostelaCNX/CNX/releases/latest) (~160 MB)
4. Extrai todos os arquivos no cartão
5. Extrai o pacote secundário escondido em `bootloader/bootlogo_atmo_sys.bmp`

### Requisitos

- **macOS 10.15 (Catalina) ou superior**
- **Conexão com a internet** (baixa ~160 MB do GitHub)
- Um leitor de cartão SD / o cartão conectado

Sem pacotes Python para instalar — usa o Python do sistema em `/usr/bin/python3`, que já vem com Tk/tkinter.

### Como usar

**Opção A — Dois cliques (mais fácil)**

1. Clique com o botão direito em **`CNX_Installer.app`** → **Abrir**
2. Clique em **Abrir** no aviso de segurança (necessário porque o app não é assinado)
3. Selecione o cartão SD na lista e clique em **INICIAR PROCESSO**

> **Por que botão direito → Abrir?** O Gatekeeper do macOS bloqueia apps não
> assinados na primeira execução. Botão direito → Abrir contorna isso uma vez.
> Depois você pode abrir com dois cliques normalmente.

**Opção B — Terminal**

```bash
/usr/bin/python3 ~/Documents/apps/CNX_Installer/CNX_Installer_mac.py
```

> Não use o `python3` do Homebrew — ele não inclui o tkinter.
> Sempre use o caminho completo `/usr/bin/python3`.

### Solução de problemas

| Problema | Solução |
|---|---|
| "App está danificado" / não abre | No Terminal: `xattr -cr ~/Documents/apps/CNX_Installer/CNX_Installer.app` e tente de novo |
| Cartão SD não aparece | Reconecte o cartão e clique em **Atualizar** |
| Falha ao formatar | Abra o Utilitário de Disco, ejete/desmonte o cartão e tente de novo |
| Falha no download | Verifique a internet; o app tenta automaticamente o repositório reserva |

---

<a name="english"></a>
## 🇺🇸 English

### What it does

1. Lists your external/removable disks (never touches the internal drive)
2. Formats the selected SD card as **FAT32** (required by Switch CFW)
3. Downloads the latest CNX Pack from the [official release](https://github.com/CostelaCNX/CNX/releases/latest) (~160 MB)
4. Extracts all files to the SD card
5. Extracts a secondary package hidden inside `bootloader/bootlogo_atmo_sys.bmp`

### Requirements

- **macOS 10.15 (Catalina) or later**
- **Internet connection** (downloads ~160 MB from GitHub)
- An SD card reader / the SD card connected

No Python packages to install — uses the system Python at `/usr/bin/python3`, which ships with Tk/tkinter.

### How to run

**Option A — Double-click (easiest)**

1. Right-click **`CNX_Installer.app`** → **Open**
2. Click **Open** in the security dialog (required because the app is unsigned)
3. Select your SD card from the dropdown and click **INICIAR PROCESSO**

> **Why right-click → Open?** macOS Gatekeeper blocks unsigned apps on first
> launch. Right-click → Open bypasses that one time. After that you can
> double-click normally.

**Option B — Terminal**

```bash
/usr/bin/python3 ~/Documents/apps/CNX_Installer/CNX_Installer_mac.py
```

> Do **not** use `python3` from Homebrew — it does not include tkinter.
> Always use the full path `/usr/bin/python3`.

### Troubleshooting

| Problem | Fix |
|---|---|
| "App is damaged" / won't open | Run: `xattr -cr ~/Documents/apps/CNX_Installer/CNX_Installer.app` then retry |
| SD card not listed | Reconnect the SD card, then click **Atualizar** |
| Format fails | Open Disk Utility, eject/unmount the SD card first, then retry |
| Download fails | Check your internet connection; the app will auto-retry with the backup repo |

---

## Estrutura / Layout

```
CNX_Installer/
├── CNX_Installer.app/        ← dois cliques aqui / double-click this
│   └── Contents/
│       ├── MacOS/CNX_Installer        (launcher → /usr/bin/python3)
│       ├── Resources/CNX_Installer_mac.py
│       └── Info.plist
├── CNX_Installer_mac.py      ← script standalone (mesma coisa / same thing)
├── screenshots/
└── README.md
```

## Licença / License

O CNX Pack é distribuído sob **GPLv3** pelo projeto original.
The CNX Pack is distributed under **GPLv3** by the original project.
See https://github.com/CostelaCNX/CNX for details.
