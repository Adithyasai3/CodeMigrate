from django.core.signing import Signer, TimestampSigner

signer = Signer("secret-key-1", ":")
stamp = TimestampSigner("secret-key-2")
token = signer.sign("hello")
