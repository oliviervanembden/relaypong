from codecs import namereplace_errors
from idlelib.debugobj_r import remote_object_tree_item
import os
import sys

# ------------------------- Debug / Logging -------------------------
_DEBUG = os.getenv("SIM_VERBOSE", "0") == "1"

def set_debug(enabled: bool) -> None:
    """Extern te togglen vanuit tests of REPL: sim.set_debug(True/False)."""
    global _DEBUG
    _DEBUG = bool(enabled)

def _id(obj):
    """Korte hex-id voor compacte logs."""
    return hex(id(obj))[-6:]

def _pin_name(pin_code: int) -> str:
    return { -1: "SRC", 0: "COIL", 1: "COMM", 2: "NC", 3: "NO", 4: "DIODE", 5: "LED" }.get(pin_code, f"PIN{pin_code}")

def _log(msg: str) -> None:
    """Eén plek voor alle logs. Schrijft alleen als _DEBUG True is."""
    if _DEBUG:
        print(msg)

# --------------------- (ongewijzigde helper) -----------------------
def _dedup_updates(pins):
    """Dedupliceer pin-lijsten [obj, code] zonder hashable te eisen."""
    seen = set()
    out = []
    for p in pins:
        if not p:
            continue
        key = (id(p[0]), p[1])  # object-identiteit + pin-code
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out
def _enable_ansi():
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 0x0004)
        except Exception:
            pass

# -------- Cross-platform non-blocking keyboard --------
if os.name == "nt":
    import msvcrt
    class Keyboard:
        def __init__(self):
            self._down = set()
            self._edge = set()
        def start(self): pass
        def step(self):
            # IMPORTANT: clear per-tick state so momentary buttons release
            self._edge.clear()
            self._down.clear()
            # Drain all keypresses available this tick (non-blocking)
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\b", "\x08"):
                    k = "backspace"
                else:
                    k = ch.lower()
                self._edge.add(k)   # rising edge this tick
                self._down.add(k)   # treated as "held this tick"
        def stop(self): pass
        def pressed(self, k): return k in self._down
        def edge(self, k):    return k in self._edge

else:
    import termios, tty, select
    class Keyboard:
        def __init__(self):
            self._orig = None
            self._edge = set()
            self._down = set()  # lightweight: treat any read char as pressed for this tick
        def start(self):
            fd = sys.stdin.fileno()
            self._orig = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        def step(self):
            self._edge.clear()
            self._down.clear()
            # Drain all ready chars this tick (non-blocking)
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0)
                if not r: break
                ch = sys.stdin.read(1)
                if ch in ("\x7f", "\b"):
                    k = "backspace"
                else:
                    k = ch.lower()
                self._edge.add(k)
                self._down.add(k)
        def stop(self):
            if self._orig is not None:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._orig)
                self._orig = None
        def pressed(self, k): return k in self._down
        def edge(self, k):    return k in self._edge

# -------- Devices that your engine can tick (pin == 5) --------
class ButtonKey:
    """
    Drives an output wire from a keyboard key.

    mode:
      - "momentary": out_wire.power = 1 while key is observed this tick
      - "edge":      out_wire.power = 1 for one tick on *press* (rising edge)
    """
    def __init__(self, out_wire, key: str, keyboard: Keyboard, mode: str = "momentary"):
        self.out = out_wire
        self.key = key.lower()
        self.kb  = keyboard
        self.mode = mode
        # Make the engine call update() when pin==5 (same pattern as your LED)
        out_wire.connectPin([self, 5])

    def update(self):
        if self.mode == "edge":
            self.out.power = 1 if self.kb.edge(self.key) else 0
        else:  # momentary
            # Treat "pressed this tick" as on. For Windows this acts like edge unless auto-repeat.
            self.out.power = 1 if (self.kb.pressed(self.key) or self.kb.edge(self.key)) else 0

class ResetKey:
    """
    Emits a one-tick reset pulse on Backspace (default).
    Hook this to your reset bus or RC-init logic.
    """
    def __init__(self, out_wire, keyboard: Keyboard, key: str = "backspace"):
        self.out = out_wire
        self.key = key.lower()
        self.kb  = keyboard
        self.out.connectPin([self, 5])

    def update(self):
        # One-tick pulse on press edge
        self.out.power = 1 if self.kb.edge(self.key) else 0


