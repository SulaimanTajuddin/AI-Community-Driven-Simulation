"""
AI Agent Community Simulation
==============================
A multi-agent community simulation where agents with distinct roles
(Explorer, Guardian, Trader, Scholar, Herald) roam a 2D world,
interact, exchange knowledge, form alliances, and emit events.

Run:
    pip install rich
    python agent_community_sim.py

Optional live visual (requires pygame):
    pip install pygame
    python agent_community_sim.py --visual
"""

import random
import math
import time
import argparse
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
from enum import Enum

# ── Roles ────────────────────────────────────────────────────────────────────

class Role(Enum):
    EXPLORER = "Explorer"
    GUARDIAN = "Guardian"
    TRADER   = "Trader"
    SCHOLAR  = "Scholar"
    HERALD   = "Herald"

ROLE_COLORS_ANSI = {
    Role.EXPLORER: "\033[35m",  # magenta
    Role.GUARDIAN: "\033[32m",  # green
    Role.TRADER:   "\033[31m",  # red
    Role.SCHOLAR:  "\033[34m",  # blue
    Role.HERALD:   "\033[33m",  # yellow
}
RESET = "\033[0m"

ROLE_ACTIONS = {
    Role.EXPLORER: ["scouted new territory", "mapped a resource node", "found a path"],
    Role.GUARDIAN: ["defended the cluster", "blocked an intrusion", "secured the perimeter"],
    Role.TRADER:   ["exchanged resources", "completed a trade", "negotiated a deal"],
    Role.SCHOLAR:  ["shared findings", "archived data", "published knowledge"],
    Role.HERALD:   ["broadcast news", "relayed an alert", "announced an alliance"],
}

# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class SimConfig:
    world_width:      float = 800.0
    world_height:     float = 600.0
    num_agents:       int   = 20
    interaction_radius: float = 70.0
    max_speed:        float = 2.0
    noise_factor:     float = 0.15
    message_prob:     float = 0.04
    knowledge_prob:   float = 0.015
    alliance_prob:    float = 0.008
    alliance_ttl:     int   = 120   # ticks before alliance fades
    cooldown_ticks:   int   = 20
    ticks_per_second: int   = 10    # for text mode pacing

# ── Event system ──────────────────────────────────────────────────────────────

@dataclass
class Event:
    tick:    int
    kind:    str          # "message" | "knowledge" | "alliance" | "action"
    source:  int          # agent id
    target:  Optional[int]
    detail:  str

# ── Agent ─────────────────────────────────────────────────────────────────────

@dataclass
class Agent:
    id:        int
    role:      Role
    x:         float
    y:         float
    vx:        float = field(default_factory=lambda: (random.random() - 0.5) * 1.2)
    vy:        float = field(default_factory=lambda: (random.random() - 0.5) * 1.2)
    energy:    float = field(default_factory=lambda: 50 + random.random() * 50)
    knowledge: int   = field(default_factory=lambda: random.randint(0, 10))
    allies:    set   = field(default_factory=set)
    cooldown:  int   = 0

    @property
    def name(self) -> str:
        return f"{self.role.value}#{self.id}"

    def colored_name(self) -> str:
        c = ROLE_COLORS_ANSI[self.role]
        return f"{c}{self.name}{RESET}"

    def move(self, cfg: SimConfig):
        self.x += self.vx
        self.y += self.vy

        # Bounce off walls
        if self.x < 10 or self.x > cfg.world_width - 10:
            self.vx *= -1
            self.x = max(10.0, min(cfg.world_width - 10, self.x))
        if self.y < 10 or self.y > cfg.world_height - 10:
            self.vy *= -1
            self.y = max(10.0, min(cfg.world_height - 10, self.y))

        # Random walk noise
        self.vx += (random.random() - 0.5) * cfg.noise_factor
        self.vy += (random.random() - 0.5) * cfg.noise_factor

        # Clamp speed
        speed = math.hypot(self.vx, self.vy)
        if speed > cfg.max_speed:
            self.vx = self.vx / speed * cfg.max_speed
            self.vy = self.vy / speed * cfg.max_speed

        if self.cooldown > 0:
            self.cooldown -= 1

