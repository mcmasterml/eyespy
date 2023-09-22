from flask import session, current_app
import pandas as pd
import numpy as np
import cv2
import os
import boto3
from botocore.exceptions import ClientError
import logging
import datetime
from werkzeug.datastructures import FileStorage
import magic
from dotenv import load_dotenv
import isodate
import re
import requests

logger = logging.getLogger('video_app')


def is_allowed_video(file: FileStorage) -> bool:
    """
    Check if the uploaded file is a valid video based on its MIME type.
    """
    # allowed MIME types
    allowed_mimetypes = ['video/mp4', 'video/quicktime']

    # read first 2 KB to determine MIME type
    file_content = file.stream.read(2048)
    file.stream.seek(0)  # reset the file stream so it can be saved later

    mime = magic.from_buffer(file_content, mime=True)

    return mime in allowed_mimetypes


def has_allowed_extension(filename):
    """
    string validation for allowed video extensions
    """
    allowed_extensions = ['mp4', 'mov']
    return ('.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions)


def generate_filename():
    """
    generates a filename for the csv
    """
    return f"detections_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def get_frame_rate(VIDEO):
    """
    gets fps of uploaded video
    """
    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return fps


def extract_video_id(url):
    """ 
    Extracts the video id from a YouTube URL
    """
    match = re.search(
        r"youtube\.com\/watch\?v=([^\&]+)", url) or re.search(r"youtu\.be\/([^\&]+)", url)
    return match.group(1) if match else None


def get_video_duration(video_id, api_key):
    """
    Gets the duration of a YouTube video
    """
    endpoint = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=contentDetails&key={api_key}"
    try:
        response = requests.get(endpoint)
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return None
    data = response.json()

    if not data.get('items'):
        logger.error(f"No video found at that URL: {endpoint}")
        return None

    duration = data['items'][0]['contentDetails']['duration']
    return duration


def get_df(list_results, VIDEO, YOUTUBE):
    """
    Takes results from YOLO model and returns a dataframe with the following columns:
    xmin, ymin, xmax, ymax, track_id, confidence, class_id, frame_num
    Each row is a detection from a frame frame_num
    """
    xmin = []
    ymin = []
    xmax = []
    ymax = []
    track_id = []
    confidence = []
    class_id = []
    frame_num = []
    timestamps = []

    frame = 0

    if not YOUTUBE:
        fps = get_frame_rate(VIDEO)

        for frame_result in list_results:
            frame += 1
            for i in range(len(frame_result.boxes.data.numpy()[:])):
                # Check if the detection is of length 7, (when it has low confidence it is outputting length 6)
                if frame_result.boxes.data.numpy()[:][i].size == 7:
                    xmin.append(frame_result.boxes.data.numpy()
                                [:][i][0])  # xmin
                    ymin.append(frame_result.boxes.data.numpy()
                                [:][i][1])  # ymin
                    xmax.append(frame_result.boxes.data.numpy()
                                [:][i][2])  # xmax
                    ymax.append(frame_result.boxes.data.numpy()
                                [:][i][3])  # ymax
                    track_id.append(frame_result.boxes.data.numpy()
                                    [:][i][4])  # track_id
                    confidence.append(frame_result.boxes.data.numpy()[
                        :][i][5])  # confidence
                    class_id.append(frame_result.boxes.data.numpy()
                                    [:][i][6])  # class_id
                    frame_num.append(frame)  # frame
                    timestamps.append(frame / fps)  # timestamp
                else:
                    print("No detections in frame ", frame, " of lenght 7")
                    pass

    if YOUTUBE:
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(env_path)
        API_KEY = os.environ.get('YOUTUBE_API_KEY')
        video_id = extract_video_id(VIDEO)  # VIDEO is YouTube URL
        duration_ = get_video_duration(video_id, API_KEY)
        duration = isodate.parse_duration(duration_).total_seconds()

        duration_per_frame = duration / len(list_results)

        for frame_result in list_results:
            frame += 1
            for i in range(len(frame_result.boxes.data.numpy()[:])):
                # Check if the detection is of length 7, (when it has low confidence it is outputting length 6)
                if frame_result.boxes.data.numpy()[:][i].size == 7:
                    xmin.append(frame_result.boxes.data.numpy()
                                [:][i][0])  # xmin
                    ymin.append(frame_result.boxes.data.numpy()
                                [:][i][1])  # ymin
                    xmax.append(frame_result.boxes.data.numpy()
                                [:][i][2])  # xmax
                    ymax.append(frame_result.boxes.data.numpy()
                                [:][i][3])  # ymax
                    track_id.append(frame_result.boxes.data.numpy()
                                    [:][i][4])  # track_id
                    confidence.append(frame_result.boxes.data.numpy()[
                        :][i][5])  # confidence
                    class_id.append(frame_result.boxes.data.numpy()
                                    [:][i][6])  # class_id
                    frame_num.append(frame)  # frame
                    timestamps.append(frame * duration_per_frame)  # timestamp
                else:
                    print("No detections in frame ", frame, " of lenght 7")
                    pass

    # dict
    data = {'frame_num': frame_num,
            'timestamp': timestamps,
            'xmin': xmin,
            'ymin': ymin,
            'xmax': xmax,
            'ymax': ymax,
            'track_id': track_id,
            'confidence': confidence,
            'class_id': class_id}

    df = pd.DataFrame(data=data)
    print("DataFrame created from model results")
    return df


def seconds_to_mmss(seconds):
    """
    Convert a float number of seconds into 'MM:SS' format.
    """
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02}:{seconds:02}"


