# Wiring the housing

Gut the old board completely. You only keep three things from the original:
the **light tower** (bulb/LEDs + spinning-reflector motor), the **speaker**,
and the shell. Everything runs off one **5 V wall supply** instead of batteries.

## Parts

| Part | Notes |
|---|---|
| ESP32-C3 or ESP32-C6 board | C3 SuperMini, XIAO C3/C6, or C6 DevKitC-1 |
| MAX98357A I2S amp breakout | ~3 W into 4 Ω at 5 V, drives the original speaker directly |
| Logic-level N-MOSFET | IRLB8721 / IRLZ44N (TO-220) or an AOD4184 "MOSFET trigger module" |
| Schottky diode 1N5819 (or 1N4007) | flyback protection for the motor |
| 10 kΩ + 100 Ω resistors | gate pull-down and gate resistor (skip if using a module) |
| 1000 µF ≥10 V electrolytic cap | across 5 V near the tower/amp, absorbs motor inrush |
| 5 V 3 A power supply + panel jack | USB-C (5 V-only "dumb" brick) or 5.5×2.1 mm barrel |
| Momentary push button (optional) | test/stop; can reuse the housing's original button |

## Check the tower voltage first

Look at the old battery compartment: 3 cells = 4.5 V, 4 cells = 6 V.

* **4.5 V or less** – run it straight from the 5 V rail as shown below.
* **6 V** – it will usually spin fine (slightly slower) on 5 V. Try it on the
  bench first. If it's too sluggish, use a 9–12 V supply, a buck converter
  set to 6 V for the tower, and a second buck (or the board's VIN) at 5 V
  for the electronics.

Also measure the tower's current with a multimeter on the bench. Most draw
0.3–1 A, so a 3 A supply leaves headroom for the amp and the motor's startup spike.

## Schematic

```
 5V SUPPLY (+) ──┬─────────────┬──────────────┬───────────────┐
                 │             │              │               │
             [1000µF]     ESP32 5V/VIN    MAX98357A VIN   LIGHT TOWER (+)
                 │                                            │
 5V SUPPLY (–) ──┴── GND ──────┴── GND ───────┴── GND    ┌────┤
                                                         │  1N5819
                                                         │  (stripe → +5V)
                                                         │    │
                                                    TOWER (–) ┘
                                                         │
                                                       DRAIN
   ESP32 PIN_LIGHT ──[100Ω]──┬─────────────────────── GATE   N-MOSFET
                             │                         SOURCE
                          [10kΩ]                         │
                             │                           │
                            GND ────────────────────────GND

   MAX98357A:  BCLK ← PIN_I2S_BCLK   LRC ← PIN_I2S_LRC   DIN ← PIN_I2S_DOUT
               GAIN: leave open (9 dB) – tie to GND for 12 dB if too quiet
               SD:   leave open
               OUT+ / OUT– → speaker (do NOT connect either to GND)

   Button:     PIN_BUTTON ── button ── GND   (internal pull-up is used)
```

## Pin map

| Signal | ESP32-C3 | ESP32-C6 (DevKitC-1 / XIAO C6) |
|---|---|---|
| Light MOSFET gate | GPIO 3 | GPIO 18 |
| I2S BCLK | GPIO 4 | GPIO 19 |
| I2S LRC/WS | GPIO 5 | GPIO 20 |
| I2S DIN | GPIO 6 | GPIO 21 |
| Button | GPIO 7 | GPIO 22 |

On a XIAO C3 those are D1–D5; on a XIAO C6 they are D10, D8, D9, D3, D4.
Different board? Override pins in `platformio.ini`, e.g.
`build_flags = ${env.build_flags} -D PIN_LIGHT=10`.

## Tips

* Power the ESP32 from the 5 V rail via its **5V/VIN pin**, not 3V3.
  Don't plug USB into the board while the wall supply is connected unless your
  board has a diode on its 5 V input (most SuperMini/XIAO boards do).
* Keep the motor's wires twisted and away from the antenna end of the ESP32.
* If the light flickers or the ESP32 resets when the tower kicks on, add more
  bulk capacitance or a 1 Ω resistor in series with the tower.
* Some towers have separate wires for the lamp and the motor. Tie them
  together on the MOSFET drain, or add a second MOSFET on another GPIO.
