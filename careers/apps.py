from django.apps import AppConfig


class CareersConfig(AppConfig):
    name = 'careers'

    def ready(self):
        # Importing signals here registers them with Django's signal dispatcher.
        # This is the canonical place — runs once when the app registry is fully loaded.
        import careers.signals  # noqa: F401
