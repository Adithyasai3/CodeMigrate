from django.core.signing import Signer, TimestampSigner

signer = Signer(key="secret-key-1", sep=":")
stamp = TimestampSigner(key="secret-key-2")
TOKEN = signer.sign("hello")
