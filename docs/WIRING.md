# Wiring the housing

Gut the old board completely. You keep the **light tower** (a ring of
individual lights, fired in sequence to make the rotating strobe), the
**speaker**, and the shell. It runs on three salvaged 18650 cells in
parallel, charged through the panel-mount barrel jack, in place of the old
D cells.

## Power

```
5 V adapter ─► barrel jack ─► 1S charge/boost (UPS) module ─► 5 V rail
                                   │                        (XIAO 5V, amp, LED driver)
                         3× 18650 in parallel (1S3P)
                                   │
                        VBAT ─[100k]─┬─[100k]─ GND
                                     └─► PIN_VBAT (battery gauge)
```

**Module requirements.** Pick one that:
* charges and powers the load at the same time (sold as "UPS",
  "load-sharing" or "pass-through"), so the light keeps running on the charger,
* has **no automatic low-load shut-off**. Power-bank chips like the IP5306
  turn their output off when the load drops below ~50 mA, and an idle ESP32
  can drop that low. Known good: **Adafruit PowerBoost 1000C** (1 A
  charge, 1 A out, no auto-off). Generic "18650 UPS 5V" boards vary, so
  check the listing for "no auto shutdown".
* can supply at least the tower + amp current. Measure the tower first. If
  it plus the amp at full volume is over ~1 A, use a 2 A module or keep the
  volume down.

Use a **5 V 2 A** wall adapter with a 5.5×2.1 mm plug, center positive.

**Salvaged cells: check before paralleling.**
* Only use cells that rest at **≥ 3.0 V** and have no dents, rust or
  swelling. Recycle anything below ~2.5 V.
* Charge each one on its own, let it sit a week, and recheck. Recycle any
  that dropped more than ~0.1 V (high self-discharge).
* Bring all three to within **0.05 V** of each other before connecting them
  in parallel. Otherwise the fullest cell dumps current into the emptiest.
* Use a holder or spot-welded nickel strip, and keep the cells away from the
  speaker magnet and sharp edges. Don't solder directly to the cells.
* Put a **3 A fuse** (or a protection board) on the pack's + lead if the
  module has no battery protection of its own.

## Before you buy parts: measure the tower

With the old board removed, check these with a multimeter and a 5 V supply
(or the old batteries):

1. **How many lights, and how they're wired.** Look for one wire shared by
   all the lights, plus one wire per light.
   * **Shared wire is + (common anode).** This is the usual case, and the
     ULN2803A below works as-is.
   * **Shared wire is – (common ground).** You need high-side switching
     (a UDN2981 / TBD62783 instead of the ULN2803A). Let me know and I'll
     adjust the plan.
2. **Voltage.** Count the cells in the old battery holder: 3 cells = 4.5 V,
   4 cells = 6 V.
3. **Current per light.** Power one light from the shared wire and measure
   the current. LEDs are usually 20–60 mA, incandescent bulbs 100–300 mA.
4. **Built-in resistors?** If the lights are bare LEDs with no resistor on
   the old board's side, each one needs a resistor:
   (5 V − LED voltage) ÷ current, e.g. (5 − 2.0) / 0.03 ≈ 100 Ω for red.

## Parts

| Part | Notes |
|---|---|
| ESP32-C3 or ESP32-C6 board | C3 SuperMini, C6 DevKitC-1 or XIAO C6 (see pin notes) |
| ULN2803A (DIP-18) | 8 low-side drivers, 500 mA each, flyback diodes built in, takes 3.3 V logic directly |
| MAX98357A I2S amp breakout | ~3 W into 4 Ω at 5 V, drives the original speaker |
| 1000 µF ≥10 V electrolytic cap | across 5 V at the amp/driver |
| 1S UPS / charge-boost module | see **Power** above |
| 3× 18650 + holder, 3 A fuse | salvaged cells, matched (see above) |
| 2× 100 kΩ resistors | battery gauge divider |
| 5 V 2 A adapter | 5.5×2.1 mm plug for the panel jack |
| Momentary push button (optional) | test/stop; can reuse the housing's original button |
| Perfboard or proto PCB | to hold the ULN2803A (use a DIP socket) |

