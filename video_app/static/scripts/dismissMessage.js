document.addEventListener('DOMContentLoaded', function() {
    var closeButtons = document.querySelectorAll('.closeFlashMessage');
    closeButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
            var flashMessage = this.parentElement;
            flashMessage.style.display = 'none';
        });
    });
});