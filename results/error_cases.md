# Error analysis: D-full[gemini]-s0 (test split)

36 failures in total (12 missed, 24 false positives). 10 shown, sampled deterministically (seed 42), real-code cases first.
Diagnoses are computed by re-running each stage; see evaluation/error_analysis.py.

## 1. False positive (real) `real-django-polymorphic-polymorphic-formsets-models`

**Input** `polymorphic/formsets/models.py:269`

```python
  267|         return media
  268| 
> 269|     @cached_property
  270|     def empty_forms(self):
  271|         """
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.utils.functional.cached_property` — The name argument of django.utils.functional.cached_property() is removed in Django 5.0.

**Why:** cited django-5.0-removed-django_utils_functional_cached_property; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 2. False positive (real) `real-django-polymorphic-polymorphic-formsets-models`

**Input** `polymorphic/formsets/models.py:60`

```python
   58|         self.error_messages = error_messages
   59| 
>  60|     @cached_property
   61|     def content_type(self):
   62|         """
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.utils.functional.cached_property` — The name argument of django.utils.functional.cached_property() is removed in Django 5.0.

**Why:** cited django-5.0-removed-django_utils_functional_cached_property; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 3. False positive (real) `real-django-money-djmoney-init`

**Input** `djmoney/__init__.py:2`

```python
    1| __version__ = "2.1.1"
>   2| default_app_config = "djmoney.apps.MoneyConfig"
```

**Expected (execution):** no breaking change observed on this line

**Got:** `default_app_config` — The default_app_config application configuration variable has been removed in Django 4.1. Application configuration should instead be specified via the default_auto_field or by using AppConfig in the 

**Why:** cited django-4.1-removed-default_app_config; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 4. False positive (real) `real-django-taggit-taggit-managers`

**Input** `taggit/managers.py:664`

```python
  662|             )
  663| 
> 664|     def get_joining_columns(self, reverse_join=False):
  665|         if reverse_join:
  666|             return ((self.model._meta.pk.column, "object_id"),)
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.fields.related.RelatedField.get_joining_columns` — The get_joining_columns() method of ForeignObject and ForeignObjectRel is deprecated in Django 5.0 in favor of get_joining_fields().

**Why:** cited django-5.0-deprecated-django_db_models_fields_related_foreignobject_get_joining_co; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 5. Missed breaking usage (real) `real-django-taggit-taggit-serializers`

**Input** `taggit/serializers.py:10`

```python
    8| # Third party
    9| from django.utils.translation import gettext_lazy
>  10| from rest_framework import serializers
   11| 
   12| 
```

**Expected (execution):** Django 4.1.13: RemovedInDjango50Warning: The django.utils.timezone.utc alias is deprecated. Please update your code to use datetime.timezone.utc instead.

**Got:** no finding on this statement

**Why:** analyzer: no library reference resolved on this statement (dynamic access, unknown receiver type, or a pattern the analyzer does not model)

## 6. False positive (synthetic) `syn-auto-settings-forms-urlfield-assume-https-v0`

**Input** `settings.py:2`

```python
    1| SECRET_KEY = "benchmark"
>   2| USE_TZ = True
    3| INSTALLED_APPS = [
    4|     "django.contrib.contenttypes",
```

**Expected (execution):** no breaking change observed on this line

**Got:** `settings.USE_TZ` — The default value of the USE_TZ setting is changed from False to True.

**Why:** cited django-5.0-removed-settings_use_tz; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 7. Missed breaking usage (synthetic) `syn-mixed-19`

**Input** `case.py:12`

```python
   10| 
   11| 
>  12| validator = EmailValidator(whitelist=["localhost"])
   13| allowed = validator.domain_whitelist
   14| 
```

**Expected (execution):** Django 4.0.10: RemovedInDjango41Warning: The whitelist argument is deprecated in favor of allowlist.

**Got:** no finding on this statement

**Why:** retrieval/KB: references found (django.core.validators.EmailValidator) but no retrieved in-range KB entry names them; the change may be missing from the KB or described differently

## 8. Missed breaking usage (synthetic) `syn-mixed-01`

**Input** `case.py:2`

```python
    1| from django import forms
>   2| from django.core.files.storage import get_storage_class
    3| from django.core.cache.backends.memcached import MemcachedCache
    4| 
```

**Expected (execution):** Django 5.1.15: ImportError: cannot import name 'get_storage_class' from 'django.core.files.storage' (/venvs/5.1.15/lib/python3.10/site-packages/django/core/files/storage/__init__.py)

**Got:** no finding on this statement

**Why:** reasoner: matching evidence was retrieved (django-4.2-deprecated-django_core_files_storage_get_storage_class, django-5.1-removed-django_core_files_storage_get_storage_class; type deprecated/removed) but no finding was reported (behavior-change entries and argument-specific entries without the argument in the call are skipped)

## 9. False positive (synthetic) `syn-manual-is-iterable-call`

**Input** `case.py:1`

```python
>   1| from django.utils.itercompat import is_iterable
    2| 
    3| ITEMS = [1, 2, 3]
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.utils.itercompat.is_iterable` — The undocumented django.utils.itercompat.is_iterable() function and the django.utils.itercompat module are deprecated in Django 5.1. Use isinstance(..., collections.abc.Iterable) instead.

**Why:** cited django-5.1-deprecated-django_utils_itercompat_is_iterable, django-5.1-deprecated-django_utils_itercompat; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry

## 10. False positive (synthetic) `syn-mixed-19`

**Input** `case.py:22`

```python
   20| 
   21| month = TruncMonth("created", is_dst=False)
>  22| week = TruncWeek("created", is_dst=False)
   23| year = TruncYear("created")
```

**Expected (execution):** no breaking change observed on this line

**Got:** `django.db.models.functions.TruncWeek` — The is_dst argument is removed from django.db.models.functions.TruncWeek().

**Why:** cited django-5.0-removed-django_db_models_functions_truncweek; execution: the line ran cleanly under every version (no error, no Django warning). Either the documented change does not manifest on this code path (e.g. silently ignored or only affects other arguments) or the reasoner over-applied the entry
