import pytest

from book_monitor.retry import RetryableError, retry


class Flaky:
    """Callable that raises RetryableError until `succeed_on` (1-based), then returns "ok"."""

    def __init__(self, succeed_on: int | None = None, error: type[Exception] = RetryableError):
        self.succeed_on = succeed_on
        self.error = error
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.succeed_on is not None and self.calls >= self.succeed_on:
            return "ok"
        raise self.error(f"fail {self.calls}")


def test_persistent_failure_makes_four_calls_waits_2_4_8_and_raises_the_last_error():
    fn, sleeps = Flaky(), []
    with pytest.raises(RetryableError) as exc:
        retry(fn, retries=3, sleep=sleeps.append)
    assert fn.calls == 4
    assert sleeps == [2, 4, 8]
    assert str(exc.value) == "fail 4"


def test_success_on_third_attempt_returns_result_without_extra_waits():
    fn, sleeps = Flaky(succeed_on=3), []
    assert retry(fn, retries=3, sleep=sleeps.append) == "ok"
    assert fn.calls == 3
    assert sleeps == [2, 4]


def test_success_on_first_attempt_never_waits():
    fn, sleeps = Flaky(succeed_on=1), []
    assert retry(fn, retries=3, sleep=sleeps.append) == "ok"
    assert fn.calls == 1
    assert sleeps == []


def test_error_that_is_not_retryable_is_raised_immediately_without_retry():
    fn, sleeps = Flaky(error=ValueError), []
    with pytest.raises(ValueError, match="fail 1"):
        retry(fn, retries=3, sleep=sleeps.append)
    assert fn.calls == 1
    assert sleeps == []


def test_on_retry_receives_attempt_number_error_and_delay_before_each_wait():
    fn, events = Flaky(succeed_on=3), []
    retry(
        fn,
        retries=3,
        sleep=lambda delay: None,
        on_retry=lambda attempt, exc, delay: events.append((attempt, str(exc), delay)),
    )
    assert events == [(1, "fail 1", 2), (2, "fail 2", 4)]
