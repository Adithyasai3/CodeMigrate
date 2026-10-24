from django.template import Context, Engine

engine = Engine()
OUT = engine.from_string("{{ value|length }}").render(Context({"value": [1, 2]}))
