# Ingest Source Prompt

You are executing the CSR command:

/ingest-source

Objective:

Register a source document in the Cognitive Specification Runtime.

Execution requirements:

1. Verify repository structure.
2. Verify source accessibility.
3. Collect source metadata.
4. Create source registration information.
5. Record an ingestion event.
6. Update runtime state.
7. Produce a concise execution report.

Constraints:

* Do not extract knowledge.
* Do not generate questions.
* Do not detect conflicts.
* Do not modify specifications.

---

## Required Metadata

The registration record must include:

* source name
* source type
* ingestion timestamp
* origin path

origin_path is the relative repository path to the original source file.

Example:

```text
input/documents/test_source.md
```

Expected outputs:

* knowledge_base/raw/
* runtime/events.md
* runtime/state.md

Success criteria:

* source registered
* ingestion event recorded
* runtime state updated

Failure criteria:

* missing repository structure
* inaccessible source
* traceability cannot be recorded
