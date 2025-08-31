class TwoFactorRequiredError(Exception):
    """Вызывается, когда для продолжения требуется код 2FA."""
    pass


class GoLoginTimeoutError(Exception):
    """Вызывается, когда операция с GoLogin (старт, стоп, создание) превышает таймаут."""
    pass


class GoLoginProfileError(Exception):
    pass


class NoValidGoLoginAccountsError(Exception):
    pass


class VerificationCodeRequiredError(Exception):
    """Вызывается, когда для входа требуется код с почты."""
    def __init__(self, message: str, is_manual_input_needed: bool):
        super().__init__(message)
        self.is_manual_input_needed = is_manual_input_needed