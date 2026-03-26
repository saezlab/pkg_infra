# User Stories

## MVP


### US-001: Discover and merge configurations
**As a** package developer  
**I need** the system to discover and merge configurations from multiple sources (working directory, user, package built-in)  
**So that** each package can load correct settings automatically.

#### Details and Assumptions
* Merge order is expected to follow source priority.
* Supported sources include working directory, user-level config, and package defaults.


---

### US-002: Use standardized config format
**As a** package developer  
**I need** configuration files to be in YAML format  
**So that** they are readable, consistent, and compatible with established tools like Hydra or OmegaConf.

#### Details and Assumptions
* YAML is the standard format for project configuration files.


---

### US-003: Propagate configuration
**As a** package developer  
**I need** configuration parameters to be propagated to lower-level packages  
**So that** all packages in the ecosystem use consistent settings.

#### Details and Assumptions
* Lower-level packages should receive only relevant config sections.


---

### US-004: Centralized logging setup
**As a** package developer  
**I need** a plug-and-play logging setup via a single initialize(config_path) call  
**So that** logging is standardized without writing boilerplate code.

#### Details and Assumptions
* Initialization should be idempotent for repeated calls.


---

### US-005: Console and file logging
**As a** user  
**I need** logs to be output both to console and file by default  
**So that** I can monitor real-time messages and keep a record.

#### Details and Assumptions
* Default behavior should require no extra configuration.

---

### US-006: Log rotation
**As a** user  
**I need** log files to rotate when they exceed a configurable size (e.g., 10 MB)  
**So that** log files do not grow indefinitely.

#### Details and Assumptions
* Max file size and backup count are configurable values.


---

### US-007: Timestamped log files
**As a** user  
**I need** log files to include timestamps in their filenames (including time zone)  
**So that** I can track when logs were generated.

#### Details and Assumptions
* Timestamp format should include timezone information.


---

### US-008: Logger exclusion
**As a** package developer  
**I need** to exclude specific loggers or set their level via configuration  
**So that** I can reduce unnecessary log noise (e.g., pandas or matplotlib).

#### Details and Assumptions
* Excluded or overridden loggers are configured in YAML.


---

### US-009: Configurable log parameters
**As a** package developer  
**I need** to configure log format, level, directory, app name, max file size, and backup count via YAML  
**So that** logging is flexible and maintainable.

#### Details and Assumptions
* Configuration values are validated before logger setup.


---

### US-010: Per-component logger
**As a** package developer  
**I need** one logger per major component of the application ecosystem  
**So that** logs can be separated by module.

#### Details and Assumptions
* Component naming convention is defined by the application ecosystem.


---

### US-011: JSON log output
**As a** package developer  
**I need** logs to be optionally generated in JSON format  
**So that** logs can be machine-readable for further processing.

#### Details and Assumptions
* JSON output mode can be toggled in configuration.

---

### US-012: Non-blocking logging
**As a** package developer  
**I need** logging to use a queue handler for async calls  
**So that** logging does not block program execution.

#### Details and Assumptions
* Queue-based logging should preserve delivery guarantees defined by policy.


---

### US-013: Centralized session management
**As a** package developer  
**I need** a single session object that contains both config and logger  
**So that** all packages can access them consistently.

#### Details and Assumptions
* Session lifecycle and singleton behavior are defined by package conventions.


---

### US-014: Demo examples
**As a** new developer  
**I need** a demo folder with example usage and configuration  
**So that** I can understand how to integrate `pkg_infra` quickly.

#### Details and Assumptions
* Demo should include a minimal runnable example and example config.


---

### US-015: Unit testing
**As a** software engineer  
**I need** a tests folder with unit tests for config, logging, and session  
**So that** I can ensure correct functionality before deployment.

#### Details and Assumptions
* Test framework and coverage thresholds are project-defined.


---

### US-016: Optional per-application log files
**As a** package developer  
**I need** the ability to generate a dedicated log file for each application  
**So that** I can isolate logs per application (future feature).

#### Details and Assumptions
* [document what you know]


---

### US-017: Extensible session/config
**As a** package developer  
**I need** the session and config layer to be extensible for future features  
**So that** the system can grow without redesign.

#### Details and Assumptions
* Extension points should not break existing configuration contracts.
