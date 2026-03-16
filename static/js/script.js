document.addEventListener("DOMContentLoaded", function() {
    const searchForm = document.getElementById("searchForm");
    const loadingOverlay = document.getElementById("loading-overlay");
    if (searchForm) {
        searchForm.addEventListener("submit", function(event) {
            loadingOverlay.style.display = "flex";
            setTimeout(() => { document.querySelector(".loading-text").innerText = "Testing Reliability Scores..."; }, 4000);
        });
    }
});