# test_ring_two_phase.py
import time
import sim

# --- helper: one-tick pulse (no permanent source) ---
class _SRC: pass
def pulse(w):
    on  = w.powerWireOn([_SRC(), -1]); sim.check(on)
    off = w.powerWireOff([_SRC(), -1]); sim.check(off)

# --- build N one-hot rows using DPDT self-hold + LEDs (no gates) ---
def build_rows(win_h: int, rows):
    win = sim.WindowGrid(1, win_h)
    coils = []
    states = []
    leds = []
    for y in rows:
        c = sim.wire(); coils.append(c)
        # DPDT: COM1 -> NO1 back to its own coil = self-hold path
        states.append(sim.relay_dpdt(
            coil=c,
            com1=c, nc1=sim.wire(), no1=c,
            com2=sim.wire(), no2=sim.wire(), nc2=sim.wire()
        ))
        leds.append(sim.led(c, 0, y, win))
    # tick contacts & leds each frame
    service = [[s,8] for s in states] + [[L,5] for L in leds]
    return win, coils, service

# --- two-phase mover: fixes "instant" contact issue in the sim ---
class PhasedMover:
    """
    On Q/A edge:
      phase=2: drop all coils (tick 1)
      phase=1: pulse target coil (tick 2)
      phase=0: idle
    """
    def __init__(self, coils, kb, rows):
        self.coils = coils
        self.kb = kb
        self.rows = rows
        self.phase = 0
        self.target = None

    def _current_index(self):
        for i, c in enumerate(self.coils):
            if c.power: return i
        return None

    def step(self):
        # start a move on edge
        if self.phase == 0:
            if self.kb.edge("q") or self.kb.edge("a"):
                cur = self._current_index()
                if cur is None:
                    cur = 0  # if nothing lit yet, start from first
                N = len(self.coils)
                self.target = (cur - 1) % N if self.kb.edge("q") else (cur + 1) % N
                self.phase = 2

        # phase 2: drop everything
        if self.phase == 2:
            pending = []
            for c in self.coils:
                pending += c.powerWireOff([_SRC(), -1])
            sim.check(pending)
            self.phase = 1
            return

        # phase 1: pulse target so it re-latches itself
        if self.phase == 1:
            pulse(self.coils[self.target])
            self.phase = 0

def main():
    H = 10
    rows = list(range(1, H-1))[:-1]  # 1..H-2
    kb = sim.Keyboard(); kb.start()

    win, coils, service = build_rows(H, rows)
    mover = PhasedMover(coils, kb, rows)

    title = f"Two-phase ring — Q=up, A=down, wrap. Rows={rows}. Backspace=recenter"
    try:
        # init: light the first row
        pulse(coils[0])
        sim.check(service); win.flush(title)

        while True:
            kb.step()

            # optional: recentre on Backspace
            if kb.edge("backspace"):
                pending = []
                for c in coils:
                    pending += c.powerWireOff([_SRC(), -1])
                sim.check(pending)
                pulse(coils[len(rows)//2])

            mover.step()          # performs reset/set across ticks
            sim.check(service)    # keep DPDT contacts & LEDs evaluated
            win.flush(title)
            time.sleep(0.02)
    finally:
        kb.stop()
        win.close()

if __name__ == "__main__":
    main()
