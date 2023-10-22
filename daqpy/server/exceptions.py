class BreakInnerLoop(Exception):
    """
    raised to break all inner loop, either of Idler or of RunWith or WithoutStateMachine
    """
    pass

class BreakAllLoops(Exception):
    """
    raised to exit the event loop itself
    """
    pass

class StateMachineError(Exception):

    pass 


__all__ = ['BreakInnerLoop', 'BreakAllLoops', 'StateMachineError']