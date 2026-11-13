MESSAGES = {"en": "Welcome", "fr": "Bienvenue"}


def greeting(locale):
    """Return the localized greeting; unsupported locales use English."""
    return MESSAGES[locale]
