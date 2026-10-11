import argparse
import json
import multiprocessing as mp


def main():
    mp.freeze_support()
    from .platforms import set_dpi_awareness
    set_dpi_awareness()
    parser = argparse.ArgumentParser(description="Mouse Invisível: personally trained local camera mouse")
    parser.add_argument("--diagnostics", action="store_true", help="Read-only OS/monitor diagnostics; no camera/input")
    parser.add_argument("--smoke-test", action="store_true", help="Create/close the GUI without camera/input")
    parser.add_argument("--replay", metavar="SESSION_JSON", help="Replay a saved session without native input")
    parser.add_argument("--model", metavar="MODEL_JSON", help="Numeric gesture model for replay")
    parser.add_argument("--profile", metavar="PROFILE_JSON", help="Optional mapping/calibration for replay")
    parser.add_argument("--check-libraries", action="store_true", help="Import native camera/training libraries without devices")
    parser.add_argument("--train", nargs="+", metavar="SESSION_JSON", help="Train from saved local sessions without native input")
    parser.add_argument("--holdout", nargs="+", help="Reserved session IDs or person identifiers")
    parser.add_argument("--by-person", action="store_true")
    parser.add_argument("--classifier", choices=["logistic", "gaussian_nb"], default="logistic")
    parser.add_argument("--output", help="Output numeric model JSON for --train")
    parser.add_argument("--check-worker", action="store_true", help="Probe frozen multiprocessing with a recording adapter only")
    args = parser.parse_args()
    if args.check_worker:
        from .input_worker import probe_recording_worker
        print(json.dumps(probe_recording_worker()))
        return
    if args.check_libraries:
        import cv2
        import mediapipe
        from mediapipe.tasks.python.vision import HandLandmarker
        import sklearn
        print(json.dumps({"opencv": cv2.__version__, "mediapipe": mediapipe.__version__,
                          "landmarker": HandLandmarker.__name__, "sklearn": sklearn.__version__,
                          "devices_opened": False}))
        return
    if args.train:
        if not args.holdout or not args.output:
            parser.error("--train requires --holdout and --output")
        from .dataset import Session
        from .model import train
        model = train([Session.load(p) for p in args.train], args.holdout,
                      args.classifier, args.by_person)
        model.save(args.output)
        print(json.dumps(model.report, indent=2, ensure_ascii=False))
        return
    if args.replay:
        if not args.model:
            parser.error("--replay requires --model")
        from .replay import replay_session
        from .dataset import Session
        from .model import Model
        from .profile import Profile
        output = replay_session(Session.load(args.replay), Model.load(args.model),
                                Profile.load(args.profile) if args.profile else None)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return
    if args.diagnostics:
        from .platforms import diagnostics
        print(json.dumps(diagnostics(), indent=2, ensure_ascii=False))
        return
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from .gui import Window
    app = QApplication([])
    app.setApplicationName("Mouse Invisível")
    window = Window()
    window.show()
    if args.smoke_test:
        QTimer.singleShot(100, window.close)
        QTimer.singleShot(200, app.quit)
    return app.exec()


if __name__ == "__main__":
    main()
