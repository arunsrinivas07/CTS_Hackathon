"""
tools.ml
========

Tools that expose Machine Learning capabilities (predictions,
classification, scoring, etc.) to agents.

Contains:
- prediction_tool.py : Tool-facing interface for ML predictions.
- model_service.py   : Underlying model loading/inference logic.

Agents should only ever call functions/classes from prediction_tool.py,
never model_service.py directly.
"""
