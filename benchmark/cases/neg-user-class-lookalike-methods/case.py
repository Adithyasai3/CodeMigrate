class Inventory:
    def assertQuerysetEqual(self, a, b):
        return list(a) == list(b)

    def make_random_password(self):
        return "not-random"


INV = Inventory()
SAME = INV.assertQuerysetEqual([1], [1])
PW = INV.make_random_password()
