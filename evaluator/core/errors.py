"""The evaluator's exception taxonomy.

Defined here so that every layer raises from the same vocabulary, and so that tests can
tell the two kinds of failure apart:

* an **infrastructure** failure means the measurement did not happen — the assistant
  timed out, the judge rate-limited us, the backend was down. It is never evidence that
  the assistant answered badly.
* a **quality** failure means the measurement happened and the answer was wrong. That is
  a plain assertion failure in a test, not an exception.
"""


class EvaluatorError(Exception):
    """Base class for everything this framework raises."""


class InfrastructureError(EvaluatorError):
    """The measurement could not be taken. Report as an error, never as a bad answer."""


class AssistantUnavailable(InfrastructureError):
    """The assistant under test could not be reached or did not reply in time."""


class BackendUnavailable(InfrastructureError):
    """Ground-truth data could not be fetched, so there is nothing to judge against."""


class JudgeUnavailable(InfrastructureError):
    """The judge could not be reached, or refused to answer."""


class InvalidVerdict(EvaluatorError):
    """The judge replied, but not in the shape the rubric demands.

    A rubric problem, not an assistant problem — never silently treat it as a fail.
    """


class PromptNotFound(EvaluatorError):
    """A prompt file is missing.

    Loud on purpose: a silently empty method prompt would leave the judge grading
    against the rubric alone, and every verdict after that would be meaningless.
    """
