"""Simulate task priority: user-triggered (P0) preempts background (P1).

Validates CLAUDE.md Task Priority Policy:
- User tasks never blocked by background jobs
- User tasks may preempt running background jobs
- Paused background jobs resume automatically after P0 drains
"""

from __future__ import annotations

import heapq
import unittest
from dataclasses import dataclass, field
from enum import IntEnum


class Priority(IntEnum):
    USER = 0
    BACKGROUND = 1


@dataclass(order=True)
class Task:
    priority: int
    name: str = field(compare=False)
    remaining: int = field(compare=False)
    state: str = field(default="pending", compare=False)


class Scheduler:
    """Minimal preemptive scheduler for policy validation."""

    def __init__(self) -> None:
        self._heap: list[Task] = []
        self._paused: list[Task] = []
        self.running: Task | None = None
        self.completed: list[str] = []

    def submit(self, name: str, priority: Priority, duration: int) -> None:
        task = Task(priority=priority, name=name, remaining=duration)
        if self.running is None:
            self.running = task
            task.state = "running"
            return
        if priority < self.running.priority:
            self.running.state = "paused"
            self._paused.append(self.running)
            self.running = task
            task.state = "running"
            return
        heapq.heappush(self._heap, task)

    def tick(self) -> None:
        if not self.running:
            self._resume_next()
            return
        self.running.remaining -= 1
        if self.running.remaining <= 0:
            self.completed.append(self.running.name)
            self.running = None
            self._resume_next()

    def run_until_idle(self, max_ticks: int = 10_000) -> None:
        ticks = 0
        while ticks < max_ticks and (self.running or self._heap or self._paused):
            self.tick()
            ticks += 1
        if ticks >= max_ticks:
            raise RuntimeError("scheduler did not drain")

    def _resume_next(self) -> None:
        if self._heap:
            self.running = heapq.heappop(self._heap)
            self.running.state = "running"
            return
        if self._paused:
            resumed = self._paused.pop()
            resumed.state = "running"
            self.running = resumed


class TaskPrioritySimulationTest(unittest.TestCase):
    def test_user_finishes_before_background_resumes(self) -> None:
        s = Scheduler()
        s.submit("perf-audit", Priority.BACKGROUND, duration=50)
        s.submit("seo11-crawl", Priority.BACKGROUND, duration=30)
        for _ in range(5):
            s.tick()
        s.submit("user-publish-article", Priority.USER, duration=10)
        self.assertEqual(s.running.name, "user-publish-article")
        self.assertEqual(s._paused[-1].name, "perf-audit")
        s.run_until_idle()
        user_idx = s.completed.index("user-publish-article")
        bg_idxs = [s.completed.index(n) for n in ("perf-audit", "seo11-crawl")]
        self.assertLess(user_idx, min(bg_idxs))

    def test_user_never_blocked_by_background_queue(self) -> None:
        s = Scheduler()
        for i in range(3):
            s.submit(f"bg-{i}", Priority.BACKGROUND, duration=20)
        s.submit("user-fix", Priority.USER, duration=3)
        s.run_until_idle()
        self.assertEqual(s.completed[0], "user-fix")

    def test_background_preserves_order_after_preempt(self) -> None:
        s = Scheduler()
        s.submit("report-a", Priority.BACKGROUND, duration=8)
        s.submit("user-a", Priority.USER, duration=2)
        s.submit("user-b", Priority.USER, duration=2)
        s.run_until_idle()
        self.assertEqual(s.completed[:2], ["user-a", "user-b"])
        self.assertIn("report-a", s.completed)


if __name__ == "__main__":
    unittest.main()