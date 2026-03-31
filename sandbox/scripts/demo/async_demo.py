"""Demonstrate how async logging protects the application hot path.

This demo benchmarks two otherwise identical logging configurations:

- synchronous file logging with an intentionally slow file handler
- async queue-based logging with the same slow file handler behind a listener

Usage:
    .venv/bin/python sandbox/scripts/demo/async_demo.py
"""

from __future__ import annotations

import argparse
import json
from logging import getLogger
import multiprocessing
from pathlib import Path
from time import perf_counter, sleep
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pkg_infra.logger import get_logger, initialize_logging_from_config  # noqa: E402


LOG_DIR = REPO_ROOT / 'sandbox' / 'scripts' / 'demo' / 'logs'
SLOW_HANDLER_CLASS = 'sandbox.scripts.demo.demo_support.SlowFileHandler'


def build_config(*, async_mode: bool, log_file: Path, delay_seconds: float) -> dict:
    """Build a standalone logging configuration for one benchmark run."""
    return {
        'settings_version': '0.0.1',
        'app': {
            'environment': 'benchmark',
            'logger': 'benchmark',
        },
        'logging': {
            'version': 1,
            'disable_existing_loggers': False,
            'file_output_format': 'text',
            'async_mode': async_mode,
            'queue_maxsize': 1000,
            'formatters': {
                'default': {'format': '%(levelname)s:%(name)s:%(message)s'},
            },
            'handlers': {
                'file': {
                    'class': SLOW_HANDLER_CLASS,
                    'formatter': 'default',
                    'filename': str(log_file),
                    'level': 'INFO',
                    'delay_seconds': delay_seconds,
                },
                'null': {
                    'class': 'logging.NullHandler',
                    'formatter': 'default',
                    'level': 'NOTSET',
                },
            },
            'loggers': {
                'default': {
                    'handlers': ['file'],
                    'level': 'INFO',
                    'propagate': False,
                },
                'benchmark': {
                    'handlers': ['file'],
                    'level': 'INFO',
                    'propagate': False,
                },
            },
            'filters': {},
            'root': {
                'level': 'WARNING',
                'handlers': [],
            },
        },
        'integrations': {},
        'packages_groups': {},
    }


def wait_for_last_record(log_file: Path, marker: str, timeout_seconds: float) -> bool:
    """Wait for the final marker to appear in the log file."""
    deadline = perf_counter() + timeout_seconds
    while perf_counter() < deadline:
        if log_file.exists() and marker in log_file.read_text(encoding='utf-8'):
            return True
        sleep(0.02)
    return False


def collect_worker_result(
    mode: str,
    *,
    records: int,
    delay_seconds: float,
) -> dict[str, object]:
    """Execute one benchmark mode and return a structured summary."""
    async_mode = mode == 'async'
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f'benchmark_{mode}.log'
    if log_file.exists():
        log_file.unlink()

    # Quiet any pre-existing root logging noise in this child process.
    getLogger().handlers.clear()

    config = build_config(
        async_mode=async_mode,
        log_file=log_file,
        delay_seconds=delay_seconds,
    )
    initialize_logging_from_config(config)
    logger = get_logger('benchmark')

    start = perf_counter()
    for index in range(records):
        logger.info('benchmark record %s', index)
    emit_elapsed = perf_counter() - start

    last_marker = f'benchmark record {records - 1}'
    delivered = wait_for_last_record(
        log_file=next(LOG_DIR.glob(f'benchmark_{mode}_*.log')),
        marker=last_marker,
        timeout_seconds=max(2.0, records * delay_seconds * 2),
    )
    total_elapsed = perf_counter() - start

    return {
        'mode': mode,
        'records': records,
        'delay_seconds': delay_seconds,
        'emit_elapsed': round(emit_elapsed, 6),
        'total_elapsed': round(total_elapsed, 6),
        'delivered': delivered,
    }


def run_worker(mode: str, *, records: int, delay_seconds: float) -> None:
    """Execute one benchmark mode and print a JSON summary."""
    print(json.dumps(
        collect_worker_result(
            mode,
            records=records,
            delay_seconds=delay_seconds,
        ),
    ))


def _benchmark_process_entry(
    send_connection: multiprocessing.connection.Connection,
    mode: str,
    records: int,
    delay_seconds: float,
) -> None:
    """Run one benchmark mode in an isolated process and send the result back."""
    try:
        payload = collect_worker_result(
            mode,
            records=records,
            delay_seconds=delay_seconds,
        )
        send_connection.send(payload)
    finally:
        send_connection.close()


def run_benchmark(*, records: int, delay_seconds: float) -> None:
    """Run sync and async workers in isolated processes and compare them."""
    results: dict[str, dict[str, object]] = {}
    context = multiprocessing.get_context('spawn')

    for mode in ('sync', 'async'):
        receive_connection, send_connection = context.Pipe(duplex=False)
        process = context.Process(
            target=_benchmark_process_entry,
            args=(send_connection, mode, records, delay_seconds),
        )
        process.start()
        send_connection.close()
        payload = receive_connection.recv()
        receive_connection.close()
        process.join()
        if process.exitcode != 0:
            raise RuntimeError(
                f'Benchmark process for mode {mode!r} failed with exit code '
                f'{process.exitcode}.',
            )
        results[mode] = payload

    sync_elapsed = float(results['sync']['emit_elapsed'])
    async_elapsed = float(results['async']['emit_elapsed'])
    improvement = sync_elapsed / async_elapsed if async_elapsed else float('inf')

    print('Async logging benchmark')
    print(f'  records: {records}')
    print(f'  simulated handler delay: {delay_seconds:.4f}s per record')
    print()
    print(f"  sync emit time : {sync_elapsed:.4f}s")
    print(f"  async emit time: {async_elapsed:.4f}s")
    print(f"  speedup on caller thread: {improvement:.2f}x")
    print()
    print('Why this matters')
    print('  - synchronous mode makes the caller pay the full file-I/O cost')
    print('  - async mode returns quickly after enqueueing the record')
    print('  - the background listener absorbs the slow handler work')


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the demo."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('sync', 'async', 'compare'), default='compare')
    parser.add_argument('--records', type=int, default=250)
    parser.add_argument('--delay-seconds', type=float, default=0.004)
    return parser.parse_args()


def main() -> None:
    """Run either a worker benchmark or the side-by-side comparison."""
    args = parse_args()
    if args.mode in {'sync', 'async'}:
        run_worker(
            args.mode,
            records=args.records,
            delay_seconds=args.delay_seconds,
        )
        return

    run_benchmark(records=args.records, delay_seconds=args.delay_seconds)


if __name__ == '__main__':
    main()
