# Review demo script (about 4 minutes)

Presenter: **M5** (web app). **M4** speaks during step 6 (validator).
Use the **offline** reasoner for the live part: no API key, no quota, same result every time.

## Before the review (do this 30 minutes early)

1. Start the API (terminal 1, in `D:\CodeMigrate`):
   ```powershell
   .venv\Scripts\python.exe -m uvicorn codemigrate.api.main:app --port 8000
   ```
2. Start the UI (terminal 2):
   ```powershell
   cd frontend; npm run dev
   ```
3. Open http://localhost:5173, log in once with the demo account, and keep the tab open.
4. Open `docs/demo/views.py` in an editor so you can copy it quickly.
5. Do one full practice run of the steps below. Close other heavy apps.
6. Keep the **backup**: a screen recording of this demo, plus `docs/CodeMigrate_Review.pptx`.

## The demo input (`docs/demo/views.py`)

```python
import datetime

from django.db import models
from django.http import JsonResponse
from django.utils.timezone import utc


class Order(models.Model):
    customer = models.CharField(max_length=100)
    created = models.DateTimeField()

    class Meta:
        index_together = [["customer", "created"]]


def recent_orders(request):
    now = datetime.datetime.now(tz=utc)
    orders = Order.objects.filter(created__lte=now)
    return JsonResponse({"count": orders.count()})
```

It looks normal and works on Django 4.0, but has two problems for 5.1:
`django.utils.timezone.utc` (deprecated 4.1, removed 5.0) and `Meta.index_together`
(deprecated 4.2, removed 5.1).

## Steps

| # | Do | Say (in your own words) |
|---|---|---|
| 1 | Show the **New scan** page. | "This is a small Django view that runs fine on Django 4.0. We want to upgrade it to 5.1." |
| 2 | Project: type `Demo shop`. From **4.0**, To **5.1**, Reasoner **offline**, Retriever **hybrid**. Tab **Paste code**, File path `views.py`, paste the code, click **Scan**. | "We choose the versions. Offline mode needs no API key; with an LLM the steps are the same." |
| 3 | Wait for **COMPLETED**. Point at the **3 findings**: line 5 and line 17 (`utc`), line 13 (`index_together`). | "Every finding points to an exact line and is marked VERIFIED, which means our validator checked its citation." |
| 4 | Click the release-note link on the `utc` finding (opens docs.djangoproject.com, 4.1 notes). Come back. | "Each warning links to the official Django release note. Nothing is shown without a source." |
| 5 | Tab **Updated code**. Show `utc = datetime.timezone.utc` replacing the old import, and the `# TODO(codemigrate)` comment above `index_together`. Then tab **Changes** (the diff). Click **Download views.py**. | "Safe changes are fixed automatically. Where an automatic fix could be wrong, we add a clear TODO instead of guessing." |
| 6 | **M4:** run the command below in a terminal (prepared beforehand). | "This is a real answer from Gemini on our benchmark. It claimed `Meta.unique_together` breaks, but gave no release-note citation. The validator rejected it as UNSUPPORTED_CLAIM, so the user never sees it. That's how we reach 0% made-up findings." |
| 7 | Back in the browser: **Export PDF** (shows the report), then **Compare systems** (results table). | "Reports can be shared. Here are the benchmark results: F1 0.82 vs 0.02 for django-upgrade." |

Command for step 6 (one line, PowerShell):

```powershell
Get-Content docs\demo\gemini_rejected_claims.jsonl | ConvertFrom-Json | Where-Object status -eq 'UNSUPPORTED_CLAIM' | Format-List file, line, symbol, status, reject_reason
```

(`docs/demo/gemini_rejected_claims.jsonl` is a copy of every claim the validator rejected in the
Gemini test run, `results/_runs/test-D-full[gemini]-s0.rejected.jsonl`, which git ignores.)

Expected output: `djmoney/contrib/exchange/models.py`, line 30, `Meta.unique_together`,
`UNSUPPORTED_CLAIM`, reason `no citation`.

Expected **Updated code** (step 5):

```python
import datetime

from django.db import models
from django.http import JsonResponse
utc = datetime.timezone.utc


class Order(models.Model):
    customer = models.CharField(max_length=100)
    created = models.DateTimeField()

    class Meta:
        # TODO(codemigrate): index_together: deprecated in Django 4.2. Use Meta.indexes.
        index_together = [["customer", "created"]]
...
```

## Optional: command line (30 seconds, if time allows)

```powershell
.venv\Scripts\codemigrate.exe scan docs\demo\views.py --provider offline --write-fixed fixed_out
```

Prints the same 3 findings and writes the updated file to `fixed_out\views.py`; the original
is never changed.

## If something goes wrong

| Problem | Do this |
|---|---|
| Page does not load | Check both terminals are running; reload http://localhost:5173. |
| Scan stays RUNNING for more than 30 s | The first scan loads the retrieval model; wait once more, otherwise switch to the backup video. |
| Login fails | Click Register and create a new account (takes 10 s). |
| Anything else | Say "let me show the recorded run", play the backup video, and continue with the slides. |

## Questions you may get during the demo

- **"Why offline and not the LLM?"** Same pipeline and same validator. Offline is repeatable and
  does not depend on internet or API quota. Offline F1 is 0.81; with Gemini it is 0.82.
- **"Why didn't it fix `index_together` automatically?"** Moving to `Meta.indexes` needs a
  migration and naming choices. A wrong automatic fix is worse than a clear TODO.
- **"Does the validator ever reject correct findings?"** Yes, sometimes: in the benchmark the
  LLM gave a few correct warnings with the wrong symbol name, and they were dropped. That's why
  recall goes from 0.92 (C) to 0.88 (D). In exchange, no made-up findings get through.
