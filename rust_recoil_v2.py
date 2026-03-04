"""
Rust Recoil Control v2 - Arduino HID
Faithfully replicates script.lua logic via Arduino serial.

Requires: pyserial (pip install pyserial)
Windows only (uses ctypes for input detection).

The Arduino Leonardo acts as USB HID mouse passthrough.
This script ONLY sends recoil compensation moves via serial.
The real mouse clicks pass through the USB Host Shield automatically.
"""

import serial
import serial.tools.list_ports
import time
import sys
import ctypes
import math
import os
import re

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

BAUD_RATE = 115200

# Path to Rust client.cfg (auto-detect sensitivity & FOV)
RUST_CFG_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Rust\cfg\client.cfg"

# Fallback values used only if client.cfg cannot be read
SENSITIVITY_FALLBACK = 0.4
FOV_FALLBACK = 78
ADS_SENSITIVITY_FALLBACK = 0.8333  # Lua script was calibrated for this value

# The constant the Lua offsets were calibrated against
_LUA_EXPECTED_ADS = 0.8333


def load_rust_config(cfg_path=None):
    """Load sensitivity, ads_sensitivity and FOV from Rust's client.cfg."""
    if cfg_path is None:
        cfg_path = RUST_CFG_PATH
    config = {"sensitivity": None, "fov": None, "ads_sensitivity": None}
    if not os.path.isfile(cfg_path):
        return config
    try:
        with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                m = re.match(r'^input\.sensitivity\s+"([^"]+)"', line)
                if m:
                    config["sensitivity"] = float(m.group(1))
                    continue
                m = re.match(r'^input\.ads_sensitivity\s+"([^"]+)"', line)
                if m:
                    config["ads_sensitivity"] = float(m.group(1))
                    continue
                m = re.match(r'^graphics\.fov\s+"([^"]+)"', line)
                if m:
                    config["fov"] = float(m.group(1))
    except (OSError, ValueError):
        pass
    return config


_rust_cfg = load_rust_config()
SENSITIVITY = _rust_cfg["sensitivity"] if _rust_cfg["sensitivity"] is not None else SENSITIVITY_FALLBACK
FOV = _rust_cfg["fov"] if _rust_cfg["fov"] is not None else FOV_FALLBACK
ADS_SENSITIVITY = _rust_cfg["ads_sensitivity"] if _rust_cfg["ads_sensitivity"] is not None else ADS_SENSITIVITY_FALLBACK
_CFG_SOURCE = "client.cfg" if _rust_cfg["sensitivity"] is not None else "fallback"

# Gun bindings: set to mouse button number (4=X1/Back, 5=X2/Forward)
# or None to disable. Same as Logitech G Hub button numbers.
# Profile 1 (_1)
AK47_1_BIND = None
LR300_1_BIND = None
MP5A4_1_BIND = None
THOMPSON_1_BIND = None
SMG_1_BIND = None
HMLMG_1_BIND = None
M249_1_BIND = None
SAR_1_BIND = None
M39_1_BIND = None
SAP_1_BIND = None
M92_1_BIND = None
PYTHON_1_BIND = None
REVOLVER_1_BIND = None

# Profile 2 (_2)
AK47_2_BIND = 4
LR300_2_BIND = None
MP5A4_2_BIND = None
THOMPSON_2_BIND = 5
SMG_2_BIND = None
HMLMG_2_BIND = None
M249_2_BIND = None
SAR_2_BIND = None
M39_2_BIND = None
SAP_2_BIND = None
M92_2_BIND = None
PYTHON_2_BIND = None

# ─── Attachments Profile 1 ─────────────────────────────────
AK47_1_HOLOSIGHT = False
AK47_1_X8_SCOPE = False
AK47_1_X16_SCOPE = False
AK47_1_HANDMADESIGHT = False
AK47_1_SILENCER = False
AK47_1_MUZZLEBOOST = False

LR300_1_HOLOSIGHT = False
LR300_1_X8_SCOPE = False
LR300_1_X16_SCOPE = False
LR300_1_HANDMADESIGHT = False
LR300_1_SILENCER = False
LR300_1_MUZZLEBOOST = False

