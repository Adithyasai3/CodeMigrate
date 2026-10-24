from django.contrib.auth.views import LogoutView


class SiteLogoutView(LogoutView):
    def get_next_page(self):
        return "/goodbye/"
