# Output Schema

The model must return a single JSON object with this exact shape.

```json
{
  "overall_status": "pass | fail | needs_review",
  "summary": "string",
  "checks": [
    {
      "requirement_id": "string",
      "standard_section": "string",
      "requirement_text": "string",
      "design_field": "string",
      "design_value": "string | number | boolean | null",
      "status": "pass | fail | needs_review | not_applicable",
      "evidence": "string",
      "confidence": "high | medium | low",
      "remediation": "string | null"
    }
  ],
  "missing_design_data": [
    {
      "field": "string",
      "reason_needed": "string",
      "related_requirement_id": "string"
    }
  ],
  "unresolved_questions": ["string"]
}
```

## Field constraints

- `overall_status`: exactly one of the three string literals.
- `summary`: one sentence, ≤ 200 characters.
- `checks`: one entry per (curve × parameter) pair evaluated. Must not be empty if any clause was retrieved.
- `evidence`: must include chunk_id, section, and page from the matched retrieved clause.
- `remediation`: must be null unless `status` is `fail`. Must reference a clause; may not invent values.
- `missing_design_data`: omit the array (or leave empty) when all required fields were present.
- `unresolved_questions`: omit the array (or leave empty) when nothing is ambiguous.
