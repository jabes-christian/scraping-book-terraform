import time
from collections.abc import Callable


class RetryableError(Exception):
    pass


def retry[T](
    fn: Callable[[], T],
    retries: int,
    base_delay: float = 2,
    on_retry: Callable[[int, RetryableError, float], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except RetryableError as exc:
            if attempt == retries:
                raise
            delay = base_delay * 2**attempt
            attempt += 1
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            sleep(delay)
