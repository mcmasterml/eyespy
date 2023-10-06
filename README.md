# EyeSpy

### Automating Video Detections

Presenting EyeSpy, a service which takes video and returns object detection and tracking analytics.

A live deployment is freely accessible [here](https://eyespy.petermcmaster.me)

Motivation for this project comes from a passion for Computer Vision models and a recognition of the current business need for automating surveillance. The idea is to feed video through an object detector (in this case, the YOLOv8 model from [ultralytics](https://github.com/ultralytics/ultralytics)) and return a dataframe and images from objects of interest (i.e. people, cars, etc.)

In this way, the task of monitoring nefarious activity becomes streamlined by the creation of a tabular dataset of everything detected within the video. This allows users to search, scrub, and identify much faster than was previously possible.

It's live!

Alternatively, you can run a local deployment by cloning this repository and following these steps:

1. Install [Docker](https://docs.docker.com/engine/install/), Start the Docker Daemon and ensure it is running.
2. `cd` into the clone of this directory
3. run `docker-compose build`
4. run `docker-compose up`
5. Go to `http://127.0.0.1:8000` in a web browser

# The Architecture

### 1. The Application

This is a python Flask app which utilizes a custom-trained version of the [ultralytics](https://github.com/ultralytics/ultralytics) YOLOv8 model and [opencv](https://github.com/opencv/opencv) as the primary tools for video processing and analytics delivery.

The Flask application is found in the `video_app` folder, and it's here that all the heavy lifting is done. `video_app/routes/` contains the routes of the application. The helper functions are in `video_app/utils.py`. The app is constructed with a modular architecture for separating `testing` and `development` from `production` environments which can be found in `surveil/config.py` file. The UI consists in three `html` pages in `video_app/templates/`.

### 2. Docker Deployment

Two Docker containers work in tandem to deploy this application (and separate front-end from back-end). A Flask container, built from `Dockerfile.flask`, houses the back-end Flask application and serves on port 5000. The nginx container built from `Dockerfile.nginx` serves the application to the world on port 8000. `docker-compose.yml` is utilized to build them together with `docker-compose`.

### 3. AWS Deployment

To properly auto-scale the resources needed and load-balance the network requests, I have utilized AWS. Specifically, I have defined a cluster which hosts these two Docker containers on an t4x.large EC2 instance. Auto-scaling is set to 4 servers, each of which can serve up to 16 requests at a time. I don't expect usage of this app to exceed 64 in my use case. If it were to achieve the grandeur of actual production, I can simple spin up a new ECS Cluster with a larger maximum.

For data persistence and model monitoring, I am utilizing an AWS S3 bucket to capture the images and dataframes gathered from the user inputs.

That's my app, thank you for using. Enjoy!