# -------- WindowGrid: tiny terminal renderer you can pass into LEDs --------
class WindowGrid:
    def __init__(self, width, height,
                 on_char="● ", off_char="· ",
                 col_on="\x1b[38;5;220m", col_off="\x1b[38;5;237m", use_color=True):
        _enable_ansi()
        self.w, self.h = width, height
        self.on_char, self.off_char = on_char, off_char
        self.col_on  = col_on  if use_color else ""
        self.col_off = col_off if use_color else ""
        self.reset   = "\x1b[0m" if use_color else ""
        self.grid    = [[False]*width for _ in range(height)]
        self._prev_lines = None
        self._started = False
        self._title_lines = 0
        self._cursor_hidden = False

    # LEDs (or any logic) call this during their update()
    def stage(self, x, y, on: bool):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = bool(on)

    def _hide_cursor(self):
        if not self._cursor_hidden:
            sys.stdout.write("\x1b[?25l"); self._cursor_hidden = True

    def _show_cursor(self):
        if self._cursor_hidden:
            sys.stdout.write("\x1b[?25h"); self._cursor_hidden = False

    def _build_line(self, y):
        out, cur = [], None
        row = self.grid[y]
        for x in range(self.w):
            on = row[x]
            col = self.col_on if on else self.col_off
            ch  = self.on_char if on else self.off_char
            if col != cur:
                out.append(col); cur = col
            out.append(ch)
        out.append(self.reset)
        return "".join(out)

    # Call once per tick (after your engine check pass)
    def flush(self, title=None):
        lines = [self._build_line(y) for y in range(self.h)]
        if not self._started:
            self._hide_cursor()
            sys.stdout.write("\x1b[2J\x1b[H")
            if title:
                sys.stdout.write(title + "\n"); self._title_lines = 1
            else:
                self._title_lines = 0
            sys.stdout.write("\n".join(lines) + "\n"); sys.stdout.flush()
            self._prev_lines = lines; self._started = True
            return

        out = []
        if title and self._title_lines:
            out.append(f"\x1b[1;1H{title}\x1b[K")
        for i, (n, o) in enumerate(zip(lines, self._prev_lines)):
            if n != o:
                rowno = self._title_lines + i + 1
                out.append(f"\x1b[{rowno};1H{n}\x1b[K")
        if out:
            sys.stdout.write("".join(out)); sys.stdout.flush()
            self._prev_lines = lines

    def close(self):
        self._show_cursor()
        sys.stdout.write(self.reset + "\n"); sys.stdout.flush()

# ----------------------------- wire --------------------------------
class wire:
    def __init__(self,):
        self.power = 0
        self.poweringPin = []
        self.poweredPin = []

    def powerWireOn(self, pin):
        _log(f"[WIRE  {_id(self)}] ON  ← from {type(pin[0]).__name__}@{_id(pin[0])}:{_pin_name(pin[1])} | "
             f"was power={self.power} | powering={self._pins_str(self.poweringPin)} powered={self._pins_str(self.poweredPin)}")
        if pin in self.poweredPin:
            _log(f"[WIRE  {_id(self)}]   ↳ already powered by same source; no-op")
            return []
        self.poweredPin.append(pin)
        if pin in self.poweringPin:
            self.poweringPin.remove(pin)
        if self.power:
            _log(f"[WIRE  {_id(self)}]   ↳ wire already high; added source, no propagation")
            return []
        else:
            self.power = 1
            _log(f"[WIRE  {_id(self)}]   ↳ wire became HIGH | powering={self._pins_str(self.poweringPin)} powered={self._pins_str(self.poweredPin)}")
            return self.poweringPin  # nieuwe pins die gecheckt moeten worden

    def powerWireOff(self, pin):
        _log(f"[WIRE  {_id(self)}] OFF ← from {type(pin[0]).__name__}@{_id(pin[0])}:{_pin_name(pin[1])} | "
             f"was power={self.power} | powering={self._pins_str(self.poweringPin)} powered={self._pins_str(self.poweredPin)}")
        if pin in self.poweringPin:
            _log(f"[WIRE  {_id(self)}]   ↳ already pending-off from this source; no-op")
            return []
        if pin in self.poweredPin:
            self.poweredPin.remove(pin)
        if pin not in self.poweringPin:
            self.poweringPin.append(pin)
        if self.poweredPin == []:
            self.power = 0
            _log(f"[WIRE  {_id(self)}]   ↳ wire became LOW | powering={self._pins_str(self.poweringPin)} powered={self._pins_str(self.poweredPin)}")
            return self.poweringPin
        else:
            _log(f"[WIRE  {_id(self)}]   ↳ other sources still active; stays HIGH")
            return []

    def connectPin(self, pin):
        self.poweringPin.append(pin)
        _log(f"[WIRE  {_id(self)}] CONNECT {type(pin[0]).__name__}@{_id(pin[0])}:{_pin_name(pin[1])} "
             f"| powering={self._pins_str(self.poweringPin)}")
    def getPins(self):
        return self.poweringPin

    @staticmethod
    def _pins_str(pins):
        out = []
        for p in pins:
            try:
                out.append(f"{type(p[0]).__name__}@{hex(id(p[0]))[-6:]}:{_pin_name(p[1])}")
            except Exception:
                out.append(str(p))
        return "[" + ", ".join(out) + "]"

