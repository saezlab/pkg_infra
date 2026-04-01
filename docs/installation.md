# Installation

## Requirements

- Python 3.10 or newer
- `pip` or another modern Python package installer

## Install from PyPI

```bash
pip install pkg_infra
```

## Install from a local checkout

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/saezlab/pkg_infra.git
cd pkg_infra
pip install -e .
```

## Install development extras

If you are working on the package itself, install the relevant extras:

```bash
pip install -e ".[docs,tests,dev]"
```

## Verify the installation

```bash
python -c "import pkg_infra; print(pkg_infra.__version__)"
```
