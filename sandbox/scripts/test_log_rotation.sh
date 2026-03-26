#!/bin/bash
set -e

# Create a temp directory for logs
TMPDIR=$(mktemp -d)
echo $TMPDIR
cd "$TMPDIR"


# Write a Python script using pkg_infra.logger

cat > log_rotate_test.py <<'PY'
import os
from pkg_infra.logger import initialize_logging_from_config, get_logger

config = {
    "logging": {
        "version": 1,
        "formatters": {
            "simple": {"format": "%(levelname)s | %(message)s"}
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "test.log",
                "maxBytes": 1024,  # 1 KB for quick rotation
                "backupCount": 2,
                "formatter": "simple"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["file"]
        }
    }
}

initialize_logging_from_config(config)
logger = get_logger("root")  # root logger

# Acceptance criteria verification
results = []

# 1. Logger uses the log level specified in the config
expected_level = 20  # INFO
actual_level = logger.level
results.append((actual_level == expected_level, f"Logger level is INFO (20): {actual_level == expected_level}"))

# 2. Root logger’s level is correctly applied
results.append((logger.name == "root", f"Logger is root: {logger.name == 'root'}"))

# 3. Log file is created
for i in range(2000):
    logger.debug(f"DEBUG line {i}")
    logger.info(f"INFO line {i}")
    logger.warning(f"WARNING line {i}")

log_files = [f for f in os.listdir('.') if f.startswith('test_') or f == 'test.log']
log_file_exists = any(f.endswith('.log') for f in log_files)
results.append((log_file_exists, f"Log file created: {log_file_exists}"))

# 4. Only INFO and higher messages are present
found_debug = False
found_info = False
found_warning = False
for fname in log_files:
    if not fname.endswith('.log'):
        continue
    with open(fname) as f:
        content = f.read()
        if "DEBUG line" in content:
            found_debug = True
        if "INFO line" in content:
            found_info = True
        if "WARNING line" in content:
            found_warning = True
results.append((not found_debug, f"DEBUG messages filtered: {not found_debug}"))
results.append((found_info, f"INFO messages present: {found_info}"))
results.append((found_warning, f"WARNING messages present: {found_warning}"))

# 5. Print results
print("\nACCEPTANCE CRITERIA RESULTS:")
for passed, msg in results:
    print(f"[{'PASS' if passed else 'FAIL'}] {msg}")
PY


python3 log_rotate_test.py

# Show the log files created
ls -lh test_*.log