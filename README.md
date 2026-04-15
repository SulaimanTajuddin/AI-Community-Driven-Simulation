# AI-Community-Driven-Simulation

A multi-agent community simulation where agents with distinct roles (Explorer, Guardian, Trader, Scholar, Herald) roam a 2D world, interact, exchange knowledge, form alliances, and emit events.

## Features

- **Text-based simulation** with live updates using Rich library
- **Graphical visualization** using Pygame for real-time agent movement and interactions
- **Statistical plotting** using Matplotlib to visualize simulation metrics over time

## Installation

```bash
pip install rich pygame matplotlib
```

## Usage

Run the simulation in text mode:
```bash
python Quantown.py
```

Run with graphical visualization:
```bash
python Quantown.py --visual
```

Run and generate statistics plots:
```bash
python Quantown.py --plot
```

## Options

- `--visual`: Use Pygame window for live visualization
- `--plot`: Generate and save statistics plots at the end
- `--agents`: Number of agents (default: 20)
- `--ticks`: Total ticks for text mode (default: 300)
- `--delay`: Delay per tick in text mode (default: 0.05)
- `--radius`: Interaction radius (default: 70.0)
- `--width`: World width (default: 800)
- `--height`: World height (default: 600)
