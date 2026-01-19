"""Configuration surfaces for the DARE framework (v2).

The v2 architecture treats configuration as part of the developer-facing API
(Layer 3) and avoids coupling the Kernel (Layer 0) to any particular config
schema. Plugin managers and components MAY choose to depend on these models for
deterministic selection/filtering semantics.
"""

