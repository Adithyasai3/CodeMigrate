# Error analysis: D-full[offline] (test split)

46 failures in total (11 missed, 35 false positives). 10 shown, sampled deterministically (seed 42), real-code cases first.
Diagnoses are computed by re-running each stage; see evaluation/error_analysis.py.

## 1. False positive (real) `real-django-taggit-taggit-managers`

**Input** `taggit/managers.py:664`

```python
  662|             )
  663| 
> 664|     def get_joining_columns(self, reverse_join=False):
  665|         if reverse_join:
  666|             return ((self.model._meta.pk.column, "object_id"),)
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.fields.related.RelatedField.get_joining_columns` — The get_joining_columns() method of ForeignObject and ForeignObjectRel is deprecated. Starting with Django 6.0, django.db.models.sql.datastructures.Join will no longer fallback to get_joining_columns(

**Why:** cited django-5.0-deprecated-django_db_models_fields_related_foreignobject_get_joining_co; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 2. False positive (real) `real-django-polymorphic-polymorphic-managers`

**Input** `polymorphic/managers.py:35`

```python
   33|         return qs
   34| 
>  35|     def __str__(self):
   36|         return "{} (PolymorphicManager) using {}".format(
   37|             self.__class__.__name__,
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.Manager.__str__` — The SitemapIndexItem.__str__() method is removed.

**Why:** cited django-5.0-removed-django_contrib_sitemaps_views_sitemapindexitem_str; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 3. False positive (real) `real-django-filter-django-filters-filters`

**Input** `django_filters/filters.py:9`

```python
    7| from django.db.models.constants import LOOKUP_SEP
    8| from django.forms.utils import pretty_name
>   9| from django.utils.itercompat import is_iterable
   10| from django.utils.timezone import now
   11| from django.utils.translation import gettext_lazy as _
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.utils.itercompat.is_iterable` — The undocumented django.utils.itercompat.is_iterable() function and the django.utils.itercompat module are deprecated. Use isinstance(..., collections.abc.Iterable) instead.

**Why:** cited django-5.1-deprecated-django_utils_itercompat_is_iterable, django-5.1-deprecated-django_utils_itercompat; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 4. False positive (real) `real-django-taggit-taggit-managers`

**Input** `taggit/managers.py:690`

```python
  688|         get_extra_restriction = _get_extra_restriction
  689| 
> 690|     def get_reverse_joining_columns(self):
  691|         return self.get_joining_columns(reverse_join=True)
  692| 
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.fields.related.RelatedField.get_reverse_joining_columns` — The ForeignObject.get_reverse_joining_columns() method is deprecated.

**Why:** cited django-5.0-deprecated-django_db_models_fields_related_foreignobject_get_reverse_jo; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 5. False positive (real) `real-django-taggit-taggit-models`

**Input** `taggit/models.py:25`

```python
   23|     )
   24| 
>  25|     def __str__(self):
   26|         return self.name
   27| 
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.Model.__str__` — The SitemapIndexItem.__str__() method is removed.

**Why:** cited django-5.0-removed-django_contrib_sitemaps_views_sitemapindexitem_str; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 6. False positive (synthetic) `syn-manual-register-converter-override`

**Input** `case.py:1`

```python
>   1| from django.urls import register_converter
    2| 
    3| 
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.urls.register_converter` — Overriding existing converters with django.urls.register_converter() is deprecated.

**Why:** cited django-5.1-deprecated-django_urls_register_converter; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 7. Missed breaking usage (synthetic) `syn-manual-was-modified-since-size`

**Input** `case.py:3`

```python
    1| from django.views.static import was_modified_since
    2| 
>   3| MODIFIED = was_modified_since(None, 0, 0)
```

**Expected (execution):** Django 4.1.13: TypeError: was_modified_since() takes from 0 to 2 positional arguments but 3 were given

**Got:** no finding on this statement

**Why:** reasoner: matching evidence was retrieved (django-4.1-incompatible-django_views_static_was_modified_since; type removed) but no finding was reported (behavior-change entries and argument-specific entries without the argument in the call are skipped)

## 8. False positive (synthetic) `syn-mixed-13`

**Input** `case.py:1`

```python
>   1| from django.utils.html import format_html
    2| from django.test import SimpleTestCase
    3| from django.utils.functional import cached_property
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.utils.html.format_html` — Support for calling format_html() without passing args or kwargs is deprecated.

**Why:** cited django-5.0-deprecated-django_utils_html_format_html; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 9. Missed breaking usage (synthetic) `syn-manual-check-constraint-check-kwarg`

**Input** `case.py:3`

```python
    1| from django.db.models import CheckConstraint, Q, UniqueConstraint
    2| 
>   3| adult = CheckConstraint(check=Q(age__gte=18), name="adult")
    4| unique_email = UniqueConstraint(fields=["email"], name="unique_email")
```

**Expected (execution):** Django 5.1.15: RemovedInDjango60Warning: CheckConstraint.check is deprecated in favor of `.condition`.

**Got:** no finding on this statement

**Why:** retrieval/KB: references found (django.db.models.CheckConstraint, django.db.models.Q) but no retrieved in-range KB entry names them; the change may be missing from the KB or described differently

## 10. False positive (synthetic) `syn-mixed-07`

**Input** `case.py:5`

```python
    3| from django.db import models
    4| from django.db.models.enums import ChoicesMeta
>   5| from django.urls import register_converter
    6| 
    7| 
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.urls.register_converter` — Overriding existing converters with django.urls.register_converter() is deprecated.

**Why:** cited django-5.1-deprecated-django_urls_register_converter; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry
