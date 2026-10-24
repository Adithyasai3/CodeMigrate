from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.expressions import Expression

MEMBER = Expression.get_group_by_cols
