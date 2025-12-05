#!/usr/bin/env python3
"""
Agent0 CLI Monitor - Real-time monitoring for training runs.

Provides a terminal-based dashboard for monitoring:
- Training progress and metrics
- System resource usage
- Recent trajectories
- Live log streaming
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Terminal control
CLEAR_SCREEN = '\033[2J\033[H'
HIDE_CURSOR = '\033[?25l'
SHOW_CURSOR = '\033[?25h'


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def get_terminal_size():
    """Get terminal dimensions."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


class TrajectoryWatcher:
    """Watch trajectory file for updates."""

    def __init__(self, path: Path):
        self.path = path
        self.last_pos = 0
        self.last_mtime = 0
        self.trajectories: List[Dict] = []

    def check_updates(self) -> List[Dict]:
        """Check for new trajectories."""
        if not self.path.exists():
            return []

        try:
            mtime = self.path.stat().st_mtime
            if mtime <= self.last_mtime:
                return []

            new_trajs = []
            with self.path.open('r') as f:
                f.seek(self.last_pos)
                for line in f:
                    try:
                        traj = json.loads(line.strip())
                        new_trajs.append(traj)
                        self.trajectories.append(traj)
                    except json.JSONDecodeError:
                        continue
                self.last_pos = f.tell()

            self.last_mtime = mtime

            # Keep only last 100 trajectories in memory
            if len(self.trajectories) > 100:
                self.trajectories = self.trajectories[-100:]

            return new_trajs
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Calculate statistics from trajectories."""
        if not self.trajectories:
            return {
                'total': 0,
                'successes': 0,
                'success_rate': 0.0,
                'avg_reward': 0.0,
                'domains': {},
            }

        successes = sum(1 for t in self.trajectories if t.get('success', False))
        total_reward = sum(t.get('reward', {}).get('total', 0.0) for t in self.trajectories)

        domains: Dict[str, Dict[str, int]] = {}
        for t in self.trajectories:
            domain = t.get('task', {}).get('domain', 'unknown')
            if domain not in domains:
                domains[domain] = {'total': 0, 'success': 0}
            domains[domain]['total'] += 1
            if t.get('success', False):
                domains[domain]['success'] += 1

        return {
            'total': len(self.trajectories),
            'successes': successes,
            'success_rate': successes / len(self.trajectories) if self.trajectories else 0.0,
            'avg_reward': total_reward / len(self.trajectories) if self.trajectories else 0.0,
            'domains': domains,
        }


def draw_progress_bar(value: float, width: int = 20, fill: str = '█', empty: str = '░') -> str:
    """Draw a progress bar."""
    filled = int(width * value)
    return fill * filled + empty * (width - filled)


def draw_sparkline(values: List[float], width: int = 20) -> str:
    """Draw a sparkline chart."""
    if not values:
        return ' ' * width

    chars = ' ▁▂▃▄▅▆▇█'
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val if max_val != min_val else 1

    # Sample values if too many
    if len(values) > width:
        step = len(values) / width
        values = [values[int(i * step)] for i in range(width)]
    elif len(values) < width:
        values = values + [values[-1]] * (width - len(values))

    sparkline = ''
    for v in values:
        idx = int((v - min_val) / range_val * (len(chars) - 1))
        sparkline += chars[idx]

    return sparkline


class Monitor:
    """Terminal-based monitoring dashboard."""

    def __init__(self, runs_dir: Path = Path('./runs')):
        self.runs_dir = runs_dir
        self.watcher = TrajectoryWatcher(runs_dir / 'trajectories.jsonl')
        self.start_time = time.time()
        self.reward_history: List[float] = []
        self.success_history: List[float] = []

    def render(self) -> str:
        """Render the dashboard."""
        width, height = get_terminal_size()

        # Check for updates
        new_trajs = self.watcher.check_updates()
        for t in new_trajs:
            self.reward_history.append(t.get('reward', {}).get('total', 0.0))
            self.success_history.append(1.0 if t.get('success', False) else 0.0)

        # Keep history bounded
        self.reward_history = self.reward_history[-50:]
        self.success_history = self.success_history[-50:]

        stats = self.watcher.get_stats()
        elapsed = time.time() - self.start_time

        lines = []

        # Header
        lines.append(f"{Colors.CYAN}{'═' * width}{Colors.ENDC}")
        title = "Agent0 Monitor"
        padding = (width - len(title)) // 2
        lines.append(f"{' ' * padding}{Colors.BOLD}{Colors.CYAN}{title}{Colors.ENDC}")
        lines.append(f"{Colors.CYAN}{'═' * width}{Colors.ENDC}")
        lines.append('')

        # Status line
        now = datetime.now().strftime('%H:%M:%S')
        elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
        status = f"  {Colors.DIM}Time: {now} | Elapsed: {elapsed_str} | Tasks: {stats['total']}{Colors.ENDC}"
        lines.append(status)
        lines.append('')

        # Main metrics
        lines.append(f"  {Colors.BOLD}Metrics{Colors.ENDC}")
        lines.append(f"  {'─' * 40}")

        # Success rate with bar
        sr = stats['success_rate']
        sr_color = Colors.GREEN if sr >= 0.5 else Colors.YELLOW if sr >= 0.3 else Colors.RED
        sr_bar = draw_progress_bar(sr, 20)
        lines.append(f"  Success Rate: {sr_color}{sr_bar}{Colors.ENDC} {sr:.1%}")

        # Average reward
        avg_r = stats['avg_reward']
        r_color = Colors.GREEN if avg_r > 0 else Colors.RED
        lines.append(f"  Avg Reward:   {r_color}{avg_r:+.3f}{Colors.ENDC}")

        # Reward trend
        if self.reward_history:
            sparkline = draw_sparkline(self.reward_history, 30)
            lines.append(f"  Reward Trend: {Colors.CYAN}{sparkline}{Colors.ENDC}")

        lines.append('')

        # Per-domain stats
        if stats['domains']:
            lines.append(f"  {Colors.BOLD}Per-Domain{Colors.ENDC}")
            lines.append(f"  {'─' * 40}")

            for domain, d_stats in stats['domains'].items():
                d_sr = d_stats['success'] / d_stats['total'] if d_stats['total'] > 0 else 0
                d_color = Colors.GREEN if d_sr >= 0.5 else Colors.YELLOW if d_sr >= 0.3 else Colors.RED
                d_bar = draw_progress_bar(d_sr, 15)
                lines.append(f"  {domain.capitalize():10} {d_color}{d_bar}{Colors.ENDC} {d_stats['success']}/{d_stats['total']} ({d_sr:.0%})")

            lines.append('')

        # Recent trajectories
        lines.append(f"  {Colors.BOLD}Recent Tasks{Colors.ENDC}")
        lines.append(f"  {'─' * 40}")

        recent = self.watcher.trajectories[-5:] if self.watcher.trajectories else []
        for t in reversed(recent):
            success = t.get('success', False)
            icon = f"{Colors.GREEN}✓{Colors.ENDC}" if success else f"{Colors.RED}✗{Colors.ENDC}"
            domain = t.get('task', {}).get('domain', '?')[:4]
            prompt = t.get('task', {}).get('prompt', '')[:40]
            reward = t.get('reward', {}).get('total', 0.0)
            lines.append(f"  {icon} [{domain}] {prompt}... {Colors.DIM}({reward:+.2f}){Colors.ENDC}")

        if not recent:
            lines.append(f"  {Colors.DIM}No tasks yet...{Colors.ENDC}")

        lines.append('')

        # Footer
        lines.append(f"{Colors.DIM}  Press Ctrl+C to exit{Colors.ENDC}")
        lines.append(f"{Colors.CYAN}{'═' * width}{Colors.ENDC}")

        return '\n'.join(lines)

    def run(self, refresh_rate: float = 1.0):
        """Run the monitor loop."""
        print(HIDE_CURSOR, end='')
        try:
            while True:
                print(CLEAR_SCREEN, end='')
                print(self.render())
                time.sleep(refresh_rate)
        except KeyboardInterrupt:
            pass
        finally:
            print(SHOW_CURSOR, end='')
            print(f"\n{Colors.DIM}Monitor stopped{Colors.ENDC}")


def main():
    """Run the monitor."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent0 training monitor")
    parser.add_argument('--runs-dir', type=Path, default=Path('./runs'),
                       help='Directory containing training runs')
    parser.add_argument('--refresh', type=float, default=1.0,
                       help='Refresh rate in seconds')

    args = parser.parse_args()

    monitor = Monitor(args.runs_dir)
    monitor.run(args.refresh)


if __name__ == '__main__':
    main()
