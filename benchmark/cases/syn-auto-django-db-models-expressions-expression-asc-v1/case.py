from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.expressions import Expression


class Custom(Expression):
    def run(self):
        return self.asc()
