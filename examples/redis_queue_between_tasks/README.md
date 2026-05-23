# Redis queue between Celery tasks example

This directory is a legacy Celery/Flask example from an earlier Retsu API. It is
kept for historical context, but the current public API is documented in the
main documentation:

- [Guard mode](../../docs/guard-mode.md)
- [Admission mode](../../docs/admission-mode.md)
- [Integrations](../../docs/integrations.md)

For current Celery usage, prefer `retsu.celery_guard()` inside a bound Celery
task:

```python
@app.task(bind=True)
def render(self, document_id: str) -> None:
    with retsu.celery_guard(
        self,
        concurrency={"render": 1},
        wait_strategy="retry",
    ):
        render_document(document_id)
```

The legacy `run.sh` flow may require porting before it works with the current
Retsu package.
