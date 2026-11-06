# Local alert policy

**Owner: Abubakar Ahmed.** `policy.py` decides which recognition result can raise a local dashboard alert. `service.py` provides the integration-facing service and calls the event store. There are no external messages. Currently only a definite `Unknown` result is an alert candidate; Known is informational and inconclusive results are logged without an alert claim. The dashboard may show a separate review warning when identity could not be confirmed.
