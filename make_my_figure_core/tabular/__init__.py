"""General tabular-data workflow: column roles, wide → long reshaping and recorded transformations.

For ordinary experimental tables (ecology, entomology, agriculture, physiology,
...), as opposed to the feature-matrix workflow in ``matrix_workflow``. Nothing
here assumes omics data, and nothing changes a measured value without an
explicit, recorded user decision.
"""
from make_my_figure_core.tabular.roles import (  # noqa: F401
    ROLE_LABELS,
    ROLES,
    ColumnRoles,
    RoleSuggestion,
    roles_from_suggestions,
    suggest_roles,
    validate_roles,
)
from make_my_figure_core.tabular.reshape import (  # noqa: F401
    ReshapeError,
    ReshapePreview,
    ReshapeSuggestion,
    WideToLong,
    preview_wide_to_long,
    suggest_wide_to_long,
    wide_to_long,
)
from make_my_figure_core.tabular.transforms import (  # noqa: F401
    LOG_METHODS,
    METHODS,
    TablePreprocessingSpec,
    TableTransform,
    TransformError,
    TransformPreview,
    apply_table_transforms,
    available_methods,
    derived_column_name,
    file_sha256,
    looks_already_log,
    preview_transform,
    replay,
    table_sha256,
)
