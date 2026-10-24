from django.contrib.postgres.constraints import ExclusionConstraint

no_overlap = ExclusionConstraint(
    name="no_overlap",
    expressions=[("span", "&&")],
    opclasses=["range_ops"],
)
