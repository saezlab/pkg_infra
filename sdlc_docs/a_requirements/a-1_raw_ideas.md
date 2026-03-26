# Project Context

## 1. Project Overview
**Project Name:** Python Package Infrastructure (`pkg_infra`).

**Purpose:** Provide standardized logging, config handling, and session management for a set of Python packages (ecosystem) to replace ad-hoc solutions.  

**Scope:** Covers config loading, logging setup, session management, ecosystem registration, and optional advanced features like async logging. 

**Key Deliverables:** 
- A Python package called `pkg_infra`.
- Project documentation
    - Code documentation
    - Internal Software Development Life Cycle documentation.
- Demo folder with script to verify functionalities
- YAML templates

---

## 2. Rationale

Our architecture at `Saezlab` consists of a number of Python packages working together. These packages require some common technical functionalities, such as logging or config handling, which are provided in well established solutions such as the logging module of Python standard library. In the past, we relied on our own implementations instead of the established solutions. In a previous attempt we intended to share these implementations across the packages, and we created the `pypath-common` package for this. `pypath-common` came with minimal changes, it was mostly reorganization of existing code, and aimed for a working—but not optimal and future proof—solution asap. To address this shortcoming, we should migrate to standard solutions. To control these standard solutions in a way tailored to our software ecosystem, we should create a minimal layer on top of them.


## 3. Stakeholders
| Role                       | Responsibility / Interest                                       |
| -------------------------- | --------------------------------------------------------------- |
| Package developers         | Integrate infra into packages for consistent logging/config     |
| Bioinformatics researchers | Benefit indirectly through reliable logging and config handling |
| Software engineers         | Maintain, extend, and test infra package                        |

- The specifities about the people behind on the project can be found in the repository of the package. They are: collaborators, maintainers, admins, etc.
---

## 4. Constraints
- Python 3.10+  
- YAML configuration format
- Logging should be made using the built-in Python library `logging` 
- Config priority order: Environment > Working Dir > User > Package defaults > Ecosystem defaults  

---

## 5. Key Concepts / Terminology
| Term            | Definition                                                     |
| --------------- | -------------------------------------------------------------- |
| `pkg_infra`     | Python package providing logging/config/session functionality  |
| `package_group` | Group of Python packages using infra for shared logging/config |
| Handler         | Component that processes log messages (file, console, custom)  |
| Scope           | Level of config: package or package_group                      |

---

## 6. Assumptions
- Users are familiar with Python and YAML  
- Packages will integrate `pkg_infra` at import time  
- Config files may exist at multiple levels (working directory, user, package, ecosystem)
- Config files should follow a specific given schema to avoid conflicts and force standarization over time

---

## 7. Reference Links
- [Saezlab](https://saezlab.org/)
- [DFG grant](https://gepris.dfg.de/gepris/projekt/528753569?language=en)
- [Umbrella project](https://github.com/saezlab/omnipath)
- [Google docs ideation](https://docs.google.com/document/d/1g8LuNhXY7fjcOCKVVoqpcIv-e5xVa8CUYkO4SAeqLmg/edit?tab=t.0#heading=h.jv2o2z5dzrkd)

---

## 8. Revision History
| Version | Date       | Author        | Description      |
| ------- | ---------- | ------------- | ---------------- |
| 1.0     | 2026-03-13 | Edwin Carreño | Initial document |


## Next:
- Go to the folder `a_requirements`.