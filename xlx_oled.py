#!/usr/bin/env python3
# =============================================================================
#  xlx_oled.py — Monitor XLX Reflector para NanoPi NEO2 + NanoHat OLED
#  PP5PK — https://pp5pk.net
#
#  Display 128x64 OLED (I2C, SSD1306) | 3 botões via GPIO sysfs
#
#  PÁGINAS (navegação com K1):
#    0 — Conexões ativas  : callsign + módulo (scroll K2/K3)
#    1 — Última atividade : últimas transmissões (scroll K2/K3)
#    2 — Sistema          : IP, uptime, CPU temp + menu de ações (K2)
#
#  BOTÕES:
#    K1 — Próxima página / fecha menu
#    K2 — Scroll ↓ (pág 0/1) / abre e navega menu (pág 2)
#    K3 — Scroll ↑ (pág 0/1) / confirma opção do menu (pág 2)
#
#  AUTO-SCROLL:
#    Após AUTOSCROLL_IDLE segundos sem tecla, troca página a cada
#    AUTOSCROLL_INTERVAL segundos. Toggle no menu da tela de sistema.
#
#  DEPENDÊNCIAS:
#    pip3 install luma.oled pillow
# =============================================================================

import os
import sys
import re
import time
import signal
import threading
import subprocess
from datetime import datetime
from collections import OrderedDict

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
#  CONFIG
# =============================================================================
OLED_I2C_PORT      = 0
OLED_I2C_ADDRESS   = 0x3C

GPIO_K1 = 0          # Próxima página / fecha menu
GPIO_K2 = 2          # Scroll ↓ / abre e navega menu
GPIO_K3 = 3          # Scroll ↑ / confirma menu

XLX_LOG_FILE       = "/var/log/xlx.log"
MY_CALLSIGN        = "PP5PK"
REFLECTOR_NAME     = "XLXBRA"

REFRESH_INTERVAL   = 5    # segundos entre refreshes automáticos
DEBOUNCE_TIME      = 0.3
LINES_PER_PAGE     = 3    # linhas visíveis nas páginas de lista
AUTOSCROLL_IDLE    = 15   # segundos de inatividade antes de ativar scroll
AUTOSCROLL_INTERVAL= 10   # segundos entre trocas de página no auto-scroll
# =============================================================================

# --- Regex -------------------------------------------------------------------
RE_CONNECT = re.compile(
    r'New client\s+(\S+)\s*(\S?)\s+at\s+\S+\s+added with protocol\s+(\S+?)'
    r'(?:\s+on module\s+([A-Z]))?$'
)
RE_DISCONNECT = re.compile(
    r'Client\s+(\S+)\s*(\S?)\s+at\s+\S+\s+removed with protocol\s+(\S+?)'
    r'(?:\s+on module\s+([A-Z]))?$'
)
RE_TX_OPEN = re.compile(
    r'(\d+ \w+,\s+\d+:\d+:\d+):\s+Opening stream on module\s+([A-Z])\s+for client\s+(\S+)\s*(\S?)\s+with'
)
RE_TX_CLOSE = re.compile(
    r'Closing stream on module\s+([A-Z])'
)

# --- Estado global -----------------------------------------------------------
connected        = OrderedDict()
last_tx          = []
connected_lock   = threading.Lock()
tx_lock          = threading.Lock()

current_page     = 0
PAGE_COUNT       = 3
scroll_offset    = 0
tx_scroll_offset = 0

sys_menu_active  = False
sys_menu_sel     = 0
SYS_MENU_OPTS    = ["Reiniciar", "Desligar", "Auto-scroll: ON", "Cancelar"]

autoscroll_on    = True
last_key_time    = time.time()

page_lock        = threading.Lock()
display_event    = threading.Event()
FONTS            = {}

# =============================================================================
#  GPIO sysfs
# =============================================================================

def gpio_export(gpio):
    path = f"/sys/class/gpio/gpio{gpio}"
    if not os.path.exists(path):
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(gpio))
            time.sleep(0.1)
        except Exception:
            pass

def gpio_set_direction(gpio, direction="in"):
    try:
        with open(f"/sys/class/gpio/gpio{gpio}/direction", "w") as f:
            f.write(direction)
    except Exception:
        pass

def gpio_unexport(gpio):
    try:
        with open("/sys/class/gpio/unexport", "w") as f:
            f.write(str(gpio))
    except Exception:
        pass

def gpio_read(gpio):
    with open(f"/sys/class/gpio/gpio{gpio}/value", "r") as f:
        return f.read().strip()

def setup_gpios():
    for gpio in (GPIO_K1, GPIO_K2, GPIO_K3):
        gpio_export(gpio)
        gpio_set_direction(gpio, "in")