# ----------------------------- diode -------------------------------
class diode:
    def __init__(self, powerIn: type[wire], powerOut: type[wire]):
        self.powerIn = powerIn
        self.powerOut = powerOut
        self.powerIn.connectPin([self, 4])
        self.powerOut.connectPin([self, -1])
        _log(f"[DIODE {_id(self)}] IN={_id(self.powerIn)} → OUT={_id(self.powerOut)} connected")

    def updateDiode(self):
        if self.powerIn.power:
            _log(f"[DIODE {_id(self)}] propagate HIGH IN→OUT")
            return self.powerOut.powerWireOn([self, -1])
        else:
            _log(f"[DIODE {_id(self)}] propagate LOW IN→OUT")
            return self.powerOut.powerWireOff([self, -1])

# ----------------------------- relay -------------------------------
class relay:
    def __init__(self, coil: type[wire], comm: type[wire], nc: type[wire], no: type[wire]):
        self.coilWire = coil
        self.commWire = comm
        self.ncWire = nc
        self.noWire = no
        self.state = 0
        coil.connectPin([self, 0])
        comm.connectPin([self, 1])
        nc.connectPin([self, 2])
        no.connectPin([self, 3])
        _log(f"[RELAY {_id(self)}] init state=OFF | COIL={_id(coil)} COMM={_id(comm)} NC={_id(nc)} NO={_id(no)}")

    def powerRelayOff(self):
        updates = []
        _log(f"[RELAY {_id(self)}] COIL→OFF (state was {self.state})")
        if self.state == 0:
            _log(f"[RELAY {_id(self)}]   ↳ already OFF; no-op")
            return []
        self.state = 0
        updates.extend(self.noWire.powerWireOff([self, 3]))
        updates.extend(self.commWire.powerWireOff([self, 1]))
        if self.ncWire.power:
            updates.extend(self.commWire.powerWireOn([self, 1]))
        if self.commWire.power:
            updates.extend(self.ncWire.powerWireOn([self, 2]))
        updates = _dedup_updates(updates)
        _log(f"[RELAY {_id(self)}]   ↳ queued updates: {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in updates]}")
        return updates

    def powerRelayOn(self):
        updates = []
        _log(f"[RELAY {_id(self)}] COIL→ON (state was {self.state})")
        if self.state == 1:
            _log(f"[RELAY {_id(self)}]   ↳ already ON; no-op")
            return []
        self.state = 1
        updates.extend(self.ncWire.powerWireOff([self, 2]))
        updates.extend(self.commWire.powerWireOff([self, 1]))
        if self.noWire.power:
            updates.extend(self.commWire.powerWireOn([self, 1]))
        if self.commWire.power:
            updates.extend(self.noWire.powerWireOn([self, 3]))
        updates = _dedup_updates(updates)
        _log(f"[RELAY {_id(self)}]   ↳ queued updates: {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in updates]}")
        return updates

    def getConnection(self, pin):
        _log(f"[RELAY {_id(self)}] getConnection({ _pin_name(pin) }) | state={'ON' if self.state else 'OFF'} "
             f"| COMM={self.commWire.power} NC={self.ncWire.power} NO={self.noWire.power}")

        if pin == 1:
            if [self, pin] in self.commWire.poweredPin:
                return []
            if self.commWire.power:
                if self.state:
                    return self.noWire.powerWireOn([self, 3])
                else:
                    return self.ncWire.powerWireOn([self, 2])
            else:
                if self.state:
                    return self.noWire.powerWireOff([self, 3])
                else:
                    return self.ncWire.powerWireOff([self, 2])
        elif pin == 3:
            if [self, pin]  in self.noWire.poweredPin:
                return []
            if self.state:
                if self.noWire.power:
                    return self.commWire.powerWireOn([self, 1])
                else:
                    return self.commWire.powerWireOff([self, 1])
            else:
                return []
        elif pin == 2:
            if [self, pin]  in self.ncWire.poweredPin:
                return []
            if self.state == 0:
                if self.ncWire.power:
                    return self.commWire.powerWireOn([self, 1])
                else:
                    return self.commWire.powerWireOff([self, 1])
            else:
                return []
        else:
            return []

