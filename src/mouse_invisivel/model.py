"""Traditional supervised ML, persisted as validated numerical parameters only."""
from dataclasses import dataclass, field
import numpy as np
from .features import FEATURE_SCHEMA, FEATURE_DIM, windows
from .dataset import label_valid
from .storage import read_json, write_json

MODEL_SCHEMA = "gesture-model-v1"


def array(value, shape):
    a = np.asarray(value, dtype=float)
    if a.shape != shape or not np.isfinite(a).all() or np.abs(a).max() > 1e12:
        raise ValueError("Invalid numeric model parameters")
    return a


@dataclass
class Model:
    kind: str
    labels: list[str]
    mean: np.ndarray
    scale: np.ndarray
    params: dict
    report: dict = field(default_factory=dict)

    def probabilities(self, x):
        x = np.asarray(x, dtype=float)
        if x.shape != (FEATURE_DIM,) or not np.isfinite(x).all():
            raise ValueError("Invalid inference feature vector")
        z = (x - self.mean) / self.scale
        if self.kind == "logistic":
            logits = self.params["coef"] @ z + self.params["intercept"]
            if len(self.labels) == 2:
                # scikit-learn's binary logistic regression stores one decision row.
                logits = np.r_[0., logits[0]]
        else:
            var = self.params["var"]
            logits = (np.log(self.params["prior"]) - 0.5 * np.sum(
                np.log(2 * np.pi * var) + (z - self.params["theta"])**2 / var, axis=1))
        logits -= logits.max()
        probs = np.exp(logits)
        return probs / probs.sum()

    def predict(self, x, threshold=0.80, margin=0.15):
        probs = self.probabilities(x)
        order = np.argsort(probs)
        confidence = float(probs[order[-1]])
        accepted = confidence >= threshold and confidence - probs[order[-2]] >= margin
        label = self.labels[order[-1]] if accepted else "rejected"
        return label, confidence

    def save(self, path):
        write_json(path, {"schema": MODEL_SCHEMA, "feature_schema": FEATURE_SCHEMA,
                          "kind": self.kind, "labels": self.labels, "mean": self.mean.tolist(),
                          "scale": self.scale.tolist(), "params": {k: v.tolist() for k, v in self.params.items()},
                          "report": self.report})

    @classmethod
    def load(cls, path):
        d = read_json(path)
        labels = d.get("labels", [])
        if (d.get("schema") != MODEL_SCHEMA or d.get("feature_schema") != FEATURE_SCHEMA
                or d.get("kind") not in ("logistic", "gaussian_nb") or not isinstance(labels, list)
                or not 3 <= len(labels) <= 32 or len(set(labels)) != len(labels)
                or not all(label_valid(s) for s in labels) or not {"neutral", "confusing"} <= set(labels)):
            raise ValueError("Unsupported model/feature schema or labels")
        n = len(labels)
        mean, scale = array(d["mean"], (FEATURE_DIM,)), array(d["scale"], (FEATURE_DIM,))
        if np.any(scale <= 0):
            raise ValueError("Invalid model scale")
        p = d["params"]
        if d["kind"] == "logistic":
            params = {"coef": array(p["coef"], (n, FEATURE_DIM)), "intercept": array(p["intercept"], (n,))}
        else:
            params = {"theta": array(p["theta"], (n, FEATURE_DIM)), "var": array(p["var"], (n, FEATURE_DIM)),
                      "prior": array(p["prior"], (n,))}
            if np.any(params["var"] <= 0) or np.any(params["prior"] <= 0):
                raise ValueError("Invalid Gaussian parameters")
        return cls(d["kind"], labels, mean, scale, params, d.get("report", {}))


def materialize(sessions):
    x, y = [], []
    for session in sessions:
        for clip in session.clips:
            for _, feature in windows(clip.frames):
                x.append(feature)
                y.append(clip.label)
    if not x:
        raise ValueError("No valid temporal windows; capture longer clips with stable tracking")
    return np.stack(x), np.array(y)


def train(sessions, holdout, kind="logistic", by_person=False, threshold=0.80, margin=0.15, dwell=0.15):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import GaussianNB
    from sklearn.metrics import classification_report, confusion_matrix
    import sklearn
    from .evaluation import evaluate_events
    if len({s.id for s in sessions}) != len(sessions):
        raise ValueError("Duplicate session IDs: cannot form an independent holdout")
    key = (lambda s: s.person) if by_person else (lambda s: s.id)
    train_sessions = [s for s in sessions if key(s) not in set(holdout)]
    test_sessions = [s for s in sessions if key(s) in set(holdout)]
    if not train_sessions or not test_sessions:
        raise ValueError("Choose independent training and held-out sessions/persons")
    # Partition full sessions BEFORE producing any overlapping windows.
    x, y = materialize(train_sessions)
    xt, yt = materialize(test_sessions)
    labels = sorted(set(y))
    if (not {"neutral", "confusing"} <= set(labels) or len(labels) < 3
            or set(yt) != set(labels)):
        raise ValueError("Both splits must contain neutral, confusing and every trained action label")
    counts = {label: int(np.sum(y == label)) for label in labels}
    if min(counts.values()) < 5:
        raise ValueError("Capture at least five valid windows per label in training")
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    models, reports = {}, {}
    for name, estimator in [("logistic", LogisticRegression(C=1., class_weight="balanced", max_iter=2000,
                                                           random_state=7)),
                            ("gaussian_nb", GaussianNB(var_smoothing=1e-6))]:
        estimator.fit(z, y)
        if name == "logistic":
            params = {"coef": estimator.coef_, "intercept": estimator.intercept_}
        else:
            params = {"theta": estimator.theta_, "var": estimator.var_, "prior": estimator.class_prior_}
        model = Model(name, list(estimator.classes_), scaler.mean_, scaler.scale_, params)
        pred = [model.predict(f, threshold, margin)[0] for f in xt]
        reports[name] = {"classification": classification_report(yt, pred, labels=labels,
                                                                 output_dict=True, zero_division=0),
                         "confusion_labels": labels + ["rejected"],
                         "confusion_matrix": confusion_matrix(yt, pred, labels=labels + ["rejected"]).tolist(),
                         "rejection_rate": float(np.mean(np.array(pred) == "rejected")),
                         "events": evaluate_events(model, test_sessions, threshold, margin, dwell)}
        models[name] = model
    if kind not in models:
        raise ValueError("Choose logistic or gaussian_nb before inspecting holdout results")
    chosen = models[kind]
    chosen.report = {"selected_before_evaluation": kind, "comparison": reports,
                     "train_sessions": [s.id for s in train_sessions],
                     "holdout_sessions": [s.id for s in test_sessions], "split_by": "person" if by_person else "session",
                     "training_window_counts": counts, "holdout_window_count": len(yt),
                     "threshold": threshold, "margin": margin, "dwell_seconds": dwell,
                     "dependencies": {"numpy": np.__version__, "scikit-learn": sklearn.__version__},
                     "evidence": "synthetic-test only; no real-world accuracy" if any(
                         s.source == "synthetic-test" for s in sessions) else "locally recorded sessions; personal holdout only",
                     "warning": "Comparison is descriptive; choosing/tuning using this holdout invalidates final-test claims."}
    return chosen
