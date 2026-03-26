import time
import threading

from pkg_infra import get_session

__all__ = [
    'log_spammer',
    'main',
]


def log_spammer(thread_id: int, n: int, delay: float = 0.0) -> None:
    """Log multiple messages from a thread for async logging demo.

    Args:
        thread_id (int): The thread identifier.
        n (int): Number of log messages to emit.
        delay (float, optional): Delay in seconds between messages. Defaults to 0.0.
    """
    session = get_session(workspace='scripts/demo', include_location=False)
    log = session.session_logger
    if log is None:
        raise RuntimeError('Session logger is not initialized.')
    for i in range(n):
        log.info(f'Thread {thread_id} message {i + 1}')
        if delay:
            time.sleep(delay)


def main() -> None:
    """Main entry point for the async logging CLI demo application.

    This function initializes logging, starts multiple threads to generate log messages,
    and demonstrates thread-safe async logging and log rotation.
    """
    get_session(workspace='scripts/demo', include_location=False)
    num_threads = 5
    messages_per_thread = 100
    threads = []
    for t in range(num_threads):
        th = threading.Thread(
            target=log_spammer, args=(t + 1, messages_per_thread)
        )
        threads.append(th)
        th.start()
    for th in threads:
        th.join()
    print(
        f'Logged {num_threads * messages_per_thread} messages from {num_threads} threads.'
    )


if __name__ == '__main__':
    main()
