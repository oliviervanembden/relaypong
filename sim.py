import os, time, sys
from math import gamma, trunc

if os.name != "nt":
    raise SystemExit("This script is Windows-only (uses msvcrt + Windows console).")

import msvcrt

# ---------- ANSI enable (Windows 10+) ----------
def _enable_ansi():
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass

# ---------- Tiny LED display ----------
class LEDDisplay:
    def __init__(self, w: int, h: int,
                 on_char="● ", off_char="· ",
                 col_on="\x1b[38;5;220m", col_off="\x1b[38;5;237m",
                 use_color=True):
        _enable_ansi()
        self.w, self.h = w, h
        self.on_char, self.off_char = on_char, off_char
        self.col_on  = col_on  if use_color else ""
        self.col_off = col_off if use_color else ""
        self.reset   = "\x1b[0m" if use_color else ""
        self.grid    = [[False]*w for _ in range(h)]
        self._started = False
        self._title = ""
        self._cursor_hidden = False

    def set(self, x, y, state: bool):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = bool(state)

    def clear(self):
        for y in range(self.h):
            for x in range(self.w):
                self.grid[y][x] = False

    def _hide_cursor(self):
        if not self._cursor_hidden:
            sys.stdout.write("\x1b[?25l")
            self._cursor_hidden = True

    def _show_cursor(self):
        if self._cursor_hidden:
            sys.stdout.write("\x1b[?25h")
            self._cursor_hidden = False

    def _line(self, y):
        row = self.grid[y]
        out = []
        cur = None
        for x in range(self.w):
            on = row[x]
            col = self.col_on if on else self.col_off
            ch  = self.on_char if on else self.off_char
            if col != cur:
                out.append(col); cur = col
            out.append(ch)
        out.append(self.reset)
        return "".join(out)

    def render(self, title: str | None = None):
        lines = [self._line(y) for y in range(self.h)]
        if not self._started:
            self._hide_cursor()
            sys.stdout.write("\x1b[2J\x1b[H")  # clear & home
            if self._title:
                sys.stdout.write(self._title + "\n")
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()
            self._started = True
            return
        # rewrite in place
        out = []
        out.append("\x1b[H")  # home
        if self._title:
            out.append(self._title + "\n")
        out.append("\n".join(lines) + "\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def close(self):
        self._show_cursor()
        sys.stdout.write(self.reset + "\n")
        sys.stdout.flush()

# ---------- Windows non-blocking input (Q,A,O,L) ----------
class WinInputs4:
    KEYS = ("q", "a", "o", "l")
    def __init__(self):
        self._edge = set()
        self._down = set()
    def step(self):
        self._edge.clear()
        self._down.clear()
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if not ch:
                continue
            k = ch.lower()
            if k in ("\b", "\x08"):
                k = "backspace"
            self._edge.add(k)
            self._down.add(k)
    def pressed(self, key): return key.lower() in self._down
    def edge(self, key):    return key.lower() in self._edge

# ---------- Simple clock (edge once per period) ----------
class Clock:
    def __init__(self, hz: float):
        self.period = 1.0/float(hz)
        self.next_t = time.perf_counter() + self.period
        self.edge_flag = False
    def step(self):
        now = time.perf_counter()
        self.edge_flag = False
        if now >= self.next_t:
            missed = int((now - self.next_t)//self.period) + 1
            self.next_t += missed * self.period
            self.edge_flag = True
    def edge(self): return self.edge_flag


class biRingCounter:
    def __init__(self,len):
        self.pos = 0
        self.len = len
        return
    def up(self):
        if self.pos < self.len:
            self.pos+=1

        return self.pos
    def down(self):
        if self.pos > 0:
            self.pos -= 1
        return self.pos

class ball:
    def __init__(self,xRing,yRing,aRing,bRing):
        self.xRing = xRing
        self.yRing = yRing
        self.aRing = aRing
        self.bRing = bRing
        self.ydirection  = 0
        self.xdirection = 0
        self.scorea = 0
        self.scoreb = 0


    def calintersecta(self):
        #print("calculating intersect a ")
        disp.set(0, batay.pos, True)
        disp.set(0, batay.pos + 1, True)
        disp.set(0, batay.pos + 2, True)
        disp.render()
        bounce = 0
        if self.yRing.pos == (self.aRing.pos+1):
            self.xdirection = 1
            self.xRing.up()
            bounce = 1
            #print("diriect hit")
        if self.yRing.pos == self.aRing.pos:
            self.xdirection = 1
            self.ydirection = -1
            self.xRing.up()
            bounce = 1
            #print(" one above")
        if self.yRing.pos == (self.aRing.pos +2):
            self.xdirection = 1
            self.ydirection = 1
            self.xRing.up()
            bounce = 1
            #print(" one belo")
        disp.set(W - 1, batby.pos, True)
        disp.set(W - 1, batby.pos + 1, True)
        disp.set(W - 1, batby.pos + 2, True)
        disp.render()
        if bounce == 0:
            self.scoreb +=1
            print(f"score player a is {self.scorea} score player b is {self.scoreb}")
            #print("miss")
            moveballtoCenter()

    def calintersectb(self):
        #print("calculating intersect b ")

        bounce = 0
        if self.yRing.pos == (self.bRing.pos+1):
            self.xdirection = 0
            self.xRing.down()
            bounce = 1
            #print("diriect hit")
        if self.yRing.pos == (self.bRing.pos):
            self.xdirection = 0
            self.ydirection = -1
            bounce = 1
            self.xRing.down()
            #print(" one above")
        if self.yRing.pos == (self.bRing.pos+2):
            self.xdirection = 0
            self.ydirection = 1
            disp.render()
            #print(" one belo")
            bounce = 1
        disp.set(W - 1, batby.pos, True)
        disp.set(W - 1, batby.pos + 1, True)
        disp.set(W - 1, batby.pos + 2, True)
        disp.render()
        if bounce == 0:
            self.scorea +=1
            print(f"score player a is {self.scorea} score player b is {self.scoreb}")
            moveballtoCenter()

    def move(self):
        if self.xRing.pos == 0 and self.xdirection == 0:
            self.calintersecta()
        elif self.xRing.pos == self.xRing.len and self.xdirection == 1:
            self.calintersectb()
        else:
            disp.set(self.xRing.pos, self.yRing.pos, False)
            if self.xdirection:
                self.xRing.up()
            else:
                self.xRing.down()
            if self.ydirection != 0: # do the wall bounce fuction
                if self.yRing.pos == self.yRing.len-1:
                    self.ydirection = -1
                if self.yRing.pos == 0:
                    self.ydirection = 1

            if self.ydirection == -1:
                self.yRing.down()
            if self.ydirection == 1:
                self.yRing.up()

            if self.xRing.pos == 0 and self.xdirection == 0:
                self.calintersecta()
            if self.xRing.pos == self.xRing.len and self.xdirection == 1:
                self.calintersectb()
            disp.set(self.xRing.pos, self.yRing.pos, True)
            disp.set(W - 1, batby.pos, True)
            disp.set(W - 1, batby.pos + 1, True)
            disp.set(W - 1, batby.pos + 2, True)
            disp.set(0, batay.pos, True)
            disp.set(0, batay.pos + 1, True)
            disp.set(0, batay.pos + 2, True)
            disp.render()
def on_q():
    disp.set(0, batay.pos  , False)
    disp.set(0, batay.pos +1, False)
    disp.set(0, batby.pos +2, False)

    batay.up()
    disp.set(0, batay.pos , True)
    disp.set(0, batay.pos + 1, True)
    disp.set(0, batay.pos + 2, True)
    disp.render(title)



def on_a():
    disp.set(0, batay.pos  , False)
    disp.set(0, batay.pos +1, False)
    disp.set(0, batay.pos +2, False)

    batay.down()
    disp.set(0, batay.pos , True)
    disp.set(0, batay.pos + 1, True)
    disp.set(0, batay.pos + 2, True)
    disp.render(title)



def on_o():
    disp.set(W-1, batby.pos  , False)
    disp.set(W - 1, batby.pos +1, False)
    disp.set(W - 1, batby.pos +2, False)

    batby.up()
    disp.set(W-1, batby.pos , True)
    disp.set(W - 1, batby.pos + 1, True)
    disp.set(W - 1, batby.pos + 2, True)
    disp.render(title)


def on_l():
    disp.set(W-1, batby.pos  , False)
    disp.set(W - 1, batby.pos +1, False)
    disp.set(W - 1, batby.pos +2, False)

    batby.down()
    disp.set(W-1, batby.pos , True)
    disp.set(W - 1, batby.pos + 1, True)
    disp.set(W - 1, batby.pos + 2, True)
    disp.render(title)


# ---------- Demo main: 2×2 board, Q/A/O/L → pixels ----------
W, H = 10, 7
batay = biRingCounter(H-3)
batby = biRingCounter(H-3)
gameBall = ball(biRingCounter(W-1),biRingCounter(H),batay,batby)
disp = LEDDisplay(W, H)
io = WinInputs4()
clk = Clock(5.0)  # 5 Hz heartbeat in the title

title_base = "Q→(0,0)  O→(1,0)  A→(0,1)  L→(1,1)    (Ctrl+C to exit)"
heartbeat = " "
t0 = time.perf_counter()
title = f"{title_base}   clk:{heartbeat}"
def moveballtoCenter():

    gameBall.xRing.pos = 0
    gameBall.yRing.pos = 0

    for a in range(int(W/2)-1):
        while True:
            io.step()
            clk.step()
            if clk.edge():
                break
            if io.edge("a"): on_q()
            if io.edge("q"): on_a()
            if io.edge("l"): on_o()
            if io.edge("o"): on_l()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, False)
        gameBall.xRing.up()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, True)
        disp.render(title)

    for a in range(int(H/2)):
        while True:
            io.step()
            clk.step()
            if clk.edge():
                break
            if io.edge("a"): on_q()
            if io.edge("q"): on_a()
            if io.edge("l"): on_o()
            if io.edge("o"): on_l()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, False)
        gameBall.yRing.up()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, True)
        disp.render(title)

try:
    # the setup
    for a in range(int(W/2)-1):
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, False)
        gameBall.xRing.up()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, True)
        time.sleep(0.1)
        disp.render(title)
    for a in range(int(H/2)):
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, False)
        gameBall.yRing.up()
        disp.set(gameBall.xRing.pos, gameBall.yRing.pos, True)
        time.sleep(0.1)
        disp.render(title)
    for a in range(int(H/2)-1):
        on_q()
        on_o()
    print(f"score player a is {0} score player b is {0}")



    while True:
        # input + clock
        io.step()
        clk.step()
        if clk.edge():
            # toggle a tiny heartbeat dot in the title
            gameBall.move()
        # map pressed→LEDs (lit while key is held)

        if io.edge("a"): on_q()
        if io.edge("q"): on_a()
        if io.edge("l"): on_o()
        if io.edge("o"): on_l()

        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    disp.close()

