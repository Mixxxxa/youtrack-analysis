from enum import StrEnum, auto

class IssueState:
    class Pre(StrEnum):
        Buffer = 'Buffer'
        OnHold = 'On hold'
        InProgress = 'In progress'
        Review = 'Review'
        Resolved = 'Resolved'
        Suspend = 'Suspend'
        WontFix = 'Wontfix'
        Duplicate = 'Duplicate'


    def __init__(self, value: 'IssueState.Pre'):
        assert value in IssueState.Pre
        self.__value = value

    
    def __eq__(self, other):
        if isinstance(other, IssueState):
            return self.__value == other.__value
        if isinstance(other, IssueState.Pre):
            return self.__value == other
        return NotImplemented
    

    def __str__(self):
        return str(self.__value)


    @staticmethod
    def parse(state: str) -> 'IssueState':
        state = state.strip().lower()
        if state == 'buffer':
            return IssueState(IssueState.Pre.Buffer)
        elif state == 'on hold':
            return IssueState(IssueState.Pre.OnHold)
        elif state == 'in progress':
            return IssueState(IssueState.Pre.InProgress)
        elif state == 'review':
            return IssueState(IssueState.Pre.Review)
        elif state == 'resolved':
            return IssueState(IssueState.Pre.Resolved)
        elif state == 'suspend':
            return IssueState(IssueState.Pre.Suspend)
        elif state == 'wontfix':
            return IssueState(IssueState.Pre.WontFix)
        elif state == 'duplicate':
            return IssueState(IssueState.Pre.Duplicate)
        raise RuntimeError(f'Unknown issue state \'{state}\'')


    def is_buffer(self) -> bool:
        return self.__value == IssueState.Pre.Buffer


    def is_hold(self) -> bool:
        return self.__value == IssueState.Pre.OnHold


    def is_in_progress(self) -> bool:
        return self.__value == IssueState.Pre.InProgress


    def is_review(self) -> bool:
        return self.__value == IssueState.Pre.Review


    def is_in_work(self) -> bool:
        P = IssueState.Pre
        return self.__value == P.InProgress or self.__value == P.Review
    

    def is_active(self) -> bool:
        P = IssueState.Pre
        return (
            self.__value == P.Buffer or 
            self.__value == P.OnHold or 
            self.__value == P.InProgress or 
            self.__value == P.Review
        )
    