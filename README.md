# xlx_oled — XLX Reflector OLED Monitor

**PP5PK** · [pp5pk.net](https://pp5pk.net)

Monitor em tempo real para reflectores XLX, exibido em um display OLED 128×64 acoplado ao **NanoPi NEO2** via acessório **NanoHat OLED**. O script lê o arquivo de log do XLXD diretamente, sem dependências externas de rede, e exibe conexões ativas, atividade recente e informações do sistema — tudo controlado pelos três botões físicos do NanoHat.

---

> **Real-time monitor for XLX reflectors**, displayed on a 128×64 OLED attached to the **NanoPi NEO2** via the **NanoHat OLED** accessory. The script reads the XLXD log file directly — no network dependencies — and shows active connections, recent activity and system info, all controlled by the NanoHat's three physical buttons.

---

## Hardware

| Item | Detalhe / Detail |
|------|-----------------|
| SBC | NanoPi NEO2 (Allwinner H5, Cortex-A53 64-bit) |
| Acessório / Accessory | NanoHat OLED — FriendlyElec |
| Display | SSD1306, 128×64 px, I2C (`/dev/i2c-0`, endereço `0x3C`) |
| Botão K1 / Button K1 | GPIO 0 |
| Botão K2 / Button K2 | GPIO 2 |
| Botão K3 / Button K3 | GPIO 3 |
| OS testado / Tested OS | Armbian (Debian Trixie, kernel 6.6 LTS) |

---

## Hardware Referência / Hardware Reference

### NanoHat OLED — FriendlyElec

> Documentação oficial / Official documentation: [wiki.friendlyelec.com/wiki/index.php/NanoHat_OLED](https://wiki.friendlyelec.com/wiki/index.php/NanoHat_OLED)

| Especificação / Specification | Detalhe / Detail |
|-------------------------------|-----------------|
| Display | OLED monocromático / Monochrome OLED, 0.96" |
| Resolução / Resolution | 128 × 64 px |
| Interface | I2C |
| Dimensões PCB / PCB dimensions | 40 × 40 mm |
| Botões / Buttons | 3 botões programáveis / 3 programmable buttons |
| Conector de áudio / Audio connector | P2 3,5mm (entrada + saída / input + output) |
| Conector USB | USB Type-A |
| Compatibilidade / Compatibility | NanoPi NEO, NEO2, NEO Air, NEO Plus2 |

#### Mapeamento de pinos / Pin mapping (GPIO1 — Header 24 pinos / 24-pin header)

| Pino físico / Physical pin | Nome / Name | GPIO Linux |
|---------------------------|-------------|-----------|
| 11 | K1 | 0 |
| 13 | K2 | 2 |
| 15 | K3 | 3 |
| 3 | I2C0_SDA | — |
| 5 | I2C0_SCL | — |

> O conector de 12 pinos do NanoHat só tem GND e 5V conectados — os demais pinos estão abertos. O display OLED e os botões usam exclusivamente o header de 24 pinos (GPIO1).
>
> The NanoHat's 12-pin connector only has GND and 5V connected — the remaining pins are open. The OLED display and buttons use exclusively the 24-pin header (GPIO1).

---

## Telas / Pages

O display alterna entre três telas navegadas pelo botão **K1**.

The display cycles through three pages navigated by button **K1**.

### Tela 0 — Conexões Ativas / Active Connections

Exibe em tempo real todos os nós conectados ao reflector, com callsign, sufixo, módulo e protocolo. Suporta scroll para até 10+ conexões simultâneas.

Shows all nodes currently linked to the reflector in real time, with callsign, suffix, module and protocol. Supports scrolling for 10+ simultaneous connections.

```
CONEXOES ATIVAS [3]
──────────────────── ┐
PP5PK-B    [D] DCS   │
PU6AXE     [C] DCS   │ scroll
ECHO       [E] XLX   │
──────────────────── ┘
K1= Pag.  K2= ↓  K3= ↑
```

**Protocolos reconhecidos / Recognized protocols:** DCS, D+ (DPlus), DX (DExtra), DMR (DMRMmdvm), YSF, XLX, M17, NXD (NXDN), P25.

### Tela 1 — Atividade Recente / Recent Activity

Histórico das últimas 10 transmissões detectadas no log (`Opening stream`), com horário, callsign completo e módulo. Mais recente no topo, com scroll para navegar o histórico.

History of the last 10 transmissions detected in the log (`Opening stream`), with time, full callsign and module. Most recent at the top, with scrollable history.

```
ATIV. RECENTE [5]
────────────────────
21:00 PP5PK-A   [D]
20:55 PY2OMB-B  [D]
20:48 PP5PK-A   [D]
────────────────────
K1= Pag.  K2= ↓  K3= ↑
```

### Tela 2 — Sistema / System

Informações do servidor: IP, uptime, temperatura da CPU e horário local. O indicador `SCR:ON/OFF` mostra o estado do auto-scroll alinhado à direita na linha da temperatura.

Server information: IP, uptime, CPU temperature and local time. The `SCR:ON/OFF` indicator shows the auto-scroll state, right-aligned on the temperature line.

```
SISTEMA  |  XLXBRA
────────────────────
IP: 192.168.1.10
UP: 5h23m - 21:00 GMT-3
TEMP: 48°C      SCR:ON
────────────────────
K1= Prox.  K2= Menu
```

Pressionar **K2** nesta tela abre o menu de ações.

Pressing **K2** on this page opens the actions menu.

### Menu de Ações / Actions Menu

Menu com scroll, 3 opções visíveis por vez, navegado por **K2** e confirmado por **K3**. **K1** fecha o menu sem executar nada.

Scrollable menu, 3 options visible at a time, navigated by **K2** and confirmed by **K3**. **K1** closes the menu without executing anything.

```
⚙ ACOES
────────────────────
▶ Reiniciar
  Desligar
  Auto-scroll: ON
────────────────────
K2= Prox.  K3= Confirma
```

| Opção / Option | Ação / Action |
|----------------|--------------|
| Reiniciar | `shutdown -r now` |
| Desligar | `shutdown -h now` |
| Auto-scroll: ON/OFF | Alterna o auto-scroll / Toggles auto-scroll |
| Cancelar | Fecha o menu / Closes the menu |

---

## Botões / Buttons

| Botão / Button | Fora do menu / Outside menu | No menu / In menu |
|---|---|---|
| **K1** | Próxima tela / Next page | Fecha o menu / Close menu |
| **K2** | Scroll ↓ (telas 0 e 1) / Abre menu (tela 2) | Próxima opção / Next option |
| **K3** | Scroll ↑ (telas 0 e 1) | Confirma opção / Confirm option |

---

## Auto-scroll

Após **15 segundos** sem interação, o display começa a trocar de tela automaticamente a cada **10 segundos**, funcionando como painel de monitoramento passivo. Qualquer botão pressionado reinicia o contador de inatividade. O auto-scroll é suspenso automaticamente quando o menu de ações está aberto. Pode ser desativado permanentemente pelo menu da tela de sistema.

After **15 seconds** of inactivity, the display starts cycling pages automatically every **10 seconds**, functioning as a passive monitoring panel. Any button press resets the idle counter. Auto-scroll is automatically suspended when the actions menu is open. It can be permanently disabled via the system page menu.

Os tempos são configuráveis na seção `CONFIG` do script:

The timings are configurable in the `CONFIG` section of the script:

```python
AUTOSCROLL_IDLE     = 15   # segundos de inatividade / seconds of inactivity
AUTOSCROLL_INTERVAL = 10   # segundos entre trocas / seconds between page changes
```

---

## Dependências / Dependencies

### 1. Habilitar I2C no Armbian / Enable I2C on Armbian

Edite o arquivo de configuração de boot:

Edit the boot configuration file:

```bash
sudo nano /boot/armbianEnv.txt
```

Localize a linha `overlays=` e certifique-se de que `analog-codec` e `i2c0` estão presentes:

Locate the `overlays=` line and make sure `analog-codec` and `i2c0` are present:

```
overlays=analog-codec i2c0 usbhost1 usbhost2
```

```bash
sudo reboot
```

Após o reboot, confirme que o barramento I2C está disponível e o display é detectado:

After reboot, confirm the I2C bus is available and the display is detected:

```bash
ls /dev/i2c-0
sudo i2cdetect -y 0   # deve mostrar 3c / should show 3c
```

### 2. Pacotes do sistema / System packages

```bash
sudo apt install python3-pip python3-pil i2c-tools fonts-dejavu-core fonts-freefont-ttf -y
```

### 3. Biblioteca Python / Python library

```bash
sudo pip3 install luma.oled --break-system-packages
```

### 4. Permissão I2C para o usuário / I2C permission for the user

```bash
sudo usermod -aG i2c $USER
```

> Faça logout e login novamente para que a alteração de grupo tenha efeito, ou use `sudo` ao executar o script manualmente pela primeira vez.
>
> Log out and back in for the group change to take effect, or use `sudo` when running the script manually for the first time.

---

## Instalação / Installation

```bash
# 1. Clonar o repositório / Clone the repository
git clone https://github.com/PP5PK/xlx_oled.git
cd xlx_oled

# 2. Copiar o script / Copy the script
sudo cp xlx_oled.py /opt/xlx_oled.py

# 3. Editar as configurações / Edit configuration
sudo nano /opt/xlx_oled.py
```

Ajuste as variáveis na seção `CONFIG` conforme o seu ambiente:

Adjust the variables in the `CONFIG` section to match your environment:

```python
XLX_LOG_FILE    = "/var/log/xlx.log"   # caminho do log do XLXD / XLXD log path
MY_CALLSIGN     = "PP5PK"              # seu indicativo / your callsign
REFLECTOR_NAME  = "XLXBRA"            # nome do reflector / reflector name
```

```bash
# 4. Testar manualmente / Test manually
sudo python3 /opt/xlx_oled.py

# 5. Instalar como serviço / Install as service
sudo cp xlx-oled.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xlx-oled
sudo systemctl start xlx-oled

# 6. Verificar / Verify
sudo systemctl status xlx-oled
journalctl -u xlx-oled -f
```

---

## Serviço systemd / systemd Service

Arquivo `xlx-oled.service`:

```ini
[Unit]
Description=XLX Reflector OLED Monitor (PP5PK)
After=network.target xlxd.service
Wants=xlxd.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/xlx_oled.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SupplementaryGroups=i2c gpio

[Install]
WantedBy=multi-user.target
```

---

## Configuração do XLXD / XLXD Configuration

O script lê o log gerado automaticamente pelo XLXD. Verifique se o caminho do log está correto na variável `XLX_LOG_FILE`. O arquivo padrão é `/var/log/xlx.log`.

The script reads the log automatically generated by XLXD. Verify that the log path is correct in the `XLX_LOG_FILE` variable. The default file is `/var/log/xlx.log`.

O parser reconhece as seguintes entradas do log:

The parser recognizes the following log entries:

```
# Conexão / Connection
New client PP5PK   B at 172.23.127.1 added with protocol DCS on module D

# Desconexão / Disconnection
Client PP5PK   B at 172.23.127.1 removed with protocol DCS on module D

# Transmissão / Transmission
Opening stream on module D for client PP5PK   A with sid 56507
```

---

## Arquitetura / Architecture

O script é um daemon Python puro, sem dependência do software original da FriendlyElec (BakeBit ou binário C). Utiliza quatro threads independentes:

The script is a pure Python daemon, with no dependency on FriendlyElec's original software (BakeBit or C binary). It uses four independent threads:

| Thread | Função / Function |
|--------|------------------|
| `xlx_log_reader` | Lê o log XLXD incrementalmente em tempo real / Reads the XLXD log incrementally in real time |
| `button_thread` | Polling dos GPIOs a 50ms com debounce / GPIO polling at 50ms with debounce |
| `refresh_timer` | Dispara refresh do display a cada 5s / Triggers display refresh every 5s |
| `autoscroll_thread` | Gerencia o ciclo automático de telas / Manages the automatic page cycle |

O acesso aos GPIOs é feito via **sysfs** (`/sys/class/gpio`), sem dependência de bibliotecas como RPi.GPIO ou libgpiod, garantindo compatibilidade com o kernel mainline do Armbian.

GPIO access is done via **sysfs** (`/sys/class/gpio`), with no dependency on libraries like RPi.GPIO or libgpiod, ensuring compatibility with Armbian's mainline kernel.

---

## Projetos Relacionados / Related Projects

- [XLX_Dark_Dashboard](https://github.com/PP5PK/XLX_Dark_Dashboard) — Dashboard web com tema escuro para reflectores XLX / Dark theme web dashboard for XLX reflectors
- [monitor_XLX](https://github.com/PP5PK/monitor_XLX) — Daemon Bash para notificações Telegram de eventos XLX / Bash daemon for XLX event Telegram notifications

---

## Licença / License

GPL-3.0 — veja o arquivo [LICENSE](LICENSE).

---

73 de / 73 de **PP5PK** · Mafra, Santa Catarina, Brasil 🇧🇷