MP5A4_1_HOLOSIGHT = False
MP5A4_1_X8_SCOPE = False
MP5A4_1_X16_SCOPE = False
MP5A4_1_HANDMADESIGHT = False
MP5A4_1_SILENCER = False
MP5A4_1_MUZZLEBOOST = False

THOMPSON_1_HOLOSIGHT = False
THOMPSON_1_X8_SCOPE = False
THOMPSON_1_X16_SCOPE = False
THOMPSON_1_HANDMADESIGHT = False
THOMPSON_1_SILENCER = False
THOMPSON_1_MUZZLEBOOST = False

SMG_1_HOLOSIGHT = False
SMG_1_X8_SCOPE = False
SMG_1_X16_SCOPE = False
SMG_1_HANDMADESIGHT = False
SMG_1_SILENCER = False
SMG_1_MUZZLEBOOST = False

HMLMG_1_HOLOSIGHT = False
HMLMG_1_X8_SCOPE = False
HMLMG_1_X16_SCOPE = False
HMLMG_1_HANDMADESIGHT = False
HMLMG_1_SILENCER = False

M249_1_HOLOSIGHT = False
M249_1_X8_SCOPE = False
M249_1_X16_SCOPE = False
M249_1_HANDMADESIGHT = False
M249_1_SILENCER = False

SAR_1_HOLOSIGHT = False
SAR_1_X8_SCOPE = False
SAR_1_X16_SCOPE = False
SAR_1_HANDMADESIGHT = False
SAR_1_SILENCER = False

M39_1_HOLOSIGHT = False
M39_1_X8_SCOPE = False
M39_1_X16_SCOPE = False
M39_1_HANDMADESIGHT = False
M39_1_SILENCER = False

SAP_1_HOLOSIGHT = False
SAP_1_X8_SCOPE = False
SAP_1_X16_SCOPE = False
SAP_1_HANDMADESIGHT = False
SAP_1_SILENCER = False

M92_1_HOLOSIGHT = False
M92_1_X8_SCOPE = False
M92_1_X16_SCOPE = False
M92_1_HANDMADESIGHT = False
M92_1_SILENCER = False

PYTHON_1_HOLOSIGHT = False
PYTHON_1_X8_SCOPE = False
PYTHON_1_X16_SCOPE = False
PYTHON_1_HANDMADESIGHT = False

REVOLVER_1_SILENCER = False

# ─── Attachments Profile 2 ─────────────────────────────────
AK47_2_HOLOSIGHT = False
AK47_2_X8_SCOPE = False
AK47_2_X16_SCOPE = False
AK47_2_HANDMADESIGHT = False
AK47_2_SILENCER = False
AK47_2_MUZZLEBOOST = False

LR300_2_HOLOSIGHT = False
LR300_2_X8_SCOPE = False
LR300_2_X16_SCOPE = False
LR300_2_HANDMADESIGHT = False
LR300_2_SILENCER = False
LR300_2_MUZZLEBOOST = False

MP5A4_2_HOLOSIGHT = False
MP5A4_2_X8_SCOPE = False
MP5A4_2_X16_SCOPE = False
MP5A4_2_HANDMADESIGHT = False
MP5A4_2_SILENCER = False
MP5A4_2_MUZZLEBOOST = False

THOMPSON_2_HOLOSIGHT = False
THOMPSON_2_X8_SCOPE = False
THOMPSON_2_X16_SCOPE = False
THOMPSON_2_HANDMADESIGHT = False
THOMPSON_2_SILENCER = False
THOMPSON_2_MUZZLEBOOST = False

SMG_2_HOLOSIGHT = False
SMG_2_X8_SCOPE = False
SMG_2_X16_SCOPE = False
SMG_2_HANDMADESIGHT = False
SMG_2_SILENCER = False
SMG_2_MUZZLEBOOST = False

HMLMG_2_HOLOSIGHT = False
HMLMG_2_X8_SCOPE = False
HMLMG_2_X16_SCOPE = False
HMLMG_2_HANDMADESIGHT = False
HMLMG_2_SILENCER = False

M249_2_HOLOSIGHT = False
M249_2_X8_SCOPE = False
M249_2_X16_SCOPE = False
M249_2_HANDMADESIGHT = False
M249_2_SILENCER = False

SAR_2_HOLOSIGHT = False
SAR_2_X8_SCOPE = False
SAR_2_X16_SCOPE = False
SAR_2_HANDMADESIGHT = False
SAR_2_SILENCER = False

