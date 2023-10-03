document.querySelectorAll('input[name="uploadMethod"]').forEach(function(radio) {
    radio.addEventListener('change', function() {
        let selectedMethod = this.value;
        
        // Hide everything first
        document.getElementById('dropZoneHeader').style.display = 'none';
        document.getElementById('dropZone').style.display = 'none';
        document.getElementById('urlInputFieldHeader').style.display = 'none';
        document.getElementById('urlInputField').style.display = 'none';
        document.getElementById('webcamHeader').style.display = 'none';
        document.getElementById('additionalOptions').style.display = 'none';
        document.getElementById('getResultsButton').style.display = 'none';

        // Show based on the selection
        if (selectedMethod === 'fileUpload') {
            document.getElementById('dropZone').style.display = 'block';
            document.getElementById('dropZoneHeader').style.display = 'block';
            document.getElementById('additionalOptions').style.display = 'block';
            document.getElementById('getResultsButton').style.display = 'block';
        } else if (selectedMethod === 'youtubeURL') {
            document.getElementById('urlInputField').style.display = 'block';
            document.getElementById('urlInputFieldHeader').style.display = 'block';
            document.getElementById('additionalOptions').style.display = 'block';
            document.getElementById('getResultsButton').style.display = 'block';
        } else if (selectedMethod === 'useWebcam') {
            document.getElementById('webcamHeader').style.display = 'block';
        }
    });
});
