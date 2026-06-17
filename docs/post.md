# Post de divulgação — CNX Pack Installer para macOS

> Texto pronto para copiar e colar (Reddit, fóruns, GBAtemp, GitHub Discussions, Discord, etc.).

---

## Instalei um jeito de rodar o CNX Pack no macOS (sem precisar de Windows)

Fala, pessoal!

Quem usa Mac e queria montar o cartão SD com o **CNX Pack** (o pacote all-in-one de custom firmware Atmosphère pro Nintendo Switch, do **CostelaBR**) provavelmente já sofreu: o instalador oficial é só pra **Windows**. Eu fiz um **port pro macOS** e disponibilizei tudo de graça e open source.

### Repositório
**https://github.com/maiaramon/cnx-installer-macos**

### O que ele faz
- Lista só os **discos externos/removíveis** (nunca encosta no disco interno do Mac)
- Formata o microSD em **FAT32** (exigência do CFW)
- Baixa o **CNX Pack mais recente** direto do release oficial (~160 MB)
- Extrai tudo no cartão, inclusive o pacote secundário escondido no `bootloader/bootlogo_atmo_sys.bmp`

### Como usar (2 cliques)
1. Baixe o **`CNX_Installer.app.zip`** na aba [Releases](https://github.com/maiaramon/cnx-installer-macos/releases) e descompacte
2. **Botão direito no `.app` → Abrir** (só na 1ª vez, porque o app ainda não é assinado pela Apple)
3. Selecione o cartão SD e clique em **INICIAR PROCESSO**

> Se aparecer *"o app está danificado / desenvolvedor não verificado"*, é normal em app gratuito não assinado. Resolve com o botão direito → Abrir, ou rodando no Terminal:
> `xattr -cr ~/Downloads/CNX_Installer.app`

### Detalhes técnicos
- Interface em **Tkinter** rodando no **Python do sistema** (`/usr/bin/python3`) — **zero dependências** pra instalar
- Compatível com **macOS 10.15 (Catalina) ou superior**
- Código aberto sob **GPLv3**, README bilíngue (PT/EN) e contribuições são bem-vindas via issue/PR

### Créditos
O **CNX Pack** é todo desenvolvido e mantido pelo **CostelaBR** -> https://github.com/CostelaCNX/CNX. Este projeto é **só um instalador não-oficial pra macOS** — todo o firmware pertence ao projeto original.

Qualquer bug ou sugestão, abre uma issue no repo. Espero que ajude a galera de Mac.

---

## Short English version

**Run the CNX Pack on macOS — no Windows needed**

The official CNX installer (Atmosphère CFW pack for Nintendo Switch, by CostelaBR) is Windows-only, so I made a free, open-source **macOS port**: https://github.com/maiaramon/cnx-installer-macos

It lists your external disks, formats the SD card as FAT32, downloads the latest CNX Pack and extracts everything. No dependencies (uses system Python), works on macOS 10.15+. First launch: right-click -> Open (unsigned app). All firmware credit goes to the original project: https://github.com/CostelaCNX/CNX
