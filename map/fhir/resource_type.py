from enum import Enum, auto


class NameEnum(Enum):
    """Mechanism to auto generate enum values using enum.name"""
    def _generate_next_value_(name, start, count, last_values):
        return name


class ResourceType(NameEnum):
    """Enumeration of supported FHIR resourceTypes"""
    # Extend as needed, controlled to prevent abuse of the API
    CarePlan = auto()
    Communication = auto()
    DocumentReference = auto()
    Encounter = auto()
    Observation = auto()
    Patient = auto()
    Procedure = auto()
    Questionnaire = auto()
    QuestionnaireResponse = auto()

    @classmethod
    def validate(cls, value):
        """validate given value is in ResourceType enumeration"""
        if value in cls.__members__:
            return True
        raise ValueError(f"{value} not a supported FHIR resourceType")
