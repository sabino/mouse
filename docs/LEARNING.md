# Personal training protocol

No gesture model or demonstration training dataset is bundled. The synthetic fixtures
in tests exercise mathematics and plumbing only; their scores prove no generalization.

Record at least two independent sessions (prefer 3–5 on different days and lighting).
For each session record multiple clips of every action, neutral pointing/idle movement,
and `confusing` partial gestures, transitions, similar poses and ordinary non-command
movements. Label them explicitly; the app never invents labels. Keep clips chronological:
neutral → action → neutral. Repeat, vary speed/distance/angle, and do not include other
people without consent. Only landmark coordinates and metadata are saved, no images/audio.

Choose the holdout session/person and the classifier before inspecting its scores.
Overlapping 0.6 s windows are generated within clips AFTER session splitting. Five
interpolated time samples contain wrist-relative/palm-scaled xyz, joint cosines and
thumb distances. Left-hand x is canonicalized. Wrist displacement, mean velocity and
velocity variation retain motion; timestamp gaps/hand switches are rejected. Scaling
is fitted only on training windows. Logistic regression (default) and Gaussian naive
Bayes are compared descriptively; the selected method is not silently changed using
the holdout. Models are personalized and do not claim performance on unseen people.

Held-out reports include per-class precision/recall/F1, confusion matrix, rejection
rate and policy replay diagnostics: episode precision/recall, false activations per
idle minute, and median episode latency. Clip-level ground truth is coarse: it is not
expert event annotation. Gaps reset arming; action-only clips without preceding neutral
will miss events by design. Repeated tuning on the same holdout invalidates final-test
claims; collect a fresh session for final evaluation. Report confidence is a model
score, not a validated probability of safety. Perform preview trials before live use.

Safe persistence: bounded JSON, versioned feature/model/profile/calibration schemas,
finite numeric arrays with exact shapes; no pickle, joblib or dynamic model class loading.
Coefficient export uses NumPy inference; tests compare it with sklearn predict_proba.
Cursor coordinates use a separate continuous ridge regression; gesture probabilities
never encode screen coordinates. Save/reload model, calibration and mapping separately.
