from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template
from flask import request, Response, session, url_for, send_from_directory, send_file

from threading import Thread
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from video_app.utils import Detections, is_allowed_video, has_allowed_extension, upload_to_s3, extract_video_id, get_video_duration, download_video_from_youtube
from video_app.models import load_model

from io import BytesIO

import sys
import time
import os
import boto3
import magic
import logging
import zipfile
import re
import requests
import isodate

from dotenv import load_dotenv

logger = logging.getLogger('video_app')

main = Blueprint('main', __name__)


@main.route('/')
def home():
    ''' 
    renders the upload form at upload.html, 
    deletes local files in `temp_data` as upload.html calls /delete_files
    '''
    logger.info('"/" route was hit')
    return render_template('upload.html')


@main.route('/upload', methods=['POST'])
def upload():
    """
    Takes user input from the upload form, validates it, and saves it locally
    """
    try:
        # Input
        # User Input video file or YouTube URL
        uploaded_file = request.files.get('video_file', None)
        video_url = request.form.get('video_url', "").strip()

        # Handle User Input for Detections
        selected_detections = request.form.getlist('detections')
        # Define mapping between selections and detection classes
        meta_class_mapping = {
            'People': [0],
            'Vehicles': list(range(1, 9)),
            'Traffic_Signs': list(range(9, 14)),
            'Animals': list(range(14, 24)),
            'Sports_Equipment': list(range(24, 39)),
            'Food': list(range(39, 56)),
            'Household_Items': list(range(56, 80))
        }
        # Create a list of all classes to be detected
        classes = []
        for detection in selected_detections:
            classes.extend(meta_class_mapping.get(detection, []))
        # Save the list of classes in the session
        session['CLASSES'] = classes

        # Handle User Input for select Model
        selected_model = request.form.get('singleSelectModel')
        # save the selected_model in the session
        session['MODEL'] = selected_model

        # Messaging (for simple errors, show exit-able message. For all others, error.html)
        # Neither URL nor file was provided
        if not uploaded_file and not video_url:
            flash('Please provide either a video file or a YouTube URL')
            return redirect(url_for('main.home'))
        # Both URL and file were provided (should never happen due to dropZone.js logic)
        if uploaded_file and video_url:
            flash('Please only provide one: a video file or a YouTube URL')
            return redirect(url_for('main.home'))
        # Detections were not selected
        if not selected_detections:
            flash('Please select at least one detection from Additional Options')
            return redirect(url_for('main.home'))

        # File Validation
        # Case: file upload via dropZone
        if uploaded_file and not video_url:
            if not uploaded_file.filename:
                raise BadRequest('Uploaded file has no name')
            # or not has_allowed_extension(uploaded_file):
            elif not is_allowed_video(uploaded_file):
                raise BadRequest(
                    'Uploaded file is not an allowed video type. Accepted types: .mp4, .mov')
            # Check file size, limit 500MB
            file_size_mb = int(request.headers.get(
                'Content-Length', 0)) / (1024 * 1024)
            if file_size_mb > 500:
                raise BadRequest('Uploaded file size exceeds the 500MB limit')
            # Save the file locally
            filename = secure_filename(uploaded_file.filename)
            VIDEO_FOLDER = current_app.config['VIDEO_FOLDER']
            video_file_path = os.path.join(VIDEO_FOLDER, filename)
            uploaded_file.save(video_file_path)
            # Store uploaded video path in session
            session['YOUTUBE'] = False
            session['VIDEO_SOURCE'] = video_file_path

        # Case: YouTube URL
        logger.info(f"video_url: {video_url}")
        if not uploaded_file and video_url:
            # String begins with https://www.youtube.com/watch?v= or https://youtu.be/
            if not (video_url.startswith('https://www.youtube.com/watch?v=') or video_url.startswith('https://youtu.be/')):
                raise BadRequest(
                    'YouTube URL is invalid. Must begin with "https://www.youtube.com/watch?v=" or "https://youtu.be/"')             
            # Check video length, limit 10 minutes
            video_id = extract_video_id(video_url)
            API_KEY = os.environ.get('YOUTUBE_API_KEY')
            duration_ = get_video_duration(video_id, API_KEY)
            duration = isodate.parse_duration(duration_).total_seconds()
            logger.info(f"Video duration: {duration}")
            if int(duration) > 600:
                raise BadRequest(
                    'YouTube video is longer than the 10-minute limit. Please provide a shorter video.')
            # download the video locally with pytube
            VIDEO_FOLDER = current_app.config['VIDEO_FOLDER']
            downloaded_video = download_video_from_youtube(video_url, VIDEO_FOLDER)
            logger.info(f"downloaded_video: {downloaded_video}")
            # TODO: Revisit this logic. the filename will have spaces and odd characters...
            # No longer used werkzeug secure_filename here...

            # Save YouTube URL in session
            session['YOUTUBE'] = True
            session['VIDEO_SOURCE'] = downloaded_video

        return render_template('loading.html')

    except Exception as e:
        return render_template('error.html', error_message=str(e))


