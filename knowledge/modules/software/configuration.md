# Layered configuration semantics

Model expected precedence as base < environment < command line, independent of truthiness. Recursive merge preserves unrelated nested keys when a nested dictionary supplies only some settings. Replacement of lists is typically preferable to concatenation unless explicitly specified. Validation rejects unknown top-level and nested keys before mutation. Copying a top-level dict is not the same as deep-copying nested maps.

Source category: general engineering principles. NOT fixture test results.
