from ultralytics import YOLO
import ultralytics
import lap


# Change this to use different model_weights
model_weights = 'models/weights/yolov8n.pt'


# ultralytics.data.dataset.YOLODataset.get_labels
# ultralytics.data.base.BaseDataset.labels

model = YOLO(model_weights)
print(model.names)
