window.onload = function () {
    setTimeout(function() {
        fetch('/delete_files').then(response => {
            if (response.ok) {
                console.log("File deletion has begun.");
            } else {
                console.error("Failed to begin file deletion.");
            }
        });
    }, 5000);
};