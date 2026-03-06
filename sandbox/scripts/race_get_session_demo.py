"""Demonstrate potential race conditions in pkg_infra.session.get_session().

This script widens the initialization window by monkeypatching
`pkg_infra.session._get_configuration()` to sleep. It then launches two threads
that call `get_session()` at the same time and reports how often both threads
enter the initialization path.

Usage:
    .venv/bin/python sandbox/scripts/race_get_session_demo.py
"""

from __future__ import annotations

import time
import threading

import pkg_infra.session as session_module


def run_trial() -> tuple[int, int]:
    """Run one concurrent initialization attempt.

    Returns:
        tuple[int, int]:
            - Number of times `_get_configuration()` was called.
            - Number of unique session object ids returned to worker threads.
    """
    session_module._current_session = None
    results: list[int] = []
    counter = {'init_calls': 0}
    barrier = threading.Barrier(2)

    original_get_configuration = session_module._get_configuration

    def slow_get_configuration() -> object:
        counter['init_calls'] += 1
        time.sleep(0.2)
        return original_get_configuration()

    session_module._get_configuration = slow_get_configuration

    try:

        def worker() -> None:
            barrier.wait()
            sess = session_module.get_session('.', include_location=False)
            results.append(id(sess))

        t1 = threading.Thread(target=worker, name='race-worker-1')
        t2 = threading.Thread(target=worker, name='race-worker-2')
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    finally:
        session_module._get_configuration = original_get_configuration

    return counter['init_calls'], len(set(results))


def main() -> None:
    """Execute multiple trials and print a concise race summary."""
    trials = 50
    races_detected = 0
    double_init_trials = 0

    for _ in range(trials):
        init_calls, unique_sessions = run_trial()
        if init_calls > 1:
            double_init_trials += 1
        if unique_sessions > 1:
            races_detected += 1

    print(f'Trials: {trials}')
    print(
        f'Trials with double initialization path entered: {double_init_trials}'
    )
    print(f'Trials with >1 unique session object returned: {races_detected}')
    print(
        'Note: double initialization is already a race, even if final singleton id matches.'
    )


if __name__ == '__main__':
    main()
