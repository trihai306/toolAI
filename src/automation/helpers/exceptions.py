class BrowserControllerException(Exception):
    """Base exception cho BrowserController"""
    pass

class BrowserNotAvailable(BrowserControllerException):
    pass

class ElementNotFound(BrowserControllerException):
    pass

class ActionTimeout(BrowserControllerException):
    pass

class PopupNotClosed(BrowserControllerException):
    pass 