class relay_dpdt:
    def __init__(self, coil: type[wire],
                 com1: type[wire], nc1: type[wire], no1: type[wire],
                 com2: type[wire], no2: type[wire], nc2: type[wire]):
        self.coilWire = coil
        self.com1Wire = com1
        self.nc1Wire  = nc1
        self.no1Wire  = no1
        self.com2Wire = com2
        self.no2Wire  = no2
        self.nc2Wire  = nc2
        self.state = 0
        coil.connectPin([self, 7])
        com1.connectPin([self, 8]);  nc1.connectPin([self, 9]);  no1.connectPin([self,10])
        com2.connectPin([self,11]);  no2.connectPin([self,12]);  nc2.connectPin([self,13])
        _log(f"[RELAY {_id(self)}] init state=OFF | COIL={_id(coil)} "
             f"COM1={_id(com1)} NC1={_id(nc1)} NO1={_id(no1)} "
             f"COM2={_id(com2)} NO2={_id(no2)} NC2={_id(nc2)}")

    def powerRelayOff(self):
        updates = []
        _log(f"[RELAY {_id(self)}] COIL→OFF (state was {self.state})")
        if self.state == 0:
            _log(f"[RELAY {_id(self)}]   ↳ already OFF; no-op")
            return []
        self.state = 0

        # Pole 1: break NO1, clear COM1, then make COM1↔NC1
        updates.extend(self.no1Wire.powerWireOff([self,10]))
        updates.extend(self.com1Wire.powerWireOff([self, 8]))
        if self.nc1Wire.power:
            updates.extend(self.com1Wire.powerWireOn([self, 8]))
        if self.com1Wire.power:
            updates.extend(self.nc1Wire.powerWireOn([self, 9]))

        # Pole 2: break NO2, clear COM2, then make COM2↔NC2
        updates.extend(self.no2Wire.powerWireOff([self,12]))
        updates.extend(self.com2Wire.powerWireOff([self,11]))
        if self.nc2Wire.power:
            updates.extend(self.com2Wire.powerWireOn([self,11]))
        if self.com2Wire.power:
            updates.extend(self.nc2Wire.powerWireOn([self,13]))

        updates = _dedup_updates(updates)
        _log(f"[RELAY {_id(self)}]   ↳ queued updates: {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in updates]}")
        return updates

    def powerRelayOn(self):
        updates = []
        _log(f"[RELAY {_id(self)}] COIL→ON (state was {self.state})")
        if self.state == 1:
            _log(f"[RELAY {_id(self)}]   ↳ already ON; no-op")
            return []
        self.state = 1

        # Pole 1: break NC1, clear COM1, then make COM1↔NO1
        updates.extend(self.nc1Wire.powerWireOff([self, 9]))
        updates.extend(self.com1Wire.powerWireOff([self, 8]))
        if self.no1Wire.power:
            updates.extend(self.com1Wire.powerWireOn([self, 8]))
        if self.com1Wire.power:
            updates.extend(self.no1Wire.powerWireOn([self,10]))

        # Pole 2: break NC2, clear COM2, then make COM2↔NO2
        updates.extend(self.nc2Wire.powerWireOff([self,13]))
        updates.extend(self.com2Wire.powerWireOff([self,11]))
        if self.no2Wire.power:
            updates.extend(self.com2Wire.powerWireOn([self,11]))
        if self.com2Wire.power:
            updates.extend(self.no2Wire.powerWireOn([self,12]))

        updates = _dedup_updates(updates)
        _log(f"[RELAY {_id(self)}]   ↳ queued updates: {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in updates]}")
        return updates

    def getConnection(self, pin):
        _log(f"[RELAY {_id(self)}] getConnection({_pin_name(pin)}) | state={'ON' if self.state else 'OFF'} "
             f"| COM1={self.com1Wire.power} NC1={self.nc1Wire.power} NO1={self.no1Wire.power} "
             f"| COM2={self.com2Wire.power} NC2={self.nc2Wire.power} NO2={self.no2Wire.power}")

        # --- Pole 1 (8,9,10) ---
        if pin == 8:  # COM1
            if [self, pin] in self.com1Wire.poweredPin:
                return []
            if self.com1Wire.power:
                if self.state:
                    return self.no1Wire.powerWireOn([self,10])
                else:
                    return self.nc1Wire.powerWireOn([self, 9])
            else:
                if self.state:
                    return self.no1Wire.powerWireOff([self,10])
                else:
                    return self.nc1Wire.powerWireOff([self, 9])

        elif pin == 10:  # NO1
            if [self, pin] in self.no1Wire.poweredPin:
                return []
            if self.state:
                if self.no1Wire.power:
                    return self.com1Wire.powerWireOn([self, 8])
                else:
                    return self.com1Wire.powerWireOff([self, 8])
            else:
                return []

        elif pin == 9:   # NC1
            if [self, pin] in self.nc1Wire.poweredPin:
                return []
            if self.state == 0:
                if self.nc1Wire.power:
                    return self.com1Wire.powerWireOn([self, 8])
                else:
                    return self.com1Wire.powerWireOff([self, 8])
            else:
                return []

        # --- Pole 2 (11,12,13) ---
        elif pin == 11:  # COM2
            if [self, pin] in self.com2Wire.poweredPin:
                return []
            if self.com2Wire.power:
                if self.state:
                    return self.no2Wire.powerWireOn([self,12])
                else:
                    return self.nc2Wire.powerWireOn([self,13])
            else:
                if self.state:
                    return self.no2Wire.powerWireOff([self,12])
                else:
                    return self.nc2Wire.powerWireOff([self,13])

        elif pin == 12:  # NO2
            if [self, pin] in self.no2Wire.poweredPin:
                return []
            if self.state:
                if self.no2Wire.power:
                    return self.com2Wire.powerWireOn([self,11])
                else:
                    return self.com2Wire.powerWireOff([self,11])
            else:
                return []

        elif pin == 13:  # NC2
            if [self, pin] in self.nc2Wire.poweredPin:
                return []
            if self.state == 0:
                if self.nc2Wire.power:
                    return self.com2Wire.powerWireOn([self,11])
                else:
                    return self.com2Wire.powerWireOff([self,11])
            else:
                return []

        else:
            return []


