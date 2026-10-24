from django.contrib.sessions.serializers import PickleSerializer

payload = PickleSerializer().dumps({"cart": [1, 2]})
