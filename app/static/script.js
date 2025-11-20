async function recommend() {
    const query = document.getElementById("query").value;
    const lat = parseFloat(document.getElementById("lat").value);
    const lon = parseFloat(document.getElementById("lon").value);

    if (!query || isNaN(lat) || isNaN(lon)) {
        alert("Please fill all fields");
        return;
    }

    const res = await fetch(
        `/recommend?query=${encodeURIComponent(query)}&user_lat=${lat}&user_lon=${lon}`
    );

    const data = await res.json();
    console.log("API response:", data);

    // Accept both: `[{}, {}]` or `{results: [...]}` 
    const results = Array.isArray(data) ? data : data.results;

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "";

    if (!results || results.length === 0) {
        resultsDiv.innerHTML = "<p>No restaurants found</p>";
        return;
    }

    results.forEach(r => {
        const div = document.createElement("div");
        div.className = "restaurant";
        div.innerHTML = `
            <h2>${r["Restaurant Name"]}</h2>
            <p><strong>Cuisines:</strong> ${r.Cuisines}</p>
            <p><strong>Rating:</strong> ${r["Aggregate rating"]} (${r["Rating text"]})</p>
            <p><strong>Distance:</strong> ${r.distance_km?.toFixed(2) ?? "?"} km</p>
            <p><strong>Address:</strong> ${r.Address}</p>
        `;
        resultsDiv.appendChild(div);
    });
}
