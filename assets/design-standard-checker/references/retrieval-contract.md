# Retrieval Contract

The application passes retrieved standard clauses to the skill in this exact JSON shape:

```json
{
  "retrieved_clauses": [
    {
      "chunk_id": "std-00123",
      "document_name": "AASHTO-Green-Book.pdf",
      "page": 12,
      "section": "4.2.1",
      "clause_id": "4.2.1-A",
      "text": "The minimum radius of horizontal curves shall be...",
      "similarity_score": 0.87
    }
  ]
}
```

## Field meanings

- `chunk_id`: unique identifier for this text chunk within the application's index.
- `document_name`: the original PDF filename as uploaded by the user.
- `page`: page number in the source PDF (1-based).
- `section`: section number from the source document, if identifiable.
- `clause_id`: a stable identifier composed as `{section}-{letter}` assigned by the application. Use this in `evidence` and `remediation` fields of the output.
- `text`: the raw clause text as extracted from the PDF.
- `similarity_score`: the cosine similarity score from the vector retrieval step (0–1). Higher means more relevant.

## Usage notes

- Clauses are sorted by descending `similarity_score`. The most relevant clauses are first.
- A single query may return clauses from multiple documents.
- Cite `chunk_id`, `section`, `clause_id`, and `page` whenever referencing a clause in `evidence` or `remediation`.
- Do not treat `similarity_score` as a compliance confidence level — it reflects retrieval relevance, not standards authority.
