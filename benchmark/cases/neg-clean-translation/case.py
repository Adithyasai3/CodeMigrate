from django.utils.translation import gettext, gettext_lazy as _, ngettext

TITLE = _("Title")
HELLO = gettext("Hello")
ITEMS = ngettext("item", "items", 2)
