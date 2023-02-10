class WebError(Exception):
    """BHT pipeline base exception"""

    def __init__(self, message="BHT Error"):
        self.message = message
        super().__init__(self.message)


class WebPathError(WebError):
    """File or Dir path error"""
    pass


class WebResultError(WebError):
    """Result error"""
    pass