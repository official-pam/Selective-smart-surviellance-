# Team roles and module handoffs

These assignments follow the Group 4 team task sheet. File ownership means who prepares the module and its evidence; it does not prevent teammates from reviewing or helping.

| Owner | Owns | Must provide | Receives |
|---|---|---|---|
| Williams Emehel | `detection/` | Persistent track ID, person box, zone ID, inside/outside state, entry/exit time, person crop | Camera frame and configured zone from the application |
| Emmanuel John | `facial_recognition/` | Tracking ID, identity status, accepted name only for Known, cosine similarity, reason for unclear face | Face crop and tracking ID from detection/integration |
| Abubakar Ahmed | `alerting/`, `storage/` | Saved face/full-frame evidence, event row, delivery state, duplicate-alert cooldown | Selected entry event from integration and safe image paths |
| Ugochukwu Okoroji | `dashboard/` | Dashboard screens populated by real event records | Read-only event-store access, coordinated with Abubakar |
| Josiah Frank Achile | `integration/` | One runnable processing flow and agreed interfaces | Completed modules and the shared contracts |
| Joseph Ekuma | `evaluation/`, end-to-end QA | Scenario results, problems/fixes, demo and backup recording | A stable integrated build and the team test plan |

## Rules everyone follows

- Change a shared record only after discussing the interface with the other owners.
- Keep a tracking ID separate from a person's name. Tracking identifies a video track; recognition proposes an identity.
- Pass `Face unclear` when a face cannot be assessed. Do not silently turn a missing or blurry face into `Unknown`.
- Only `Known` may include an accepted name. Keep a nearest-match candidate separate from an accepted identity.
- Raise an intruder event only for someone detected **inside** the restricted zone. Outside-zone activity is ignored by the selection policy.
- A known staff entry is logged but does not produce an intruder alert. Unknown and face-unclear entries can trigger alerts.
- Make entry/exit, uncertain recognition and alert-delivery failures visible in logs so the team can explain what the system did.

## Suggested work sequence

1. Josiah reviews `contracts.py` with every owner and records any approved changes in `INTERFACES.md`.
2. Williams returns detections for inside and outside tracks and tests entry/exit.
3. Emmanuel consumes the contract and measures recognition on held-out photos before choosing a threshold.
4. Abubakar stores each security event before attempting delivery, so a network failure does not erase it.
5. Ugochukwu connects the dashboard to saved event data.
6. Joseph leads the integrated scenario run, records counts and rates, and captures a successful demo plus a backup.