def get_summary_df(df, labels):
    """
    Create a summary dataframe from the detections dataframe 
    to be presented to the user
    """
    grouped = df.groupby('track_id')

    # Extract data for each track_id
    label = grouped['class_id'].first().map(labels.get)
    timestamp_enter = grouped['timestamp'].min()
    timestamp_exit = grouped['timestamp'].max()
    confidence = grouped['confidence'].max()

    # NOTE: 'timestamp' becomes 'time enter' / 'time exit'
    summary_df = pd.DataFrame({
        'track id': label.index,
        'label': label.values,
        'time enter': timestamp_enter.values,
        'time exit': timestamp_exit.values,
        'confidence': confidence.values
    })

    # Convert float seconds into 'MM:SS' format
    summary_df['time enter'] = summary_df['time enter'].apply(
        seconds_to_mmss)
    summary_df['time exit'] = summary_df['time exit'].apply(
        seconds_to_mmss)

    # Cast 'track id' column as int
    summary_df['track id'] = summary_df['track id'].astype(int)

    # Round the 'confidence' column to 2 decimal places
    summary_df['confidence'] = summary_df['confidence'].round(2)

    return summary_df


def get_middle_frames(df, track_ids):
    """ 
    Returns a dict which stores {track_id: sought_frame} for each track_id in track_ids
    """
    middle_frames = {}
    for track_id in track_ids:
        first_frame_num = df.loc[df['track_id']
                                 == track_id, 'frame_num'].min()
        last_frame_num = df.loc[df['track_id']
                                == track_id, 'frame_num'].max()
        middle_frame_num = int((last_frame_num + first_frame_num) // 2)

        sought_frame = (middle_frame_num - 4)
        while df.loc[(df['track_id'] == track_id) & (df['frame_num'] == sought_frame)].empty:
            sought_frame += 1

        middle_frames[track_id] = sought_frame
    return middle_frames


def get_images(df, labels, VIDEO, middle_frames, IMAGE_FOLDER):
    """ 
    Takes middle frames dict and video file path to save images of middle frames per object
    with bounding boxes, labels, and confidence
    """
    # read video
    try:
        video = cv2.VideoCapture(VIDEO)
        if not video.isOpened():
            logger.error(f"Unable to open video file: {VIDEO}")
            return
        # frame rate
        fps = video.get(cv2.CAP_PROP_FPS)

        # open video stream
        frame_counter = 0
        while video.isOpened():
            ret, frame = video.read()
            if not ret:
                break
            frame_counter += 1

            # draw bounding boxes, labels, and confidence
            for track_id in middle_frames.keys():
                if frame_counter == middle_frames[track_id]:
                    x1 = int(round(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'xmin'].iloc[0]))
                    y1 = int(round(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'ymin'].iloc[0]))
                    x2 = int(round(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'xmax'].iloc[0]))
                    y2 = int(round(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'ymax'].iloc[0]))
                    this_confidence = round(float(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'confidence'].iloc[0]), 3)
                    this_class_id = int(round(df.loc[(df['track_id'] == track_id) & (
                        df['frame_num'] == middle_frames[track_id]), 'class_id'].iloc[0]))

                    # Labels for all 80 classes from `Detections.labels` via `model.names`
                    this_label = labels[this_class_id]

                    # Draw bounding box, label, and confidence
                    cv2.rectangle(frame, (x1, y1),
                                  (x2, y2), (200, 0, 200), 2)
                    cv2.putText(frame, this_label + " " + str(this_confidence),
                                (x1, y2 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (155, 20, 155), 2)

                    # Write Image
                    image_path = os.path.join(
                        IMAGE_FOLDER, f"detection{int(track_id)}_{this_label}.jpg")
                    cv2.imwrite(image_path, frame)

        video.release()
        cv2.destroyAllWindows()
        print('SUCCESSFULLY wrote images to: ', IMAGE_FOLDER)
    except Exception as e:
        logger.error(f"Error processing video {video}: {e}")
    return os.listdir(IMAGE_FOLDER)


def upload_to_s3(file_name, bucket, object_name=None):
    """
    Upload images and csv to S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

    # Determine the "folder" in which the file should be stored in the bucket
    if file_name.endswith('.jpg'):
        s3_folder = 'video-app-data/images/'
    elif file_name.endswith('.csv'):
        s3_folder = 'video-app-data/csvs/'
    else:
        s3_folder = ''

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = s3_folder + os.path.basename(file_name)
    else:
        object_name = s3_folder + object_name

    # Upload the file
    s3_client = boto3.client('s3', aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                             aws_access_key_id=AWS_ACCESS_KEY_ID)
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logger.error(e)
        return False
    return True


class Detections:
    """ 
    Takes a generator object from YOLO model
    to return parsed data:
    - dataframe with columns: 'frame_num', 'timestamp', 'xmin', 'ymin', 'xmax', 'ymax', 
                              'track_id', 'confidence', 'class_id'
    - number of people
    - number of bikes
    - number of cars
    and write images to a folder
    """

    def __init__(self):
        """ TODO: add docstring
        """
        self.results = []
        self.df = None
        self.track_ids = None
        self.csv = None
        self.html = None
        self.labels = None

    def process_video(self, model, VIDEO, CLASSES, YOUTUBE):
        try:
            logger.info('Video processing has begun')
            self.results = list(model.track(source=VIDEO, conf=0.5, iou=0.5,
                                classes=CLASSES, tracker="bytetrack.yaml"))
            self.df = get_df(self.results, VIDEO, YOUTUBE)
            self.labels = model.names
            self.summary_df = get_summary_df(self.df, self.labels)
            self.track_ids = self.df['track_id'].unique()
            self.csv = self.summary_df.to_csv(index=False)
            self.html = self.summary_df.to_html(
                classes='dataframe', index=False)
            logger.info('Video processing has finished')
        except ValueError as e:
            logger.error(f'ValueError in process_video(): {e}')
        return

    def write_images(self, VIDEO, IMAGE_FOLDER):
        """Draws bounding boxes on a frame from the video
        """
        logger.info('Class Detections method write_images() has begun')
        middle_frames = get_middle_frames(self.df, self.track_ids)
        images = get_images(self.df, self.labels, VIDEO,
                            middle_frames, IMAGE_FOLDER)
        logger.info('images successfully written locally')
        return images

    def write_csv(self, CSV_FOLDER):
        """Writes csv to a folder
        """
        filename = generate_filename()
        csv_path = os.path.join(CSV_FOLDER, filename)
        with open(csv_path, 'w') as f:
            f.write(self.csv)
        logger.info('csv successfully written locally')
        return csv_path

    def write_all_to_s3(self, IMAGE_FOLDER, CSV_FOLDER, bucket):

        # Write images to s3
        full_image_paths = [os.path.join(IMAGE_FOLDER, filename) for filename in os.listdir(
            IMAGE_FOLDER) if os.path.isfile(os.path.join(IMAGE_FOLDER, filename))]
        for image in full_image_paths:
            upload_to_s3(image, bucket)
        logger.info('images successfully written to s3 bucket')

        # Write csv to s3
        full_csv_paths = [os.path.join(CSV_FOLDER, filename) for filename in os.listdir(
            CSV_FOLDER) if os.path.isfile(os.path.join(CSV_FOLDER, filename))]
        for csv in full_csv_paths:
            upload_to_s3(csv, bucket)
        logger.info('csv successfully written to s3 bucket')
        return