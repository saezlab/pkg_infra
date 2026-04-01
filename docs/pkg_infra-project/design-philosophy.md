# Design Philosophy

## Build on standard tools

The project exists to reduce custom infrastructure code, not to introduce a new
parallel stack. The package deliberately builds on established Python
components, especially the standard `logging` library, and adds only the small
layer needed to make those tools work consistently across the ecosystem.

## Prefer shared conventions over local reinvention

Multiple Saezlab packages need similar runtime behavior. Instead of each
project handling logging, config loading, and session metadata differently,
`pkg_infra` centralizes those concerns so teams can share one predictable model.

## Keep configuration explicit

Configuration is expected to come from YAML files with a defined schema and a
clear merge order. This keeps overrides understandable and reduces ambiguity
when projects run in different environments.

## Support the ecosystem without overfitting it

The package includes concepts such as integrations and package groups because
they reflect the real needs of the surrounding software ecosystem. At the same
time, the implementation aims to stay lightweight and readable so it remains
maintainable over time.
