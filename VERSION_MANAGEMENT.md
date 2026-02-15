# JiecUnit Version Management

## Overview

JiecUnit uses semantic versioning (MAJOR.MINOR.PATCH) to manage releases. The version information is stored in the `VERSION` file at the project root and can be accessed from programs through preprocessor macros.

## Version File

The `VERSION` file contains the current version in the format:
```
MAJOR.MINOR.PATCH
```

Example:
```
2.8.1
```

## Accessing Version from Code

The version is defined in `src/jiecunit_config.txt` and can be accessed using the following macros:

- `_JIECUNIT` - Always true (indicates JiecUnit is included)
- `_JIECUNIT_VERSION` - Full version string (e.g., "2.8.1")
- `_JIECUNIT_VER` - Short version number (e.g., 208 for version 2.8.x)
- `_JIECUNIT_FULL_VER` - Full version number (e.g., 20801 for version 2.8.1)

### Version Number Format

- `_JIECUNIT_VER` = MAJOR * 100 + MINOR
  - Example: 2.8.1 → 2 * 100 + 8 = 208
- `_JIECUNIT_FULL_VER` = MAJOR * 10000 + MINOR * 100 + PATCH
  - Example: 2.8.1 → 2 * 10000 + 8 * 100 + 1 = 20801

### Example Usage

```iec-st
{#include <jiecunit.txt>}

TEST_S(test_version_info)
    {st}
    puts(jiec_concat('Version: ', _JIECUNIT_VERSION));
    puts(jiec_concat('Short Ver: ', dint_to_string(_JIECUNIT_VER)));
    puts(jiec_concat('Full Ver: ', dint_to_string(_JIECUNIT_FULL_VER)));
    {end}
END_TEST_S
```

See `samples/version_sample.txt` for a complete working example.

## Updating Version

To update the version:

1. Update the `VERSION` file with the new version number
2. Update the version macros in `src/jiecunit_config.txt`:
   ```
   {#define _JIECUNIT true}
   {#define _JIECUNIT_FULL_VER XXXXX}  // MAJOR*10000 + MINOR*100 + PATCH
   {#define _JIECUNIT_VER XXX}          // MAJOR*100 + MINOR
   {#define _JIECUNIT_VERSION "X.Y.Z"}
   ```
3. Commit the changes
4. Tag the commit with the version number: `git tag jiecunit.X.Y.Z`

## Semantic Versioning Guidelines

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

For more information about semantic versioning, see https://semver.org/
