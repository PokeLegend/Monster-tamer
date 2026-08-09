# Monster Tamer

A small monster catching, battling, and training game built with Python and Pygame.
Explore a handful of areas, catch wild monsters, battle rival trainers, level up
and evolve your team, and take on the Champion.

All creatures render as procedurally-drawn shapes (no external art assets), so the
game is 100% self-contained and free of any licensing concerns.

## Features

- **18 monsters** across 6 evolution lines (Fire, Water, Grass, Electric, Rock, Flying)
- **Turn-based battles** with a type-effectiveness chart, accuracy/PP, and status moves
- **Catching** wild monsters with capture orbs (catch chance scales with HP and species rarity)
- **Training & leveling** with an EXP system and automatic evolutions
- **4 explorable areas** connected together, with wild encounter zones and trainer battles
- **Save / Continue** system (saved to your user profile)
- A **Champion battle** at the end of Rocky Pass

## Controls

| Key            | Action                          |
|----------------|----------------------------------|
| Arrow keys / WASD | Move / navigate menus         |
| Enter / Space  | Confirm, interact, advance text |
| Esc            | Back out of a menu               |
| P or Esc       | Pause menu (Party / Save / Pokedex / Quit) |

## Playing from source

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python main.py
```

## Downloading the Windows build

Every push to `main` builds a Windows executable via GitHub Actions. Tagged
releases (e.g. `v1.0.0`) automatically publish a `MonsterTamer-Windows.zip`
to the repo's **Releases** page — grab it, unzip, and run `MonsterTamer.exe`.
No Python installation required.

## Building the .exe yourself

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name MonsterTamer --add-data "data;data" main.py
```

The executable will be in `dist/MonsterTamer.exe`.

## Publishing a new release

This repo ships with a GitHub Actions workflow (`.github/workflows/build.yml`)
that builds the Windows executable and attaches it to a GitHub Release whenever
you push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Check the **Actions** tab to watch the build, then find the download under
**Releases** once it finishes.

## Project structure

```
monster-tamer/
├── main.py                # game loop & all screens/states
├── engine/
│   ├── monster.py         # Monster class, stats, type chart, leveling
│   ├── battle.py          # turn-based battle logic
│   ├── player.py          # player party/inventory/save state
│   ├── world.py           # map loading, collision, encounters
│   ├── render.py          # procedural sprite drawing & UI helpers
│   └── save.py            # save/load to disk
├── data/
│   ├── monsters.json      # species definitions
│   ├── moves.json         # move definitions
│   └── maps.json          # area layouts, encounters, trainers
└── .github/workflows/build.yml
```

## Extending the game

- Add a new monster: add an entry to `data/monsters.json` (and moves it needs
  to `data/moves.json`).
- Add a new area: add an entry to `data/maps.json` with a `grid`, `exits`,
  `encounters`, and `trainers`, then link it from a neighboring map's `exits`.

## License

MIT — see [LICENSE](LICENSE).
