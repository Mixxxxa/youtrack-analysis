class InvalidIssueIdError(RuntimeError):
    def __init__(self, id: str, *args):
        super().__init__(f"Invalid issue id or url: '{id}'" , *args)

class ParsingError(RuntimeError):
    def __init__(self, id: str, message: str):
        super().__init__(f"Unable to parse data from issue '{id}': {message}")