# ── Alliance record ───────────────────────────────────────────────────────────

@dataclass
class Alliance:
    agent_a: int
    agent_b: int
    formed_at: int
    ttl: int

    def is_alive(self, tick: int) -> bool:
        return (tick - self.formed_at) < self.ttl

# ── Simulator ─────────────────────────────────────────────────────────────────

class Simulation:
    def __init__(self, cfg: SimConfig):
        self.cfg       = cfg
        self.tick      = 0
        self.agents: list[Agent] = []
        self.alliances: list[Alliance] = []
        self.events:   list[Event] = []
        self.stats = defaultdict(int)
        self._init_agents()

    def _init_agents(self):
        roles = list(Role)
        for i in range(self.cfg.num_agents):
            role = roles[i % len(roles)]
            agent = Agent(
                id=i,
                role=role,
                x=30 + random.random() * (self.cfg.world_width  - 60),
                y=30 + random.random() * (self.cfg.world_height - 60),
            )
            self.agents.append(agent)

    def _dist(self, a: Agent, b: Agent) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def _emit(self, kind: str, src: int, tgt: Optional[int], detail: str):
        self.events.append(Event(self.tick, kind, src, tgt, detail))
        if len(self.events) > 500:          # keep memory bounded
            self.events = self.events[-500:]

    def step(self):
        self.tick += 1

        # Move all agents
        for a in self.agents:
            a.move(self.cfg)

        # Interaction pass
        for i in range(len(self.agents)):
            for j in range(i + 1, len(self.agents)):
                a, b = self.agents[i], self.agents[j]
                if a.cooldown > 0 or b.cooldown > 0:
                    continue
                d = self._dist(a, b)
                if d >= self.cfg.interaction_radius:
                    continue

                rnd = random.random()

                # Generic message / action
                if rnd < self.cfg.message_prob:
                    action = random.choice(ROLE_ACTIONS[a.role])
                    detail = f"{a.name} {action} → {b.name}"
                    self._emit("message", a.id, b.id, detail)
                    self.stats["messages"] += 1
                    a.cooldown = self.cfg.cooldown_ticks
                    b.cooldown = self.cfg.cooldown_ticks

                # Knowledge transfer (Scholar amplified)
                if rnd < self.cfg.knowledge_prob or (
                    rnd < self.cfg.knowledge_prob * 3
                    and (a.role == Role.SCHOLAR or b.role == Role.SCHOLAR)
                ):
                    a.knowledge += 1
                    b.knowledge += 1
                    self.stats["knowledge"] += 1
                    self._emit("knowledge", a.id, b.id,
                               f"Knowledge transfer: {a.name} ↔ {b.name}")

                # Alliance formation
                if rnd < self.cfg.alliance_prob and b.id not in a.allies:
                    a.allies.add(b.id)
                    b.allies.add(a.id)
                    self.stats["alliances"] += 1
                    al = Alliance(a.id, b.id, self.tick, self.cfg.alliance_ttl)
                    self.alliances.append(al)
                    self._emit("alliance", a.id, b.id,
                               f"Alliance formed: {a.name} + {b.name}")

        # Expire old alliances
        self.alliances = [al for al in self.alliances if al.is_alive(self.tick)]

    def recent_events(self, n: int = 10) -> list[Event]:
        return self.events[-n:]

    def summary(self) -> dict:
        role_counts = defaultdict(int)
        for a in self.agents:
            role_counts[a.role.value] += 1
        top_scholars = sorted(self.agents, key=lambda a: a.knowledge, reverse=True)[:3]
        most_connected = sorted(self.agents, key=lambda a: len(a.allies), reverse=True)[:3]
        return {
            "tick":           self.tick,
            "agents":         len(self.agents),
            "messages":       self.stats["messages"],
            "knowledge":      self.stats["knowledge"],
            "alliances":      self.stats["alliances"],
            "active_alliances": len(self.alliances),
            "role_counts":    dict(role_counts),
            "top_scholars":   [(a.name, a.knowledge) for a in top_scholars],
            "most_connected": [(a.name, len(a.allies)) for a in most_connected],
        }

