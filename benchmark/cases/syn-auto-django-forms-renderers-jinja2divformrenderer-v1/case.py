import logging

logger = logging.getLogger(__name__)

from django.forms import renderers

VALUE = renderers.Jinja2DivFormRenderer
