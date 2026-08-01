# MonochromePuzzle

`MonochromePuzzle` is a small Pygame puzzle game built around XOR overlap logic:

- black + black = white
- black + white = black

The goal is to drag the available pieces onto the play grid until the resulting pattern matches the target preview.

## Gameplay

Each level generates:

- a target monochrome pattern
- a set of puzzle pieces
- a hidden valid placement for every piece

When two black cells overlap, they cancel out and become white. Because of that, solving a level is not just about filling space. You need to think about how pieces interact with each other.

## Features

- Procedurally generated levels from `0` to `100`
- Increasing difficulty through larger grids and more pieces
- Drag-and-drop piece placement with grid snapping
- XOR-based overlap behavior
- Progressive hint system
- Level selection overlay
- Dynamic screen sizing so the available pieces fit more reliably

## Controls

- `Mouse drag`: move pieces
- `HINT`: show the next unresolved piece placement
- `LEVELS`: open the level picker
- `RESET` or `R`: restart the current level
- `S`: show or hide the full solution overlay
- `◀` / `▶` or `Left` / `Right`: previous or next level
- `ESC`: close overlays or quit

## Hints

The hint system is progressive:

- The first hint shows where the first unresolved piece should go
- After that piece is correctly placed, the next hint advances to the next unresolved piece
- Repeating this process can guide the player through the full solution

## Project Structure

The project has been modularized into smaller files:

- [xor_puzzle.py](./xor_puzzle.py): entry point and CLI startup
- [game.py](./game.py): main game loop, input handling, and screen state
- [generation.py](./generation.py): procedural level generation and grid computation
- [rendering.py](./rendering.py): drawing helpers, tray layout, and overlays
- [ui.py](./ui.py): reusable UI helpers like buttons and text drawing
- [models.py](./models.py): core data models such as `Piece`
- [constants.py](./constants.py): colors, sizing, and shared layout constants

## Requirements

- Python 3.12+
- `pygame 2.6.1` or compatible

Install Pygame if needed:

```bash
pip install pygame
```

## Run the Game

From the `MonochromePuzzle` folder:

```bash
python xor_puzzle.py
```

Start from a specific level:

```bash
python xor_puzzle.py --level 25
```

Print a generated solution in the terminal:

```bash
python xor_puzzle.py --print-solution 25
```

## Docker

This project includes a Docker setup for running the game or CLI tools inside a container.

Files added for Docker:

- [Dockerfile](./Dockerfile)
- [docker-compose.yml](./docker-compose.yml)
- [requirements.txt](./requirements.txt)
- [.dockerignore](./.dockerignore)

### Build the image

From the `MonochromePuzzle` folder:

```bash
docker build -t monochrome-puzzle .
```

### Run the GUI container

```bash
docker run --rm -it monochrome-puzzle
```

### Run the GUI container with Docker Compose

```bash
docker compose up --build monochrome-puzzle
```

### Run a specific level

```bash
docker run --rm -it monochrome-puzzle python xor_puzzle.py --level 25
```

### Print a solution from Docker

```bash
docker run --rm monochrome-puzzle python xor_puzzle.py --print-solution 25
```

### Run CLI mode with Docker Compose

This mode does not need a desktop display:

```bash
docker compose run --rm monochrome-puzzle-cli
```

You can also override the command:

```bash
docker compose run --rm monochrome-puzzle-cli python xor_puzzle.py --print-solution 40
```

### Display setup for Pygame

`MonochromePuzzle` is a GUI app, so the container needs access to a display server.

The included `docker-compose.yml` is now split into two use cases:

- `monochrome-puzzle`: GUI mode
- `monochrome-puzzle-cli`: headless terminal mode

### Windows with Docker Desktop and VcXsrv

This is the most practical setup if you are running Docker containers on Windows and want the Pygame window to appear on your desktop.

1. Install and start `VcXsrv`.
2. Launch it with:
   - Multiple windows
   - Start no client
   - Disable access control
3. Allow `VcXsrv` through Windows Defender Firewall on private networks.
4. In PowerShell, run:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
docker compose up --build monochrome-puzzle
```

If you prefer plain `docker run`:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
docker run --rm -it -e DISPLAY=$env:DISPLAY monochrome-puzzle
```

### Windows with WSLg

If your Docker workflow is inside WSL with WSLg enabled, your Linux GUI stack may already provide a display. In that case, check your current `DISPLAY` value first:

```bash
echo $DISPLAY
```

Then pass that value through:

```bash
DISPLAY=$DISPLAY docker compose up --build monochrome-puzzle
```

### If the window does not appear

Try these checks:

- Make sure `VcXsrv` is running before you start the container.
- Make sure Windows Firewall is not blocking the X server.
- Keep `DISPLAY=host.docker.internal:0.0` for Docker Desktop on Windows.
- Use `monochrome-puzzle-cli` first to confirm the container itself is healthy.

### Verify X11 before launching the game

If Docker builds successfully but the game window still does not appear, test the display connection separately from Pygame.

First rebuild so the diagnostic tools are available:

```powershell
docker compose build --no-cache monochrome-puzzle
```

Then check whether the container can reach your Windows X server:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
docker compose run --rm monochrome-puzzle xdpyinfo
```

If that works, try a tiny test window:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
docker compose run --rm monochrome-puzzle xclock
```

How to read the result:

- If `xdpyinfo` fails, the issue is the X server connection, not Pygame.
- If `xclock` opens, the container-to-Windows display path is working.
- If both succeed but the game still fails, the remaining issue is SDL/Pygame-specific.

### Recommended troubleshooting order on Windows

1. Start `VcXsrv` with access control disabled.
2. Set the display in PowerShell:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
```

3. Test the X connection:

```powershell
docker compose run --rm monochrome-puzzle xdpyinfo
```

4. Test a basic X window:

```powershell
docker compose run --rm monochrome-puzzle xclock
```

5. Start the game:

```powershell
docker compose up monochrome-puzzle
```

### Environment variables you can tune

- `DISPLAY`: where the GUI window should be forwarded
- `SDL_AUDIODRIVER`: defaults to `dummy` to avoid audio-device errors in containers

Examples:

```bash
docker compose run --rm -e DISPLAY=host.docker.internal:0.0 monochrome-puzzle
```

```bash
docker compose run --rm -e SDL_VIDEODRIVER=dummy monochrome-puzzle-cli
```

### Quick recommendation

For your environment, start with this on Windows:

```powershell
$env:DISPLAY="host.docker.internal:0.0"
docker compose up --build monochrome-puzzle
```

If that still does not show a Pygame window, use `VcXsrv` and verify that access control is disabled.

## Puzzle Design Notes

This project mixes several kinds of player skill:

- spatial reasoning
- observation
- planning
- pattern interpretation
- experimentation

Because the board uses XOR instead of normal stacking, the best move is often counterintuitive. A piece that seems to “erase” part of the board can still be the correct move.

## Future Improvements

Possible next steps for the project:

- save player progress across sessions
- track solved levels
- add animations and sound
- improve piece selection feedback for dense overlaps
- add handcrafted challenge levels alongside generated ones
- add other games observation, memory, spatial, creativity, interpretation, calculation