@main.route('/processing')
def processing():
    """ 
    process video, write images & csv to s3, serve images & csv to user
    """
    logger.info("Processing route was hit!")
    load_dotenv()
    try:
        # Load model using cache
        selected_model_type = session.get('MODEL')
        # If model not in cache, load it and save it in cache
        if selected_model_type not in current_app.model_cache:
            current_app.model_cache[selected_model_type] = load_model(
                selected_model_type)
        # Get the model from cache
        model = current_app.model_cache[selected_model_type]

        # Process video
        detectionsInVideo = Detections()
        VIDEO = session.get('VIDEO_SOURCE')
        YOUTUBE = session.get('YOUTUBE')
        CLASSES = session.get(
            'CLASSES', [0, 1, 2, 3, 4, 5, 6, 7, 8])  # default: people & vehicles
        detectionsInVideo.process_video(model, VIDEO, CLASSES, YOUTUBE)

        S3_BUCKET = os.environ.get('S3_BUCKET_NAME')

        # Write csv locally
        CSV_FOLDER = current_app.config['CSV_FOLDER']
        csv_path = detectionsInVideo.write_csv(CSV_FOLDER)
        # Write csv to S3 Bucket
        upload_to_s3(csv_path, S3_BUCKET)

        # save csv to session for serving download from /download_csv
        session['CSV'] = csv_path

        # serve csv to user as csv_info as (filename, url)
        table_html = detectionsInVideo.html

        # Only serve images if not YouTube
        image_info = None

        # TODO: if youtube, download file locally with pytube first


        # TODO: make sure this works for all cases, not just not YouTube
        # If local file (not YouTube), write and serve images
        if not YOUTUBE:
            # Write images locally
            IMAGE_FOLDER = current_app.config['IMAGE_FOLDER']
            detectionsInVideo.write_images(VIDEO, IMAGE_FOLDER)
            # Write images to S3 Bucket
            full_image_paths = [os.path.join(IMAGE_FOLDER, filename) for filename in os.listdir(
                IMAGE_FOLDER) if os.path.isfile(os.path.join(IMAGE_FOLDER, filename))]
            for image in full_image_paths:
                upload_to_s3(image, S3_BUCKET)
            logger.info('images successfully written to s3 bucket')

            # serve images to user as image_info as (filename, url)
            IMAGE_FOLDER = current_app.config['IMAGE_FOLDER']
            images = [f for f in os.listdir(IMAGE_FOLDER) if (
                f.lower().endswith('.jpg') or f.lower().endswith('.jpeg'))]
            image_info = [(f, url_for('main.serve_image', filename=f))
                          for f in images]

        return render_template('results.html', youtube=YOUTUBE, image_info=image_info, table_html=table_html)
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@main.route('/delete_files')
def delete_files_locally():
    """ 
    deletes the local files from previous sessions.
    called from 'upload.html' on page load
    """
    try:
        IMAGE_FOLDER = current_app.config['IMAGE_FOLDER']
        CSV_FOLDER = current_app.config['CSV_FOLDER']
        VIDEO_FOLDER = current_app.config['VIDEO_FOLDER']

        files_deleted = 0
        errors = []

        # Remove all files
        for directory in [IMAGE_FOLDER, CSV_FOLDER, VIDEO_FOLDER]:
            for root, dirs, files in os.walk(directory, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                        logger.info(f"Deleted file {file_path}")
                    except Exception as e:
                        error_msg = f"Error deleting file {file_path}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)

        response_delete_data = {
            "success": len(errors) != 0,
            "files_deleted": files_deleted,
            "errors": errors
        }
        logger.info("files deleted successfully!")
        return jsonify(response_delete_data), 200 if len(errors) == 0 else 500
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@main.errorhandler(BadRequest)
def handle_bad_request(e):
    """ 
    Handle errors, show message to user from error.html
    """
    return render_template('error.html', error_message=str(e))


@main.route('/images/<filename>')
def serve_image(filename):
    """ 
    serve images, called from /processing route
    only available for uploaded videos (not YouTube)
    """
    try:
        IMAGE_FOLDER = current_app.config['IMAGE_FOLDER']
        return send_from_directory(IMAGE_FOLDER, filename)
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@main.route('/download_images')
def download_images():
    """ 
    serve images when user clicks on 'Download Images' button in 'results.html'
    only available for uploaded videos (not YouTube)
    """
    try:
        image_folder = current_app.config['IMAGE_FOLDER']

        # Create a Zip file on-the-fly
        in_memory_zip = BytesIO()
        with zipfile.ZipFile(in_memory_zip, 'w') as zf:
            for image_name in os.listdir(image_folder):
                zf.write(os.path.join(image_folder, image_name),
                         arcname=image_name)

        in_memory_zip.seek(0)
        return send_file(in_memory_zip,
                         download_name='images.zip',
                         as_attachment=True)
    except Exception as e:
        return render_template('error.html', error_message=str(e))


@main.route('/download_csv')
def download_csv():
    """
    serve csv when user clicks on 'Download CSV' button in 'results.html' 
    """
    try:
        # Fetch csv file path from session
        csv_file_path = session.get('CSV')

        if csv_file_path is None or not os.path.exists(csv_file_path):
            raise BadRequest("CSV file not found")

        # Read the content of the csv file
        with open(csv_file_path, 'r') as file:
            csv_data = file.read()

        # Create a response with csv data, content_type, headers, and a filename
        csv_response = Response(csv_data, content_type='text/csv')
        csv_response.headers['Content-Disposition'] = 'attachment; filename=detections.csv'

        return csv_response
    except Exception as e:
        return render_template('error.html', error_message=str(e))
