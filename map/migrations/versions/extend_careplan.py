"""Add additional Questionnaire to all appropriate CarePlans"""
from map.migrations.helpers import extend_care_plan

version = 6

missing_questionnaire = {
    "detail": {
      "instantiatesCanonical": [
        "Questionnaire/1376"
      ],
      "status": "scheduled",
      "doNotPerform": False,
      "description": "COVID-19 testing questionnaire"
    }
  }


def upgrade():
    extend_care_plan(missing_questionnaire)
