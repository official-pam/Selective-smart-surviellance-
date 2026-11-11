# Local alert policy

**Owner: Abubakar Ahmed.** `policy.py` decides which recognition result can raise a local dashboard alert. `service.py` provides the integration-facing service and calls the event store. There are no external messages. A zone entry raises an immediate potential-intruder alert unless recognition has already confirmed a registered person. This includes entries where no face is visible; the notice is resolved if a later frame confirms a registered identity.