# ------------------------------ led --------------------------------
class led:
    def __init__(self, in_wire: type[wire], x: int, y: int, window: WindowGrid | None = None):
        self.in_wire = in_wire
        self.x, self.y = x, y
        self.window = window
        self.state = 0
        # Assuming your LED uses pin 5 in the engine:
        in_wire.connectPin([self, 5])

    def update(self):
        # Called by engine when pin==5
        new_state = 1 if self.in_wire.power else 0
        if new_state != self.state:
            self.state = new_state
        if self.window is not None:
            self.window.stage(self.x, self.y, bool(self.state))

# ---------------------------- button -------------------------------
class button:
    def __init__(self, wire):
        self.wire = wire
        self.wire.connectPin([self, -1])
        _log(f"[BUTTON{_id(self)}] connected to WIRE={_id(self.wire)}")

    def press(self):
        _log(f"[BUTTON{_id(self)}] press()")
        return self.wire.powerWireOn([self, -1])

    def release(self):
        _log(f"[BUTTON{_id(self)}] release()")
        return self.wire.powerWireOff([self, -1])

# ----------------------------- engine ------------------------------
def check(WireIn):
    toCheck = []
    toCheck.extend(WireIn)
    _log(f"[ENGINE] start with {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in toCheck]}")

    while toCheck != []:
        _log(f"[ENGINE] next-layer → {[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in toCheck]}")
        check_list = toCheck.copy()
        toCheck.clear()

        for pin in check_list:
            dev, pnum = pin[0], pin[1]
            _log(f"[ENGINE] check {type(dev).__name__}@{_id(dev)}:{_pin_name(pnum)}")

            if pnum == -1:
                continue

            # ---- Relay coil pins ----
            elif pnum == 0 or pnum == 7:  # SPDT coil=0, DPDT coil=7
                if dev.coilWire.power == 1:
                    toCheck.extend(dev.powerRelayOn())
                if dev.coilWire.power == 0:
                    toCheck.extend(dev.powerRelayOff())

            # ---- Relay contact pins ----
            elif (1 <= pnum <= 3) or (8 <= pnum <= 13):  # SPDT contacts 1..3, DPDT contacts 8..13
                addToCheck = dev.getConnection(pnum)
                _log(f"[ENGINE] relay pin {_pin_name(pnum)} produced "
                     f"{[(type(p[0]).__name__, _id(p[0]), _pin_name(p[1])) for p in addToCheck]}")
                toCheck.extend(addToCheck)

            # ---- Diode ----
            elif pnum == 4:
                toCheck.extend(dev.updateDiode())

            # ---- Other active parts (e.g., LED) ----
            elif pnum == 5:
                dev.update()

        # filter empty entries
        toCheck = [x for x in toCheck if x]

    _log(f"[ENGINE] done.")




if __name__ == "__main__":
    print("je zit in de verkeerde file")
