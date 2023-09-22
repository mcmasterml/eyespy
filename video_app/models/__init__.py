from ultralytics import YOLO
import lap


def load_model(model_type):

    weights_selection_mapping = {
        "nano": "yolov8n.pt",
        "medium": "yolov8m.pt",
        "XL": "yolov8x.pt",
        "custom": "best.pt"
    }

    model_weights = 'weights/' + \
        weights_selection_mapping.get(
            model_type, "yolov8n.pt")  # default to nano
    model = YOLO(model_weights)
    return model