def cleanup_gpios():
    for gpio in (GPIO_K1, GPIO_K2, GPIO_K3):
        gpio_unexport(gpio)

# =============================================================================
#  Botões
# =============================================================================
_last_press = {GPIO_K1: 0.0, GPIO_K2: 0.0, GPIO_K3: 0.0}

def button_thread():
    prev = {GPIO_K1: "0", GPIO_K2: "0", GPIO_K3: "0"}
    while True:
        for gpio in (GPIO_K1, GPIO_K2, GPIO_K3):
            try:
                val = gpio_read(gpio)
                now = time.time()
                if val == "1" and prev[gpio] == "0":
                    if now - _last_press[gpio] > DEBOUNCE_TIME:
                        _last_press[gpio] = now
                        if   gpio == GPIO_K1: on_k1()
                        elif gpio == GPIO_K2: on_k2()
                        elif gpio == GPIO_K3: on_k3()
                prev[gpio] = val
            except Exception:
                pass
        time.sleep(0.05)

def _reset_idle():
    global last_key_time
    last_key_time = time.time()

def on_k1():
    global current_page, scroll_offset, tx_scroll_offset, sys_menu_active, sys_menu_sel
    _reset_idle()
    if sys_menu_active:
        sys_menu_active = False
        sys_menu_sel    = 0
    else:
        with page_lock:
            current_page     = (current_page + 1) % PAGE_COUNT
            scroll_offset    = 0
            tx_scroll_offset = 0
    display_event.set()

def on_k2():
    global scroll_offset, tx_scroll_offset, sys_menu_active, sys_menu_sel
    _reset_idle()
    with page_lock:
        page = current_page
    if page == 0:
        with connected_lock:
            total = len(connected)
        max_scroll = max(0, total - LINES_PER_PAGE)
        scroll_offset = min(scroll_offset + 1, max_scroll)
    elif page == 1:
        with tx_lock:
            total = len(last_tx)
        max_scroll = max(0, total - LINES_PER_PAGE)
        tx_scroll_offset = min(tx_scroll_offset + 1, max_scroll)
    elif page == 2:
        if sys_menu_active:
            sys_menu_sel = (sys_menu_sel + 1) % len(SYS_MENU_OPTS)
        else:
            sys_menu_active = True
            sys_menu_sel    = 0
    display_event.set()

def on_k3():
    global scroll_offset, tx_scroll_offset
    _reset_idle()
    with page_lock:
        page = current_page
    if page == 0:
        scroll_offset = max(0, scroll_offset - 1)
    elif page == 1:
        tx_scroll_offset = max(0, tx_scroll_offset - 1)
    elif page == 2:
        if sys_menu_active:
            _execute_sys_menu(sys_menu_sel)
    display_event.set()

def _execute_sys_menu(sel):
    global sys_menu_active, sys_menu_sel, autoscroll_on
    sys_menu_active = False
    sys_menu_sel    = 0
    if sel == 0:
        subprocess.Popen(["sudo", "shutdown", "-r", "now"])
    elif sel == 1:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    elif sel == 2:
        autoscroll_on = not autoscroll_on
        SYS_MENU_OPTS[2] = f"Auto-scroll: {'ON' if autoscroll_on else 'OFF'}"
    # sel == 3: Cancelar — não faz nada

# =============================================================================
#  Leitor do log XLX
# =============================================================================

def _parse_line(line):
    global last_tx

    m = RE_CONNECT.search(line)
    if m:
        call, suffix, proto, module = m.groups()
        call   = call.strip()
        suffix = suffix.strip() if suffix else ""
        key    = f"{call}-{suffix}" if suffix else call
        mod    = module.strip() if module else "?"
        proto_short = {
            "DCS": "DCS", "DPlus": "D+", "DExtra": "DX",
            "DMRMmdvm": "DMR", "YSF": "YSF", "XLX": "XLX",
            "M17": "M17", "NXDN": "NXD", "P25": "P25",
        }.get(proto, proto[:3])
        with connected_lock:
            connected[key] = {
                "call": call, "suffix": suffix,
                "module": mod, "proto": proto_short
            }
        display_event.set()
        return

    m = RE_DISCONNECT.search(line)
    if m:
        call, suffix, proto, module = m.groups()
        call   = call.strip()
        suffix = suffix.strip() if suffix else ""
        key    = f"{call}-{suffix}" if suffix else call
        with connected_lock:
            connected.pop(key, None)
        display_event.set()
        return

    m = RE_TX_OPEN.search(line)
    if m:
        ts, mod, call, suffix = m.groups()
        hora   = ts.split(",")[1].strip()[:5]
        call   = call.strip()
        suffix = suffix.strip() if suffix else ""
        label  = f"{call}-{suffix}" if suffix else call
        entry  = {"time": hora, "call": label, "module": mod}
        with tx_lock:
            last_tx.append(entry)
            if len(last_tx) > 10:
                last_tx.pop(0)
        display_event.set()

