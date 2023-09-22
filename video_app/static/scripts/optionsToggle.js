document.getElementById('toggleOptions').addEventListener('click', function() {
    var container = document.getElementById('optionsContainer');
    if(container.style.display === "none") {
        container.style.display = "flex";
    } else {
        container.style.display = "none";
    }
});