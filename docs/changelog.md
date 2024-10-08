# Release Notes
---

# [0.3.0](https://github.com/osl-incubator/retsu/compare/0.2.4...0.3.0) (2024-08-18)


### Features

* Add initial support for async processes ([#19](https://github.com/osl-incubator/retsu/issues/19)) ([7ce37d1](https://github.com/osl-incubator/retsu/commit/7ce37d12990029d2d2d02446b4fd5fc7040205f0))
* Add wrap-up decorator for managing celery tasks ([#20](https://github.com/osl-incubator/retsu/issues/20)) ([41c6fb3](https://github.com/osl-incubator/retsu/commit/41c6fb37a19c376b010aae13c22f1ac43cbd80fe))

## [0.2.4](https://github.com/osl-incubator/retsu/compare/0.2.3...0.2.4) (2024-08-16)


### Bug Fixes

* Fix __del__ and rename create_processes to setup ([#18](https://github.com/osl-incubator/retsu/issues/18)) ([c4654d7](https://github.com/osl-incubator/retsu/commit/c4654d77623477bbae0b86b0cb841bd8595593fb))

## [0.2.3](https://github.com/osl-incubator/retsu/compare/0.2.2...0.2.3) (2024-08-16)


### Bug Fixes

* Fix function names and fix minor issues ([#17](https://github.com/osl-incubator/retsu/issues/17)) ([f4cf368](https://github.com/osl-incubator/retsu/commit/f4cf368837450cfd95d7554cf75635f5421342d0))

## [0.2.2](https://github.com/osl-incubator/retsu/compare/0.2.1...0.2.2) (2024-08-14)


### Bug Fixes

* Fix stopping workflow and refactor ([#15](https://github.com/osl-incubator/retsu/issues/15)) ([5ab8f9b](https://github.com/osl-incubator/retsu/commit/5ab8f9b8d1ce53a77572398f09f0164d90a3b2f8))

## [0.2.1](https://github.com/osl-incubator/retsu/compare/0.2.0...0.2.1) (2024-08-12)


### Bug Fixes

* Force process termination ([#14](https://github.com/osl-incubator/retsu/issues/14)) ([0e4f088](https://github.com/osl-incubator/retsu/commit/0e4f08858ad17642338648bc123749259b3e06b8))

# [0.2.0](https://github.com/osl-incubator/retsu/compare/0.1.1...0.2.0) (2024-06-29)


### Features

* Use redis for queues ([#13](https://github.com/osl-incubator/retsu/issues/13)) ([750fb6b](https://github.com/osl-incubator/retsu/commit/750fb6b71300b0b40831f6e8917d324edb58592a))

## [0.1.1](https://github.com/osl-incubator/retsu/compare/0.1.0...0.1.1) (2024-06-20)


### Bug Fixes

* Fix `get` command in the result attribute, and add `get_group_tasks` ([#11](https://github.com/osl-incubator/retsu/issues/11)) ([ff29334](https://github.com/osl-incubator/retsu/commit/ff293346b08c3c63d410830e4c68cd9ad428e78f))

# [0.1.0](https://github.com/osl-incubator/retsu/compare/0.0.4...0.1.0) (2024-06-07)


### Features

* Add method create_task to the ProcessManager class ([07379b8](https://github.com/osl-incubator/retsu/commit/07379b8da2dd3aeef4f7326e9fad8322cadd2db8))

## [0.0.4](https://github.com/osl-incubator/retsu/compare/0.0.3...0.0.4) (2024-05-31)


### Bug Fixes

* Improve the task metadata handling ([#7](https://github.com/osl-incubator/retsu/issues/7)) ([476e0b4](https://github.com/osl-incubator/retsu/commit/476e0b444e89d87203e3b1964e4ba091e74afd1c))

## [0.0.3](https://github.com/osl-incubator/retsu/compare/0.0.2...0.0.3) (2024-05-29)


### Bug Fixes

* Fix initial issues with the structure and the example ([#5](https://github.com/osl-incubator/retsu/issues/5)) ([7d520f9](https://github.com/osl-incubator/retsu/commit/7d520f90606412bb3c77d4444fefed871684e034))
* wait for the celery task until the end of the execution. ([#6](https://github.com/osl-incubator/retsu/issues/6)) ([f1ba586](https://github.com/osl-incubator/retsu/commit/f1ba5865f3bd115e978b8b0b9ccfc8639d34983a))

## [0.0.2](https://github.com/osl-incubator/retsu/compare/0.0.1...0.0.2) (2024-05-28)


### Bug Fixes

* Fix documentation build step ([#3](https://github.com/osl-incubator/retsu/issues/3)) ([1244e73](https://github.com/osl-incubator/retsu/commit/1244e7377442653335cb8db6a1553ae59e39101f))
* Fix issue with semantic-release version pattern ([#4](https://github.com/osl-incubator/retsu/issues/4)) ([6ce350a](https://github.com/osl-incubator/retsu/commit/6ce350a9599ece9f1c263f236924251296b8d3a5))
