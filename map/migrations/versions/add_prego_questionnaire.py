"""Add Pregnancy Questionnaire to all appropriate CarePlans"""
from map.migrations.helpers import extend_care_plan

version = 7

missing_questionnaire = {
    "detail": {
      "instantiatesCanonical": [
        "Questionnaire/1442"
      ],
      "status": "scheduled",
      "doNotPerform": False,
      "description": "Pregnancy questionnaire"
    }
  }


def upgrade():
    extend_care_plan(missing_questionnaire)
