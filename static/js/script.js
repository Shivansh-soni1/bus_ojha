document.addEventListener("DOMContentLoaded", function () {
    const searchForm = document.getElementById("searchForm");
    const loadingOverlay = document.getElementById("loading-overlay");
    if (searchForm) {
        searchForm.addEventListener("submit", function (event) {
            loadingOverlay.style.display = "flex";
            setTimeout(() => { document.querySelector(".loading-text").innerText = "Testing Reliability Scores..."; }, 4000);
        });
    }

    // Replace this with your actual Geoapify API key
    const GEOAPIFY_API_KEY = "57e420cd91b64223bc484b98e702f0df"; 

    function setupGeoapifyAutocomplete(inputId, listId, hiddenLatId, hiddenLonId) {
        const input = document.getElementById(inputId);
        const list = document.getElementById(listId);
        const hiddenLat = document.getElementById(hiddenLatId);
        const hiddenLon = document.getElementById(hiddenLonId);
        
        if (!input || !list) return;

        let timeout = null;

        input.addEventListener('input', function() {
            clearTimeout(timeout);
            const val = this.value;
            
            if (!val || val.length < 2) {
                list.style.display = 'none';
                return;
            }

            timeout = setTimeout(() => {
                // Fetch from Geoapify. Filter by countrycode=in for India.
                const url = `https://api.geoapify.com/v1/geocode/autocomplete?text=${encodeURIComponent(val)}&type=city&filter=countrycode:in&format=json&apiKey=${GEOAPIFY_API_KEY}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        list.innerHTML = '';
                        if (data.results && data.results.length > 0) {
                            data.results.forEach(result => {
                                const li = document.createElement('li');
                                // Display formatted address, e.g., "Mumbai, Maharashtra, India"
                                li.textContent = result.formatted;
                                li.addEventListener('click', function() {
                                    // Extract just the city name for the input display
                                    input.value = result.city || result.name || result.formatted.split(',')[0];
                                    
                                    // Set hidden fields with precise coordinates to speed up backend
                                    if (hiddenLat && hiddenLon) {
                                        hiddenLat.value = result.lat;
                                        hiddenLon.value = result.lon;
                                    }

                                    list.style.display = 'none';
                                });
                                list.appendChild(li);
                            });
                            list.style.display = 'block';
                        } else {
                            list.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error("Geoapify Error:", error);
                    });
            }, 300); // debounce 300ms
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== input && e.target !== list) {
                list.style.display = 'none';
            }
        });
    }

    setupGeoapifyAutocomplete('source-input', 'source-autocomplete', 'source-lat', 'source-lon');
    setupGeoapifyAutocomplete('dest-input', 'dest-autocomplete', 'dest-lat', 'dest-lon');
});