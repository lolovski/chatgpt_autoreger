class TwoFactorRequiredError(Exception):
    """Вызывается, когда для продолжения требуется код 2FA."""
    pass

class GoLoginTimeoutError(Exception):
    """Вызывается, когда операция с GoLogin (старт, стоп, создание) превышает таймаут."""
    pass

class GoLoginProfileError(Exception):
    pass