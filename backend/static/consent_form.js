// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})
window.addEventListener("load", function () {
    // do things after the DOM loads fully
    console.log("Everything is loaded");

    var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
        backdrop: 'static',
        keyboard: false
    });

    let cont = document.getElementById('continue');
    cont.addEventListener('click', function (ev) {
        myModal.hide()
    });

    to_show = cont.dataset.show
    console.log(typeof(to_show))
    if (to_show == "True") {
        myModal.show();
    }
});

