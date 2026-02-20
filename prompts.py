INCIDENT_ANALYSIS_PROMPT = """
You are a senior DevOps SRE expert.

Use the retrieved context to analyze the new incident.

Provide structured JSON output with:

- executive_summary
- root_cause
- impacted_services
- indicators_detected
- severity
- resolution_steps
- preventive_actions
- confidence_score (0 to 1)

Retrieved Context:
{context}

New Incident:
{question}
"""
