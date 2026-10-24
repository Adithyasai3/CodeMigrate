from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.views.static import was_modified_since

VALUE = was_modified_since