# ── Text renderer ─────────────────────────────────────────────────────────────

def run_text(sim: Simulation, total_ticks: int = 200, delay: float = 0.1):
    """Run simulation in terminal with live updates."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.live import Live
        from rich.panel import Panel
        from rich.columns import Columns
        from rich.text import Text
        HAS_RICH = True
    except ImportError:
        HAS_RICH = False

    if not HAS_RICH:
        _run_plain(sim, total_ticks, delay)
        return

    console = Console()

    def build_display():
        s = sim.summary()

        # Stats row
        stats_table = Table.grid(expand=True, padding=(0, 2))
        stats_table.add_column(justify="center")
        stats_table.add_column(justify="center")
        stats_table.add_column(justify="center")
        stats_table.add_column(justify="center")
        stats_table.add_row(
            f"[bold]Tick[/bold]\n{s['tick']}",
            f"[bold]Messages[/bold]\n{s['messages']}",
            f"[bold]Knowledge[/bold]\n{s['knowledge']}",
            f"[bold]Alliances[/bold]\n{s['alliances']} ({s['active_alliances']} active)",
        )

        # Role counts
        role_str = "  ".join(
            f"[magenta]Explorer[/magenta]:{s['role_counts'].get('Explorer',0)}"
            f"  [green]Guardian[/green]:{s['role_counts'].get('Guardian',0)}"
            f"  [red]Trader[/red]:{s['role_counts'].get('Trader',0)}"
            f"  [blue]Scholar[/blue]:{s['role_counts'].get('Scholar',0)}"
            f"  [yellow]Herald[/yellow]:{s['role_counts'].get('Herald',0)}"
            .split("  ")
        )

        # Recent events
        evts = sim.recent_events(12)
        evt_lines = "\n".join(
            f"[dim][T{e.tick}][/dim] {e.detail}" for e in reversed(evts)
        ) or "[dim]No events yet…[/dim]"

        # Top agents
        scholars = "  ".join(f"{n}({k})" for n, k in s['top_scholars'])
        connected = "  ".join(f"{n}({c})" for n, c in s['most_connected'])

        panel = Panel(
            f"{stats_table}\n\n"
            f"[bold]Roles:[/bold]  {role_str}\n\n"
            f"[bold]Top scholars:[/bold]  {scholars}\n"
            f"[bold]Most connected:[/bold]  {connected}\n\n"
            f"[bold]Recent activity:[/bold]\n{evt_lines}",
            title="[bold]AI Agent Community Simulation[/bold]",
            subtitle=f"[dim]{sim.cfg.num_agents} agents · {sim.cfg.interaction_radius:.0f}px radius[/dim]",
        )
        return panel

    with Live(build_display(), console=console, refresh_per_second=10) as live:
        for _ in range(total_ticks):
            sim.step()
            live.update(build_display())
            time.sleep(delay)

    console.print("\n[bold green]Simulation complete.[/bold green]")
    console.print_json(__import__("json").dumps(sim.summary(), indent=2))


def _run_plain(sim: Simulation, total_ticks: int, delay: float):
    """Fallback plain-text runner (no rich dependency)."""
    for t in range(total_ticks):
        sim.step()
        if t % 20 == 0:
            s = sim.summary()
            print(f"[T{s['tick']:04d}] agents={s['agents']} "
                  f"msgs={s['messages']} knowledge={s['knowledge']} "
                  f"alliances={s['alliances']}")
            for e in sim.recent_events(3):
                print(f"       {e.detail}")
        time.sleep(delay)
    print("\nFinal summary:", sim.summary())

# ── Pygame visual renderer ────────────────────────────────────────────────────

PYGAME_ROLE_COLORS = {
    Role.EXPLORER: (127, 119, 221),
    Role.GUARDIAN: (29,  158, 117),
    Role.TRADER:   (216,  90,  48),
    Role.SCHOLAR:  (55,  138, 221),
    Role.HERALD:   (186, 117,  23),
}

def run_visual(sim: Simulation):
    """Run simulation with a pygame window."""
    try:
        import pygame
    except ImportError:
        print("pygame not installed. Run:  pip install pygame")
        print("Falling back to text mode.")
        run_text(sim, total_ticks=300, delay=0.05)
        return

    pygame.init()
    W, H = int(sim.cfg.world_width), int(sim.cfg.world_height)
    screen = pygame.display.set_mode((W, H + 80))
    pygame.display.set_caption("AI Agent Community Simulation")
    clock  = pygame.time.Clock()
    font_s = pygame.font.SysFont("monospace", 11)
    font_m = pygame.font.SysFont("monospace", 13)

    running = True
    paused  = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    sim.__init__(sim.cfg)

        if not paused:
            sim.step()

        # ── Draw world ──────────────────────────────────────────────────
        screen.fill((245, 245, 242))

        # Alliance lines (fading)
        for al in sim.alliances:
            a = next((x for x in sim.agents if x.id == al.agent_a), None)
            b = next((x for x in sim.agents if x.id == al.agent_b), None)
            if a and b:
                age = sim.tick - al.formed_at
                alpha = max(0, 255 - int(age / al.ttl * 255))
                color = (127, 119, 221, alpha)
                surf = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.line(surf, color,
                                 (int(a.x), int(a.y)), (int(b.x), int(b.y)), 1)
                screen.blit(surf, (0, 0))

        # Agents
        radius = int(sim.cfg.interaction_radius)
        for a in sim.agents:
            col = PYGAME_ROLE_COLORS[a.role]
            # Interaction radius (faint)
            pygame.draw.circle(screen, (*col, 15),
                               (int(a.x), int(a.y)), radius, 1)
            # Agent dot
            pygame.draw.circle(screen, col, (int(a.x), int(a.y)), 7)
            pygame.draw.circle(screen, (255, 255, 255), (int(a.x), int(a.y)), 7, 2)
            # Knowledge halo
            if a.knowledge > 15:
                pygame.draw.circle(screen, col, (int(a.x), int(a.y)), 11, 1)
            # Label
            lbl = font_s.render(f"{a.role.value[0]}{a.id}", True, (80, 80, 80))
            screen.blit(lbl, (int(a.x) + 9, int(a.y) - 7))

        # ── HUD strip ───────────────────────────────────────────────────
        pygame.draw.rect(screen, (235, 233, 228), (0, H, W, 80))
        s = sim.summary()
        hud = (f"T={s['tick']}  Agents={s['agents']}  "
               f"Msgs={s['messages']}  Knowledge={s['knowledge']}  "
               f"Alliances={s['alliances']} ({s['active_alliances']} active)"
               f"   [SPACE=pause  R=reset]")
        screen.blit(font_m.render(hud, True, (80, 80, 80)), (10, H + 8))

        evts = sim.recent_events(2)
        for i, e in enumerate(reversed(evts)):
            screen.blit(font_s.render(e.detail[:120], True, (120, 120, 120)),
                        (10, H + 34 + i * 18))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Agent Community Simulation")
    parser.add_argument("--visual",    action="store_true", help="Use pygame window")
    parser.add_argument("--agents",    type=int,   default=20,   help="Number of agents")
    parser.add_argument("--ticks",     type=int,   default=300,  help="Total ticks (text mode)")
    parser.add_argument("--delay",     type=float, default=0.05, help="Delay per tick (text mode)")
    parser.add_argument("--radius",    type=float, default=70.0, help="Interaction radius")
    parser.add_argument("--width",     type=float, default=800,  help="World width")
    parser.add_argument("--height",    type=float, default=600,  help="World height")
    args = parser.parse_args()

    cfg = SimConfig(
        num_agents=args.agents,
        interaction_radius=args.radius,
        world_width=args.width,
        world_height=args.height,
    )
    sim = Simulation(cfg)

    print(f"Starting simulation: {cfg.num_agents} agents, "
          f"world {cfg.world_width}×{cfg.world_height}, "
          f"radius={cfg.interaction_radius}")

    if args.visual:
        run_visual(sim)
    else:
        run_text(sim, total_ticks=args.ticks, delay=args.delay)


if __name__ == "__main__":
    main()