def xlx_log_reader():
    file_pos = 0
    try:
        with open(XLX_LOG_FILE, "r", errors="replace") as f:
            for line in f:
                _parse_line(line.strip())
            file_pos = f.tell()
    except Exception:
        pass

    while True:
        try:
            with open(XLX_LOG_FILE, "r", errors="replace") as f:
                f.seek(0, 2)
                new_end = f.tell()
                if new_end < file_pos:
                    file_pos = 0
                f.seek(file_pos)
                new_data = f.read()
                if new_data:
                    file_pos = f.tell()
                    for line in new_data.splitlines():
                        _parse_line(line.strip())
        except Exception:
            pass
        time.sleep(2)

# =============================================================================
#  Informações do sistema
# =============================================================================

def get_ip():
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "scope", "global"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return "sem IP"

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            secs = float(f.read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h{m:02d}m"
    except Exception:
        return "?"

def get_cpu_temp():
    for p in ["/sys/class/thermal/thermal_zone0/temp"]:
        try:
            with open(p, "r") as f:
                return f"{int(f.read().strip()) // 1000}°C"
        except Exception:
            pass
    return "?"

# =============================================================================
#  Fontes
# =============================================================================

def load_fonts():
    try:
        for name in ["DejaVuSansMono", "FreeMono"]:
            for path in [
                f"/usr/share/fonts/truetype/dejavu/{name}.ttf",
                f"/usr/share/fonts/truetype/freefont/{name}.ttf",
            ]:
                if os.path.exists(path):
                    return {
                        "big":    ImageFont.truetype(path, 14),
                        "medium": ImageFont.truetype(path, 11),
                        "small":  ImageFont.truetype(path, 9),
                    }
    except Exception:
        pass
    d = ImageFont.load_default()
    return {"big": d, "medium": d, "small": d}

# =============================================================================
#  Renderização
# =============================================================================
WIDTH, HEIGHT = 128, 64

def _new_canvas():
    img  = Image.new("1", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(img)
    return img, draw

def _header(draw, title):
    draw.text((0, 0), title, font=FONTS["medium"], fill=1)
    draw.line([(0, 12), (WIDTH, 12)], fill=1)

def _footer(draw, text):
    draw.line([(0, 51), (WIDTH, 51)], fill=1)
    draw.text((0, 53), text, font=FONTS["small"], fill=1)

def render_connected():
    img, draw = _new_canvas()

    with connected_lock:
        items = list(connected.values())
        total = len(items)

    _header(draw, f"CONEXOES ATIVAS [{total}]")

    if total == 0:
        draw.text((10, 26), "Nenhuma conexao", font=FONTS["small"], fill=1)
    else:
        start = scroll_offset
        end   = min(start + LINES_PER_PAGE, total)
        y = 14
        for item in items[start:end]:
            call   = item["call"][:8]
            suffix = f"-{item['suffix']}" if item["suffix"] else "  "
            mod    = item["module"]
            proto  = item["proto"][:3]
            line   = f"{call+suffix:<11}[{mod}]{proto:>3}"
            draw.text((0, y), line, font=FONTS["small"], fill=1)
            y += 12

        if total > LINES_PER_PAGE:
            pct = int((scroll_offset / max(1, total - LINES_PER_PAGE)) * 36)
            draw.rectangle([(125, 14), (127, 50)], outline=1)
            draw.rectangle([(125, 14 + pct), (127, 14 + pct + 10)], fill=1)

    hora = datetime.now().strftime("%H:%M")
    _footer(draw, f"K1= Pag.  K2= ↓  K3= ↑")
    return img

def render_last_tx():
    img, draw = _new_canvas()

    with tx_lock:
        entries = list(last_tx)
        total   = len(entries)

    _header(draw, f"ATIV. RECENTE [{total}]")

    if total == 0:
        draw.text((5, 26), "Sem atividade", font=FONTS["small"], fill=1)
    else:
        reversed_entries = entries[::-1]
        start = tx_scroll_offset
        end   = min(start + LINES_PER_PAGE, total)
        y = 14
        for e in reversed_entries[start:end]:
            call_s = e["call"][:9]
            line   = f"{e['time']} {call_s:<9}[{e['module']}]"
            draw.text((0, y), line, font=FONTS["small"], fill=1)
            y += 12

        if total > LINES_PER_PAGE:
            pct = int((tx_scroll_offset / max(1, total - LINES_PER_PAGE)) * 36)
            draw.rectangle([(125, 14), (127, 50)], outline=1)
            draw.rectangle([(125, 14 + pct), (127, 14 + pct + 10)], fill=1)

    hora = datetime.now().strftime("%H:%M")
    _footer(draw, f"K1= Pag.  K2= ↓  K3= ↑")
    return img

def render_system():
    img, draw = _new_canvas()

    if sys_menu_active:
        _header(draw, "⚙ ACOES")
        total_opts  = len(SYS_MENU_OPTS)
        visible     = 3
        # scroll: garante que a opção selecionada esteja visível
        menu_start  = max(0, min(sys_menu_sel - visible + 1,
                                 total_opts - visible))
        for idx, i in enumerate(range(menu_start, menu_start + visible)):
            if i >= total_opts:
                break
            opt = SYS_MENU_OPTS[i]
            y   = 14 + idx * 12
            if i == sys_menu_sel:
                draw.rectangle([(0, y - 1), (WIDTH - 1, y + 10)], fill=1)
                draw.text((4, y), f"▶ {opt}", font=FONTS["small"], fill=0)
            else:
                draw.text((4, y), f"  {opt}", font=FONTS["small"], fill=1)
        # barra de scroll lateral
        if total_opts > visible:
            pct = int((menu_start / max(1, total_opts - visible)) * 36)
            draw.rectangle([(125, 14), (127, 50)], outline=1)
            draw.rectangle([(125, 14 + pct), (127, 14 + pct + 10)], fill=1)
        _footer(draw, "K2= Prox.  K3= Confirma")
    else:
        ip   = get_ip()
        upt  = get_uptime()
        temp = get_cpu_temp()
        hora = datetime.now().strftime("%H:%M")
        _header(draw, f"SISTEMA  |  {REFLECTOR_NAME}")
        draw.text((0, 14), f"IP: {ip}",            font=FONTS["small"], fill=1)
        draw.text((0, 26), f"UP: {upt} - {hora} GMT-3",  font=FONTS["small"], fill=1)
        asc = "SCR:ON" if autoscroll_on else "SCR:OFF"
        draw.text((0,   38), f"TEMP: {temp}",  font=FONTS["small"], fill=1)
        draw.text((WIDTH - 1, 38), asc, font=FONTS["small"], fill=1, anchor="ra")
        _footer(draw, "K1= Prox.  K2= Menu")
    return img

def render_boot():
    img, draw = _new_canvas()
    draw.text((15, 8),  REFLECTOR_NAME,  font=FONTS["big"],    fill=1)
    draw.text((20, 26), MY_CALLSIGN,     font=FONTS["medium"], fill=1)
    draw.text((5,  40), "Iniciando...",  font=FONTS["small"],  fill=1)
    draw.line([(0, 51), (WIDTH, 51)],    fill=1)
    draw.text((0,  52), "pp5pk.net",     font=FONTS["small"],  fill=1)
    return img

# =============================================================================
#  Loop de display
# =============================================================================

def autoscroll_thread():
    """Thread: avança página automaticamente após inatividade."""
    global current_page, scroll_offset, tx_scroll_offset
    while True:
        time.sleep(1)
        if not autoscroll_on or sys_menu_active:
            continue
        idle = time.time() - last_key_time
        if idle < AUTOSCROLL_IDLE:
            continue
        cycle = idle - AUTOSCROLL_IDLE
        if cycle % AUTOSCROLL_INTERVAL < 1:
            with page_lock:
                current_page     = (current_page + 1) % PAGE_COUNT
                scroll_offset    = 0
                tx_scroll_offset = 0
            display_event.set()

def refresh_timer():
    """Thread: dispara display_event a cada REFRESH_INTERVAL segundos."""
    while True:
        time.sleep(REFRESH_INTERVAL)
        display_event.set()

def display_loop(device):
    while True:
        display_event.wait()
        display_event.clear()

        with page_lock:
            page = current_page

        if   page == 0: img = render_connected()
        elif page == 1: img = render_last_tx()
        else:           img = render_system()

        device.display(img)

# =============================================================================
#  Main
# =============================================================================

def signal_handler(sig, frame):
    cleanup_gpios()
    sys.exit(0)

def main():
    global FONTS

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    serial = i2c(port=OLED_I2C_PORT, address=OLED_I2C_ADDRESS)
    device = ssd1306(serial)

    FONTS = load_fonts()

    device.display(render_boot())
    time.sleep(2)

    setup_gpios()

    threading.Thread(target=xlx_log_reader,   daemon=True).start()
    threading.Thread(target=button_thread,     daemon=True).start()
    threading.Thread(target=refresh_timer,     daemon=True).start()
    threading.Thread(target=autoscroll_thread, daemon=True).start()

    display_event.set()
    display_loop(device)

if __name__ == "__main__":
    main()
