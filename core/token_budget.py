"""Token Budget Control — Track and enforce LLM token usage.

Provides:
  - estimate_tokens(): fast char-based token estimation (~4 chars/token)
  - TokenBudget: per-run budget tracker with iteration-level accounting
  - BudgetExceeded: raised when budget is exhausted (graceful termination)

Budget enforcement strategy:
  1. Before LLM call → estimate. If would exceed → raise BudgetExceeded.
  2. After LLM call → record actual usage from API response.
  3. Orchestrator catches BudgetExceeded → terminates run gracefully.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_TOKENS_PER_ITERATION = 8_000
DEFAULT_MAX_TOKENS_PER_RUN = 30_000

# Rough heuristic: ~4 characters per token for English text
CHARS_PER_TOKEN = 4.0


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    """Estimate token count from character length. ~4 chars/token for English."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class BudgetExceeded(Exception):
    """Raised when a token budget limit would be exceeded."""

    def __init__(self, budget_type: str, limit: int, current: int, requested: int):
        self.budget_type = budget_type
        self.limit = limit
        self.current = current
        self.requested = requested
        super().__init__(
            f"Token budget exceeded: {budget_type} "
            f"(limit={limit}, used={current}, requested={requested})"
        )


# ---------------------------------------------------------------------------
# Budget Tracker
# ---------------------------------------------------------------------------
@dataclass
class IterationUsage:
    """Token usage for a single iteration."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0


class TokenBudget:
    """Thread-safe per-run token budget tracker.

    Args:
        max_tokens_per_iteration: Soft ceiling per iteration (triggers early stop).
        max_tokens_per_run: Hard ceiling for entire run (triggers graceful exit).
    """

    def __init__(
        self,
        max_tokens_per_iteration: int = DEFAULT_MAX_TOKENS_PER_ITERATION,
        max_tokens_per_run: int = DEFAULT_MAX_TOKENS_PER_RUN,
    ) -> None:
        self.max_tokens_per_iteration = max_tokens_per_iteration
        self.max_tokens_per_run = max_tokens_per_run
        self._lock = threading.Lock()
        self._run_prompt: int = 0
        self._run_completion: int = 0
        self._run_total: int = 0
        self._run_calls: int = 0
        self._iteration_usage: Dict[int, IterationUsage] = {}
        self._current_iteration: int = 1

    def set_iteration(self, iteration: int) -> None:
        """Set current iteration for tracking."""
        with self._lock:
            self._current_iteration = iteration
            if iteration not in self._iteration_usage:
                self._iteration_usage[iteration] = IterationUsage()

    def check_budget(self, estimated_tokens: int) -> None:
        """Check if an LLM call would exceed budget. Raises BudgetExceeded if so."""
        with self._lock:
            # Check run-level budget
            if self._run_total + estimated_tokens > self.max_tokens_per_run:
                raise BudgetExceeded(
                    "run", self.max_tokens_per_run,
                    self._run_total, estimated_tokens,
                )

            # Check iteration-level budget
            iter_usage = self._iteration_usage.get(
                self._current_iteration, IterationUsage()
            )
            if iter_usage.total_tokens + estimated_tokens > self.max_tokens_per_iteration:
                raise BudgetExceeded(
                    "iteration", self.max_tokens_per_iteration,
                    iter_usage.total_tokens, estimated_tokens,
                )

    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
    ) -> None:
        """Record actual token usage from API response."""
        with self._lock:
            self._run_prompt += prompt_tokens
            self._run_completion += completion_tokens
            self._run_total += total_tokens
            self._run_calls += 1

            if self._current_iteration not in self._iteration_usage:
                self._iteration_usage[self._current_iteration] = IterationUsage()
            iu = self._iteration_usage[self._current_iteration]
            iu.prompt_tokens += prompt_tokens
            iu.completion_tokens += completion_tokens
            iu.total_tokens += total_tokens
            iu.call_count += 1

            logger.debug(
                "token_usage | iter=%d prompt=%d completion=%d total=%d run_total=%d",
                self._current_iteration, prompt_tokens,
                completion_tokens, total_tokens, self._run_total,
            )

    @property
    def run_total(self) -> int:
        with self._lock:
            return self._run_total

    @property
    def run_calls(self) -> int:
        with self._lock:
            return self._run_calls

    def iteration_total(self, iteration: int) -> int:
        with self._lock:
            iu = self._iteration_usage.get(iteration)
            return iu.total_tokens if iu else 0

    def get_iteration_summary(self, iteration: int) -> dict:
        """Return token summary for a given iteration."""
        with self._lock:
            iu = self._iteration_usage.get(iteration, IterationUsage())
            return {
                "prompt_tokens": iu.prompt_tokens,
                "completion_tokens": iu.completion_tokens,
                "total_tokens": iu.total_tokens,
                "call_count": iu.call_count,
            }

    def get_run_summary(self) -> dict:
        """Return token summary for the entire run."""
        with self._lock:
            return {
                "prompt_tokens": self._run_prompt,
                "completion_tokens": self._run_completion,
                "total_tokens": self._run_total,
                "call_count": self._run_calls,
                "max_per_iteration": self.max_tokens_per_iteration,
                "max_per_run": self.max_tokens_per_run,
            }
