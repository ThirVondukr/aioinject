import dataclasses
import functools
import statistics
from collections.abc import Sequence
from datetime import timedelta


@dataclasses.dataclass
class BenchmarkResult:
    name: str
    iterations: int
    durations: Sequence[timedelta] = dataclasses.field(repr=False)

    @functools.cached_property
    def durations_sec(self) -> Sequence[float]:
        return sorted(t.total_seconds() for t in self.durations)

    @property
    def mean(self) -> timedelta:
        return timedelta(seconds=statistics.mean(self.durations_sec))

    @property
    def median(self) -> timedelta:
        return timedelta(seconds=statistics.median(self.durations_sec))

    def percentile(self, perc: float) -> timedelta:
        index = int(len(self.durations_sec) * perc)
        return timedelta(seconds=self.durations_sec[index])
