document.addEventListener('DOMContentLoaded', function () {
    const toggleBtn = document.querySelector(".toggle-btn");

    toggleBtn.addEventListener("click", function () {
        document.querySelector("#sidebar").classList.toggle("expand");
        document.querySelector(".main-content").classList.toggle("expand");
    });
});
