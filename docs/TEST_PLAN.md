# Test plan and evidence

The team should freeze the model, threshold, zone and camera settings before final evaluation. Use separate enrolment, threshold-validation and final-test captures. Keep participant consent and test labels private. Report raw counts as well as percentages.

## Required whole-system scenarios

| Scenario | Expected result | Evidence to record |
|---|---|---|
| Enrolled staff member enters the zone | Event saved; no intruder alert | Identity decision, event row and no-alert outcome |
| Unenrolled person enters | Photo saved; event saved; alert sent or queued | Recognition result, alert delay/status and evidence paths |
| Person remains outside zone | Ignored by selection rules | Zone result and no intruder alert |
| One enrolled and one unknown person enter | Alert only for unknown person | Separate track IDs and event decisions |
| Entrant's face is turned away or unusable | Face-unclear event/alert | Clear reason; do not call this Unknown |
| Same person stays two minutes | Cooldown limits repeated alerts | Number and timing of events/alerts |
| Low light | Detection still attempted; recognition effect measured | Detection recall and recognition outcome by lighting group |
| No internet | Event/evidence saved; alert pending or queued | Local event row and later delivery outcome |

## Extended real-time scenarios

Add multiple camera distances, side views, glasses, a cap, partial face obstruction, motion blur, crowding, occlusion, tracker ID switches, camera disconnect/reconnect and frame drops. Test twins only with both participants enrolled correctly and enough separate captures. Test a printed photograph, phone screen and replay video as **presentation attacks**. These experiments evaluate vulnerability; they do not prove liveness detection.

Synthetic brightness, blur or overlay images can help debug a pipeline, but report them separately from real camera captures. Augmentation copies are not new independent samples.

## Face-recognition measures

- **Known-person correct rate:** correctly accepted enrolled-person trials divided by all enrolled-person trials.
- **False rejection rate:** enrolled-person trials that do not return the correct accepted identity, divided by enrolled-person trials. Also report unclear/no-face outcomes separately.
- **Wrong identity rate:** enrolled-person trials accepted as the wrong enrolled identity.
- **False acceptance rate:** unenrolled-person trials accepted as any enrolled identity, divided by all unenrolled-person trials.
- **Uncertain rate and face-unclear rate:** report counts and denominators separately.
- **Presentation attack acceptance:** attack captures accepted as a known identity divided by attack captures. Do not label this an anti-spoof detector metric when the system contains no liveness model.

Choose the similarity threshold using validation photos for both enrolled and unenrolled participants. Do not pick it by looking at the final test results. A cosine similarity is not a calibrated probability; label it “similarity”.

## Detection, zone, alert and speed measures

Detection owner reports person precision/recall, zone-membership accuracy, track ID switches and processed frames per second. Alert/storage owner reports entry-to-alert delay, cooldown behaviour and delivery success when the network is absent. Integration reports completed end-to-end scenarios out of total, event consistency, system FPS, latency, crashes and recovered errors.

Video frames from one clip are correlated. Report the number of independent people, captures and clips, and avoid presenting thousands of neighbouring frames as thousands of independent tests. Include the hardware, video resolution, frame sampling, model versions and settings.