M39_2_HOLOSIGHT = False
M39_2_X8_SCOPE = False
M39_2_X16_SCOPE = False
M39_2_HANDMADESIGHT = False
M39_2_SILENCER = False

SAP_2_HOLOSIGHT = False
SAP_2_X8_SCOPE = False
SAP_2_X16_SCOPE = False
SAP_2_HANDMADESIGHT = False
SAP_2_SILENCER = False

M92_2_HOLOSIGHT = False
M92_2_X8_SCOPE = False
M92_2_X16_SCOPE = False
M92_2_HANDMADESIGHT = False
M92_2_SILENCER = False

PYTHON_2_HOLOSIGHT = False
PYTHON_2_X8_SCOPE = False
PYTHON_2_X16_SCOPE = False
PYTHON_2_HANDMADESIGHT = False

# Door Unlocker (set to mouse button or None)
DOOR_UNLOCKER_BIND = None
KEY_CODE = 0  # 4-digit door code, e.g. 1234

# ═══════════════════════════════════════════════════════════════
# RECOIL DATA - Exact values from script.lua
# ═══════════════════════════════════════════════════════════════

RECOIL = {
    "AK47": {
        "offset_x": [0, 0.196287718722224, 0.365188622188568, 0.508115456226468,
                      0.626480966663358, 0.721697899326678, 0.795179000043864,
                      0.848337014642358, 0.882584688949584, 0.899334768792984,
                      0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9,
                      0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
        "offset_y": [-1.35]*30,
        "rpm": 133.3,
    },
    "LR300": {
        "offset_x": [0, 0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276, 0.017410668448276,
                      0.017410668448276, 0.017410668448276],
        "offset_y": [-1.16853173596552]*30,
        "rpm": 120,
    },
    "MP5A4": {
        "offset_x": [0.0]*30,
        "offset_y": [-0.64]*30,
        "rpm": 100,
    },
    "THOMPSON": {
        "offset_x": [-0.085809965, 0.006514516, 0.007734019, 0.048618872,
                      0.078056445, -0.066088665, 0.067429669, 0.02780332,
                      0.133849085, 0.025990565, -0.061993655, 0.019162548,
                      0.061810655, -0.092478981, 0.021123053, -0.08800972,
                      -0.201583254, -0.0398146, 0.003178508],
        "offset_y": [-0.510477526, -0.507449769, -0.51212903, -0.518510046,
                      -0.491714729, -0.495322988, -0.506388516, -0.474468436,
                      -0.47605394, -0.502083505, -0.498620747, -0.477474444,
                      -0.485339713, -0.496579241, -0.496766742, -0.52010755,
                      -0.49584349, -0.50812102, -0.485279713],
        "rpm": 129.87013,
    },
    "SMG": {
        "offset_x": [-0.085810521, 0.006513752, 0.007734002, 0.048618762,
                      0.07805627, -0.066088517, 0.067429517, 0.027803257,
                      0.133849533, 0.025989756, -0.061993515, 0.019163255,
                      0.061809765, -0.092478773, 0.021123005, -0.088008772,
                      -0.2015828, -0.03981451, 0.003178501, 0.010626753,
                      -0.007430252, 0.033057008, -0.032390258],
        "offset_y": [-0.510476378, -0.507447877, -0.512127878, -0.51850813,
                      -0.491712873, -0.495321874, -0.506387377, -0.474467369,
                      -0.476052869, -0.502083126, -0.498620375, -0.477473369,
                      -0.485338621, -0.496578124, -0.496765624, -0.52010563,
                      -0.495841624, -0.508119877, -0.485277871, -0.413580103,
                      -0.414059354, -0.433270608, -0.41218510],
        "rpm": 100,
    },
    "HMLMG": {
        "offset_x": [0, -0.536458333, -0.536458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333, -0.556458333, -0.556458333, -0.556458333,
                      -0.556458333],
        "offset_y": [-1.047375]*60,
        "rpm": 125,
    },
    "M249": {
        "offset_x": [0, 0.39375, 0.525] + [0.525]*97,
        "offset_y": [-0.81, -1.0800] + [-1.0800]*98,
        "rpm": 120,
    },
    "SAR": {
        "offset_x": [0]*16,
        "offset_y": [-0.8775]*16,
        "rpm": 174.927114,
    },
    "M39": {
        "offset_x": [0.5]*20,
        "offset_y": [-0.95]*20,
        "rpm": 174.927114,
    },
    "SAP": {
        "offset_x": [0]*10,
        "offset_y": [-0.6075]*10,
        "rpm": 174.927114,
    },
    "M92": {
        "offset_x": [0]*15,
        "offset_y": [-1.9]*15,
        "rpm": 150,
    },
    "PYTHON": {
        "offset_x": [0]*6,
        "offset_y": [-3.5]*6,
        "rpm": 150,
    },
    "REVOLVER": {
        "offset_x": [0]*8,
        "offset_y": [-1.1]*8,
        "rpm": 174.927114,
    },
}

# Per-gun base active time (AT) in ms
BASE_AT = {
    "AK47": 100, "LR300": 100, "MP5A4": 100, "THOMPSON": 100, "SMG": 100,
    "HMLMG": 125, "M249": 120,
    "SAR": 145, "M39": 75, "SAP": 140, "M92": 150, "PYTHON": 145, "REVOLVER": 145,
}

# Scope multiplier values per gun (holosight, x8, x16, handmade)
SCOPE_VALUES = {
    "AK47":     (1.2, 6.9,  13.5, 0.8),
    "LR300":    (1.2, 6.75, 13.5, 0.8),
    "MP5A4":    (1.2, 6.75, 13.5, 0.8),
    "THOMPSON": (1.5, 7.75, 15.5, 0.8),
    "SMG":      (1.5, 7.75, 15.5, 0.8),
    "HMLMG":    (1.2, 7.0,  13.5, 0.8),
    "M249":     (1.2, 7.0,  13.5, 0.8),
    "SAR":      (1.2, 6.75, 13.5, 0.8),
    "M39":      (1.5, 9.75, 13.5, 0.9),
    "SAP":      (1.5, 9.75, 13.5, 0.8),
    "M92":      (1.7, 9.75, 13.5, 0.8),
    "PYTHON":   (1.5, 9.75, 13.5, 0.8),
}

# Stand multipliers
STAND_MULT = 1.89
STAND_MULT_HMLMG = 2.0
STAND_MULT_M2 = 1.93

# Semi-auto guns (use pause key for rapid fire)
SEMI_AUTO_GUNS = {"SAR", "M39", "SAP", "M92", "PYTHON", "REVOLVER"}

# Guns that repeat last bullet after magazine empty
HAS_REPEAT = {"AK47", "LR300", "MP5A4", "SMG", "THOMPSON", "SAR", "SAP", "M92"}

# Guns with muzzle boost option
HAS_MUZZLE_BOOST = {"AK47", "LR300", "MP5A4", "THOMPSON", "SMG"}

# ═══════════════════════════════════════════════════════════════
# WINDOWS INPUT - ctypes for mouse/keyboard detection
# ═══════════════════════════════════════════════════════════════

user32 = ctypes.windll.user32
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06
VK_LCONTROL = 0xA2
VK_PAUSE = 0x13

BUTTON_TO_VK = {4: VK_XBUTTON1, 5: VK_XBUTTON2}

DEBUG = True  # Set to False to hide debug prints


def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")


def is_pressed(vk):
    return (user32.GetAsyncKeyState(vk) & 0x8000) != 0


def is_left_pressed():
    return is_pressed(VK_LBUTTON)


def is_right_pressed():
    return is_pressed(VK_RBUTTON)


def is_crouch():
    return is_pressed(VK_LCONTROL)


def press_key(vk):
    user32.keybd_event(vk, 0, 0, 0)


def release_key(vk):
    user32.keybd_event(vk, 0, 0x0002, 0)


# ═══════════════════════════════════════════════════════════════
# SERIAL COMMUNICATION
# ═══════════════════════════════════════════════════════════════

def find_arduino():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "BTHENUM" in (port.hwid or ""):
            continue
        try:
            s = serial.Serial(port.device, BAUD_RATE, timeout=1)
            s.close()
            return port.device
        except (serial.SerialException, OSError):
            continue
    return None


def send_move(ser, x, y):
    """Send mouse move via serial. Handles chunking for values > 127."""
    x = int(round(x))
    y = int(round(y))
    while x != 0 or y != 0:
        cx = max(-127, min(127, x))
        cy = max(-127, min(127, y))
        ser.write(f"m{cx},{cy}\n".encode())
        x -= cx
        y -= cy


# ═══════════════════════════════════════════════════════════════
# SMOOTHING - distributes movement over time (matches Lua)
# ═══════════════════════════════════════════════════════════════

def py_round(x):
    """Round half-up like Lua's math.floor(x+0.5)."""
    if x >= 0:
        return int(math.floor(x + 0.5))
    else:
        return int(math.ceil(x - 0.5))


def smoothing(ser, total_time_ms, total_x, total_y):
    """Distribute mouse movement exactly like Lua's Smoothing(a,b,c).
    a=total_time_ms steps, each step sleeps 1ms, distributes b=total_x and c=total_y."""
    if total_time_ms <= 0:
        return
    num_steps = max(1, int(total_time_ms))

    acc_x = 0
    acc_y = 0
    for i in range(1, num_steps + 1):
        target_x = py_round(i * total_x / num_steps)
        target_y = py_round(i * total_y / num_steps)
        dx = target_x - acc_x
        dy = target_y - acc_y
        acc_x = target_x
        acc_y = target_y
        if dx != 0 or dy != 0:
            send_move(ser, dx, dy)
        busy_sleep_ms(1)


def busy_sleep_ms(ms):
    """High-precision sleep matching Lua's sasd2441."""
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        pass


# ═══════════════════════════════════════════════════════════════
# PRE-COMPUTATION - compute screen-adjusted recoil values
# ═══════════════════════════════════════════════════════════════

def get_attachment_flags(gun, profile):
    """Read attachment config for a gun+profile from global variables."""
    p = profile
    g = gun
    prefix = f"{g}_{p}_"

    flags = {
        "holosight": False, "x8_scope": False, "x16_scope": False,
        "handmade_sight": False, "silencer": False, "muzzle_boost": False,
    }

    if gun == "REVOLVER":
        flags["silencer"] = globals().get(f"REVOLVER_1_SILENCER", False)
        return flags

    for key in flags:
        var_name = prefix + key.upper()
        flags[key] = globals().get(var_name, False)

    return flags


def compute_scope_barrel(gun, flags):
    """Compute combined scope and barrel multipliers."""
    scope = 1.0
    barrel = 1.0

    if gun == "REVOLVER":
        return scope, barrel

    sv = SCOPE_VALUES.get(gun)
    if sv:
        holo_v, x8_v, x16_v, hms_v = sv
        if flags["holosight"]:
            scope *= holo_v
        if flags["x8_scope"]:
            scope *= x8_v
        if flags["x16_scope"]:
            scope *= x16_v
        if flags["handmade_sight"]:
            scope *= hms_v

    # Silencer handling
    if flags["silencer"]:
        if gun in ("THOMPSON", "SMG"):
            # Special: only affects if holosight is also equipped
            if flags["holosight"]:
                barrel *= 0.9
            # else barrel stays 1.0
        else:
            barrel *= 1.0  # Silencer is always 1.0 for other guns

    return scope, barrel


def compute_timing(gun, flags):
    """Compute AT and ST per bullet."""
    base_at = BASE_AT[gun]
    rpm = RECOIL[gun]["rpm"]

    if gun in HAS_MUZZLE_BOOST and flags["muzzle_boost"]:
        mb_mult = 0.9
        at = base_at * mb_mult
        st = rpm * mb_mult - at
    elif gun in ("HMLMG", "M249"):
        at = base_at
        st = rpm - at
    else:
        at = base_at
        st = rpm - at

    return at, st


def precompute(gun, profile):
    """Pre-compute recoil table for a gun+profile (matches Lua N1/N2 computation)."""
    screen_mult = -0.03 * (SENSITIVITY * 3) * (FOV / 100)
    flags = get_attachment_flags(gun, profile)
    scope, barrel = compute_scope_barrel(gun, flags)
    at, st = compute_timing(gun, flags)

    data = RECOIL[gun]
    bullets = len(data["offset_y"])
    c_x = []
    c_y = []

    for i in range(bullets):
        ox = data["offset_x"][i]
        oy = data["offset_y"][i]
        if gun == "REVOLVER":
            cx = py_round(ox / screen_mult)
            cy = py_round(oy / screen_mult)
        else:
            cx = py_round((ox / screen_mult) * scope * barrel)
            cy = py_round((oy / screen_mult) * scope * barrel)
        c_x.append(cx)
        c_y.append(cy)

    return {
        "c_x": c_x,
        "c_y": c_y,
        "at": at,
        "st": st,
        "bullets": bullets,
        "flags": flags,
        "gun": gun,
        "profile": profile,
    }


# ═══════════════════════════════════════════════════════════════
# FIRING LOGIC - matches Lua MOVE_EVENT behavior per gun
# ═══════════════════════════════════════════════════════════════

def get_stand_mult(gun):
    """Get the stand multiplier for a gun."""
    if gun == "HMLMG":
        return STAND_MULT_HMLMG
    elif gun == "M249":
        return STAND_MULT_HMLMG  # M249 profile 1 uses HMLMG multiplier
    else:
        return STAND_MULT


def fire_auto_standard(ser, table):
    """Fire pattern for standard auto guns: AK47, LR300, MP5A4, THOMPSON, SMG."""
    gun = table["gun"]
    profile = table["profile"]
    flags = table["flags"]
    debug(f"Firing {gun} profile {profile} ({table['bullets']} bullets)")
    c_x = table["c_x"]
    c_y = table["c_y"]
    at = table["at"]
    st = table["st"]
    bullets = table["bullets"]

    has_mb = flags.get("muzzle_boost", False) and gun in HAS_MUZZLE_BOOST
    stand_m = STAND_MULT
    # AK47 uses extra 1.05 factor
    extra = 1.05 if gun == "AK47" else 1.0

    for bullet in range(bullets):
        if not is_right_pressed() or not is_left_pressed():
            return
        crouched = is_crouch()

        bx = c_x[bullet]
        by = c_y[bullet]

        if crouched:
            smoothing(ser, at, bx, by)
        else:
            if has_mb and (bullet + 1) > 17:
                # Muzzle boost after bullet 17
                if gun == "AK47":
                    smoothing(ser, at, bx * (-0.1), by * stand_m * extra)
                else:
                    smoothing(ser, at, bx, by * stand_m)
            else:
                smoothing(ser, at, bx * stand_m * extra, by * stand_m * extra)

        if st > 0:
            busy_sleep_ms(st)

    # Repeat last bullet until release
    if gun in HAS_REPEAT:
        last_x = c_x[-1]
        last_y = c_y[-1]
        while is_left_pressed() and is_right_pressed():
            crouched = is_crouch()
            if has_mb:
                if crouched:
                    smoothing(ser, at, last_x * 0.1, last_y)
                else:
                    smoothing(ser, at, last_x * stand_m * 0.1, last_y * stand_m)
            else:
                if crouched:
                    smoothing(ser, at, last_x, last_y)
                else:
                    smoothing(ser, at, last_x * stand_m, last_y * stand_m)
            if st > 0:
                busy_sleep_ms(st)


def fire_hmlmg(ser, table):
    """Fire pattern for HMLMG with special X-zeroing logic."""
    debug(f"Firing HMLMG ({table['bullets']} bullets)")
    flags = table["flags"]
    c_x = table["c_x"]
    c_y = table["c_y"]
    at = table["at"]
    st = table["st"]
    bullets = table["bullets"]
    has_x8 = flags.get("x8_scope", False)

    for bullet in range(bullets):
        if not is_right_pressed() or not is_left_pressed():
            return
        crouched = is_crouch()
        maincycle = bullet + 1  # 1-based like Lua

        bx = c_x[bullet]
        by = c_y[bullet]

        if crouched:
            if has_x8:
                x_cutoff = 31
            else:
                x_cutoff = 45
            if maincycle > x_cutoff:
                smoothing(ser, at, 0, by)
            else:
                smoothing(ser, at, bx, by)
        else:
            if has_x8:
                x_cutoff = 16
            else:
                x_cutoff = 23
            if maincycle > x_cutoff:
                smoothing(ser, at, 0, by * STAND_MULT_HMLMG)
            else:
                smoothing(ser, at, bx * STAND_MULT_HMLMG, by * STAND_MULT_HMLMG)

        if st > 0:
            busy_sleep_ms(st)
    # No repeat for HMLMG


def fire_m249(ser, table):
    """Fire pattern for M249."""
    debug(f"Firing M249 ({table['bullets']} bullets)")
    profile = table["profile"]
    c_x = table["c_x"]
    c_y = table["c_y"]
    at = table["at"]
    st = table["st"]
    bullets = table["bullets"]

    for bullet in range(bullets):
        if not is_right_pressed() or not is_left_pressed():
            return
        crouched = is_crouch()
        maincycle = bullet + 1

        bx = c_x[bullet]
        by = c_y[bullet]

        if crouched:
            smoothing(ser, at, bx, by)
        else:
            if profile == 1:
                # Profile 1: uses HMLMG multiplier, X-zeroing after bullet 25
                if maincycle > 25:
                    smoothing(ser, at, 0, by * STAND_MULT_HMLMG)
                else:
                    smoothing(ser, at, bx * STAND_MULT_HMLMG, by * STAND_MULT_HMLMG)
            else:
                # Profile 2: uses standard multiplier, no X-zeroing
                smoothing(ser, at, bx * STAND_MULT, by * STAND_MULT)

        if st > 0:
            busy_sleep_ms(st)
    # No repeat for M249


def fire_semi(ser, table):
    """Fire pattern for semi-auto guns: SAR, M39, SAP, M92, PYTHON, REVOLVER."""
    debug(f"Firing {table['gun']} semi-auto ({table['bullets']} bullets)")
    gun = table["gun"]
    c_x = table["c_x"]
    c_y = table["c_y"]
    at = table["at"]
    st = table["st"]
    bullets = table["bullets"]

    for bullet in range(bullets):
        if not is_right_pressed() or not is_left_pressed():
            return
        crouched = is_crouch()

        # Rapid fire: press pause key
        press_key(VK_PAUSE)
        busy_sleep_ms(10)
        release_key(VK_PAUSE)

        bx = c_x[bullet]
        by = c_y[bullet]

        if crouched:
            smoothing(ser, at, bx, by)
        else:
            smoothing(ser, at, bx * STAND_MULT, by * STAND_MULT)

        if st > 0:
            busy_sleep_ms(st)

    # Repeat for guns that have it (SAR, SAP, M92)
    if gun in HAS_REPEAT:
        last_x = c_x[-1]
        last_y = c_y[-1]
        while is_left_pressed() and is_right_pressed():
            crouched = is_crouch()
            if crouched:
                smoothing(ser, at, last_x, last_y)
            else:
                smoothing(ser, at, last_x * STAND_MULT, last_y * STAND_MULT)
            if st > 0:
                busy_sleep_ms(st)


def fire_gun(ser, table):
    """Dispatch to the correct firing pattern."""
    gun = table["gun"]

    if gun in SEMI_AUTO_GUNS:
        fire_semi(ser, table)
    elif gun == "HMLMG":
        fire_hmlmg(ser, table)
    elif gun == "M249":
        fire_m249(ser, table)
    else:
        fire_auto_standard(ser, table)


# ═══════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════

def build_binding_map():
    """Build mapping from (gun, profile) -> mouse button VK code."""
    bindings = {}
    gun_names = ["AK47", "LR300", "MP5A4", "THOMPSON", "SMG", "HMLMG",
                 "M249", "SAR", "M39", "SAP", "M92", "PYTHON"]

    for gun in gun_names:
        for prof in (1, 2):
            var_name = f"{gun}_{prof}_BIND"
            btn = globals().get(var_name)
            if btn is not None:
                vk = BUTTON_TO_VK.get(btn)
                if vk:
                    bindings[(gun, prof)] = vk

    # REVOLVER only has profile 1
    if REVOLVER_1_BIND is not None:
        vk = BUTTON_TO_VK.get(REVOLVER_1_BIND)
        if vk:
            bindings[("REVOLVER", 1)] = vk

    return bindings


def main():
    port = find_arduino()
    if not port:
        print("No Arduino found! Check USB connection.")
        sys.exit(1)

    print(f"Connecting to Arduino on {port}...")
    ser = serial.Serial(port, BAUD_RATE, timeout=1)
    time.sleep(1)

    # Send status check
    ser.write(b"?\n")
    time.sleep(0.1)
    resp = ser.read(ser.in_waiting).decode(errors="ignore").strip()
    if resp:
        print(f"Arduino: {resp}")

    binding_map = build_binding_map()
    if not binding_map:
        print("No gun bindings configured! Edit the BIND variables.")
        ser.close()
        sys.exit(1)

    # Pre-compute all recoil tables
    tables = {}
    for (gun, prof) in binding_map:
        tables[(gun, prof)] = precompute(gun, prof)

    # State
    kickback = False
    active_gun = None
    active_profile = None
    prev_btn = {}

    print("\n" + "=" * 50)
    print("RUST RECOIL CONTROL v2")
    print("=" * 50)
    print(f"Sensitivity: {SENSITIVITY}  FOV: {FOV}  (loaded from {_CFG_SOURCE})")
    sm = -0.03 * (SENSITIVITY * 3) * (FOV / 100)
    print(f"Screen multiplier: {sm:.6f}")
    if abs(ADS_SENSITIVITY - 0.8333) > 0.01:
        print(f"WARNING: Your ads_sensitivity is {ADS_SENSITIVITY} but should be 0.8333")
        print(f"  Run in Rust F1 console: input.ads_sensitivity 0.8333")
    print("\nActive bindings:")
    for (gun, prof), vk in binding_map.items():
        btn = [b for b, v in BUTTON_TO_VK.items() if v == vk][0]
        t = tables[(gun, prof)]
        print(f"  Mouse{btn} -> {gun} (profile {prof}, {t['bullets']} bullets)")
    print("\nPress assigned mouse button to toggle macro ON/OFF")
    print("Right-click (ADS) + Left-click (Fire) to activate recoil control")
    print("Hold Left Ctrl = crouched (no stand multiplier)")
    print("Press Ctrl+C to exit")
    print("=" * 50)

    print("\nWaiting for input... (press Mouse4/Mouse5 to toggle macro)")

    try:
        while True:
            # Check gun toggle buttons
            for (gun, prof), vk in binding_map.items():
                pressed = is_pressed(vk)
                key = (gun, prof)
                was = prev_btn.get(key, False)

                if pressed and not was:
                    # Rising edge - toggle (matches Lua behavior exactly)
                    kickback = not kickback
                    active_gun = gun
                    active_profile = prof
                    if kickback:
                        print(f"{gun}_{prof}_MACRO-ON")
                    else:
                        print(f"{gun}_{prof}_MACRO-OFF")
                        active_gun = None
                        active_profile = None

                prev_btn[key] = pressed

            # Check door unlocker
            if DOOR_UNLOCKER_BIND is not None and KEY_CODE != 0:
                du_vk = BUTTON_TO_VK.get(DOOR_UNLOCKER_BIND)
                if du_vk and is_pressed(du_vk) and not prev_btn.get("door", False):
                    door_unlock(ser)
                if du_vk:
                    prev_btn["door"] = is_pressed(du_vk)

            # If macro active, check for ADS + fire
            if kickback and active_gun and active_profile:
                if is_right_pressed():
                    busy_sleep_ms(5)  # 5ms delay like Lua
                    if is_left_pressed():
                        table = tables.get((active_gun, active_profile))
                        if table:
                            fire_gun(ser, table)

            busy_sleep_ms(1)  # 1ms poll (busy wait for precision)

    except KeyboardInterrupt:
        pass

    ser.close()
    print("\nExited.")


def door_unlock(ser):
    """Door unlocker - automates code entry."""
    n4 = str((KEY_CODE // 1000) % 10)
    n3 = str((KEY_CODE // 100) % 10)
    n2 = str((KEY_CODE // 10) % 10)
    n1 = str(math.ceil(KEY_CODE % 10))

    press_key(0x45)  # VK_E
    busy_sleep_ms(250)
    send_move(ser, 50, 50)
    busy_sleep_ms(70)
    ser.write(b"c\n")  # Click
    busy_sleep_ms(70)
    release_key(0x45)
    busy_sleep_ms(40)

    for digit in [n4, n3, n2, n1]:
        vk = 0x30 + int(digit)  # VK_0 through VK_9
        press_key(vk)
        busy_sleep_ms(10)
        release_key(vk)
        busy_sleep_ms(40)


if __name__ == "__main__":
    main()
