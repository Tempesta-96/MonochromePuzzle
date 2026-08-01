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

Run in a browser on localhost:

```bash
python xor_puzzle.py --web --port 8000
```

Then open `http://127.0.0.1:8000`.

## Docker

This project now includes a Docker setup that runs the current localhost web mode directly inside a container.

Files:

- [Dockerfile](./Dockerfile)
- [docker-compose.yml](./docker-compose.yml)
- [requirements.txt](./requirements.txt)
- [.dockerignore](./.dockerignore)

### Build the image

From the `MonochromePuzzle` folder:

```bash
docker build -t monochrome-puzzle .
```

### Run the game from Docker

```bash
docker run --rm -p 8000:8000 monochrome-puzzle
```

Then open `http://localhost:8000`.

### Run with Docker Compose

```bash
docker compose up --build monochrome-puzzle
```

Then open `http://localhost:8000`.

### Start from a specific level

```bash
docker run --rm -p 8000:8000 monochrome-puzzle python xor_puzzle.py --web --host 0.0.0.0 --port 8000 --level 25
```

### Print a solution from Docker

```bash
docker run --rm monochrome-puzzle python xor_puzzle.py --print-solution 25
```

### CLI mode with Docker Compose

```bash
docker compose run --rm monochrome-puzzle-cli
```

Override the CLI command if needed:

```bash
docker compose run --rm monochrome-puzzle-cli python xor_puzzle.py --print-solution 40
```

### Docker services

- `monochrome-puzzle`: runs the browser-accessible game on port `8000`
- `monochrome-puzzle-cli`: runs terminal-only commands such as `--print-solution`

### Why this setup works

The game already has a built-in `--web` mode, so the container does not need X11, VcXsrv, or noVNC. Docker just exposes the local web server from the container to your machine.

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
