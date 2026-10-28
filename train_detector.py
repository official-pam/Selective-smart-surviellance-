"""Fine-tune pretrained YOLO weights on a labelled person detection dataset."""
import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="YOLO dataset YAML with separate train/val splits")
    parser.add_argument("--weights", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu", help="Use 0 for an available CUDA GPU")
    args = parser.parse_args()
    if not Path(args.data).is_file():
        parser.error("Dataset YAML does not exist.")
    model = YOLO(args.weights)
    result = model.train(data=args.data, epochs=args.epochs, batch=args.batch,
                         device=args.device, imgsz=640, patience=15, seed=42,
                         project="runs/detect", name="person_finetune", plots=True)
    best = Path(result.save_dir) / "weights" / "best.pt"
    print("Trained weights:", best)
    YOLO(str(best)).val(data=args.data, split="val", device=args.device)


if __name__ == "__main__":
    main()