**Incandescent bulbs at 4.5–6 V:** the ULN2803A drops about 1 V, so they'll be
dimmer. Use six logic-level MOSFETs (AO3400 or IRLB8721) instead, one per
light: gate through 100 Ω to the GPIO, 10 kΩ from gate to GND.

## Schematic (common-anode tower, ULN2803A)

```
 5V (+) ──┬──────────┬──────────────┬──────────────┬─────────────┐
          │          │              │              │             │
      [1000µF]   ESP32 5V/VIN   MAX98357A VIN   ULN2803A      TOWER
          │                                     pin 10 (COM)   shared (+)
 GND ─────┴── GND ───┴── GND ───────┴── GND ── pin 9 (GND)       │
                                                                  │
                     ULN2803A                          light 1 ──┤
   LIGHT pin 1 ──► pin 1 (IN1)    pin 18 (OUT1) ──► light 1 (–)  │
   LIGHT pin 2 ──► pin 2 (IN2)    pin 17 (OUT2) ──► light 2 (–)  │
   LIGHT pin 3 ──► pin 3 (IN3)    pin 16 (OUT3) ──► light 3 (–)  ...
   LIGHT pin 4 ──► pin 4 (IN4)    pin 15 (OUT4) ──► light 4 (–)
   LIGHT pin 5 ──► pin 5 (IN5)    pin 14 (OUT5) ──► light 5 (–)
   LIGHT pin 6 ──► pin 6 (IN6)    pin 13 (OUT6) ──► light 6 (–)
                   pins 7–8 / 11–12 spare (tie IN7/IN8 to GND)

   MAX98357A:  BCLK ← PIN_I2S_BCLK   LRC ← PIN_I2S_LRC   DIN ← PIN_I2S_DOUT
               GAIN: leave open (9 dB), or tie to GND for 12 dB if too quiet
               SD:   leave open
               OUT+ / OUT– → speaker (do NOT connect either one to GND)

   Button:     PIN_BUTTON ── button ── GND   (internal pull-up is used)
```

## Pin map

| Signal | ESP32-C3 SuperMini | ESP32-C6 DevKitC-1 / XIAO C6 |
|---|---|---|
| Light 1–6 | GPIO 0, 1, 3, 7, 10, 20 | GPIO 0, 1, 16, 18, 22, 23 |
| I2S BCLK | GPIO 4 | GPIO 19 |
| I2S LRC/WS | GPIO 5 | GPIO 20 |
| I2S DIN | GPIO 6 | GPIO 21 |
| Button | GPIO 21 | GPIO 17 |
| Battery sense | – | GPIO 2 |

* The pins skip the chips' boot-strapping pins, so a light driver can't stop
  the board from booting.
* **XIAO C6** labels: lights = D0, D1, D6, D10, D4, D5; I2S = D8, D9, D3;
  button = D7; battery sense = D2. That uses all 11 pins.
* **XIAO C3 doesn't break out GPIO 0/1.** Use a SuperMini, or override the pins.
* A light on C3 GPIO 20 / C6 GPIO 16 may flicker for a moment at power-up
  (those are the serial pins). That's harmless.

**Wire the lights to LIGHT 1…6 in order around the tower** so the spin turns
smoothly. If it goes the wrong way or jumps, rearrange the pin order instead of
re-soldering:

```ini
[env:esp32c3]
board = esp32-c3-devkitm-1
build_flags = ${env.build_flags} '-D LIGHT_PINS=20,10,7,3,1,0'
```

A different number of lights is fine too: list as many pins as you have. Up
to 6 get smooth PWM fading; any beyond 6 just switch on/off.

## Tips

* Power the XIAO from the module's 5 V output via its **5V pin**, not 3V3,
  and leave the XIAO's own BAT pads unconnected.
* The XIAO has a diode on its 5 V input, so plugging in USB for flashing
  while the module is on is fine.
* Use **Test lights only** on the web page with the **Chase** pattern at
  ~20 RPM to check the order of each light.
