// Dragging file over dropZone changes background color
function dragOverHandler(ev) {
    ev.preventDefault();
    ev.currentTarget.style.backgroundColor = "#eee";
}

// Reset color when drag over leaves
function dragLeaveHandler(ev) {
    ev.currentTarget.style.backgroundColor = "";  // Reset background color when drag leaves
}

// Helper fxn. Show file details, possibly thumbnail, after drop or select
function showFileDetails(file) {
    // Display the name of the file in the dropZone
    document.getElementById('dropZone').textContent = "File selected: " + file.name;

    // If it's a video, create a thumbnail preview
    if (file.type.startsWith("video/")) {
        const videoElem = document.querySelector("#thumbnailPreview video");
        const videoSource = document.getElementById('videoSource');
        videoElem.style.display = "block";

        const objectURL = URL.createObjectURL(file);
        videoSource.src = objectURL;
        videoElem.load();

        document.getElementById('thumbnailPreview').style.display = "block";
    } else {
        document.getElementById('thumbnailPreview').style.display = "none";
    }
    document.getElementById('fileName').textContent = file.name;
}

// Handle drag n drop
function dropHandler(ev) {
    ev.preventDefault();

    // Reset file input, if any
    document.getElementById('video_file').value = '';

    // Clear previous video thumbnail and info, if any
    const videoSource = document.getElementById('videoSource');
    URL.revokeObjectURL(videoSource.src);
    videoSource.src = '';
    document.querySelector('#thumbnailPreview video').style.display = "none";
    document.getElementById('fileName').textContent = '';

    // Handle file from drag n drop
    if (ev.dataTransfer.items && ev.dataTransfer.items[0] && ev.dataTransfer.items[0].kind === 'file') {
        let file = ev.dataTransfer.items[0].getAsFile();
        document.getElementById('video_file').files = ev.dataTransfer.files;
        showFileDetails(file);  // Show file details
    }
    ev.currentTarget.style.backgroundColor = "";  // Reset color after drop
}

// Click listener for file selection
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('dropZone').addEventListener('click', function() {
        document.getElementById('video_file').click();
    })
});

// If drag n drop, disable YouTube URL input
// TODO: figure out why this wasn't working
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('video_file').addEventListener('change', function() {
        let urlField = document.querySelector('.urlInputField');
        if (this.files.length > 0) {
            urlField.disabled = true;
            urlField.value = "";
            showFileDetails(this.files[0]);
        } else {
            urlField.disabled = false;
        }
    })
});

// If URL input, disable file selection and drag n drop
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('urlInputField').addEventListener('input', function() {
        let fileInput = document.getElementById('video_file');
        if (this.value.trim() !== "") {
            fileInput.disabled = true;
        } else {
            fileInput.disabled = false;
        }
    })
});
