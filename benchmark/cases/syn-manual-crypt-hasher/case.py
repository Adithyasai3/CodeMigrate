from django.contrib.auth.hashers import CryptPasswordHasher

hasher = CryptPasswordHasher()
algorithm = hasher.algorithm
