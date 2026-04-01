## Description

The `config` module handles configuration discovery, loading, merging, and
validation preparation for `pkg_infra`.

## Main Components

- `ConfigLoader`: Main loader for resolving and merging config files
- `resolve_config_paths`: Compute standard config locations
- `read_package_default`: Load the packaged baseline YAML
- `merge_configs`: Merge config fragments in precedence order

---

::: pkg_infra.config
