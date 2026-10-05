import pytest

import mailer


@pytest.fixture(autouse=True)
def no_real_email(monkeypatch):
    """Tests must never reach Gmail, even if MAIL_* settings are present."""
    def refuse(message):
        raise AssertionError("Tests attempted to send a real email.")
    monkeypatch.setattr(mailer, "send_message", refuse)
