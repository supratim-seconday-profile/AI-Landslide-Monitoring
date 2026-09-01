// ============================================================
// NER LANDSLIDE EARLY WARNING SYSTEM
// LIVE DASHBOARD
// ============================================================


// ============================================================
// CONFIGURATION
// ============================================================

const API_BASE_URL = "http://127.0.0.1:8000";

const DEFAULT_LATITUDE = 27.338;
const DEFAULT_LONGITUDE = 88.606;

const RADIUS_KM = 5;

const REFRESH_INTERVAL = 30000; // 30 seconds

const HISTORY_LIMIT = 20;


// ============================================================
// MAP INITIALIZATION
// ============================================================

const map = L.map("map").setView(
    [DEFAULT_LATITUDE, DEFAULT_LONGITUDE],
    9
);


L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution:
            "&copy; OpenStreetMap contributors"
    }
).addTo(map);


// ============================================================
// MAP OBJECTS
// ============================================================

let selectedMarker = null;

let radiusCircle = null;

let riskMarkers = [];

let allRiskMarkers = [];


// ============================================================
// CURRENT LOCATION
// ============================================================

let selectedLatitude =
    DEFAULT_LATITUDE;

let selectedLongitude =
    DEFAULT_LONGITUDE;


// ============================================================
// RISK HISTORY CHART
// ============================================================

let riskHistoryChart = null;


// ============================================================
// MAP CLICK
// ============================================================

map.on("click", async function (event) {

    selectedLatitude =
        event.latlng.lat;

    selectedLongitude =
        event.latlng.lng;


    updateSelectedLocation();

    updateMapSelection();


    // --------------------------------------------------------
    // LIVE SATELLITE PREDICTION
    // --------------------------------------------------------

    await loadLivePrediction();


    // --------------------------------------------------------
    // DATABASE LOCAL RISK
    // --------------------------------------------------------

    await loadLocalRisk();


    // --------------------------------------------------------
    // RISK HISTORY
    // --------------------------------------------------------

    await loadRiskHistory();

});


// ============================================================
// UPDATE SELECTED LOCATION
// ============================================================

function updateSelectedLocation() {

    const locationElement =
        document.getElementById("location");


    if (!locationElement) {

        return;

    }


    locationElement.innerHTML = `

        <strong>
            Latitude:
        </strong>

        ${selectedLatitude.toFixed(5)}

        <br>

        <strong>
            Longitude:
        </strong>

        ${selectedLongitude.toFixed(5)}

    `;

}


// ============================================================
// UPDATE MAP SELECTION
// ============================================================

function updateMapSelection() {

    // --------------------------------------------------------
    // REMOVE OLD SELECTED MARKER
    // --------------------------------------------------------

    if (selectedMarker) {

        map.removeLayer(
            selectedMarker
        );

    }


    // --------------------------------------------------------
    // REMOVE OLD RADIUS
    // --------------------------------------------------------

    if (radiusCircle) {

        map.removeLayer(
            radiusCircle
        );

    }


    // --------------------------------------------------------
    // CREATE SELECTED MARKER
    // --------------------------------------------------------

    selectedMarker =
        L.marker(
            [
                selectedLatitude,
                selectedLongitude
            ]
        )
        .addTo(map)
        .bindPopup(`

            <strong>
                Selected Location
            </strong>

            <br>

            ${selectedLatitude.toFixed(5)},
            ${selectedLongitude.toFixed(5)}

        `)
        .openPopup();


    // --------------------------------------------------------
    // CREATE 5 KM RADIUS
    // --------------------------------------------------------

    radiusCircle =
        L.circle(
            [
                selectedLatitude,
                selectedLongitude
            ],
            {

                radius:
                    RADIUS_KM * 1000,

                color:
                    "#2563eb",

                fillColor:
                    "#2563eb",

                fillOpacity:
                    0.10

            }
        )
        .addTo(map);

}


// ============================================================
// LIVE SATELLITE PREDICTION
// ============================================================

async function loadLivePrediction() {

    try {

        const riskElement =
            document.getElementById(
                "risk"
            );


        if (riskElement) {

            riskElement.innerHTML = `

                <div>
                    ⏳ Fetching live satellite data...
                </div>

            `;

        }


        // ----------------------------------------------------
        // REQUEST LIVE PREDICTION
        // ----------------------------------------------------

        const response =
            await fetch(
                `${API_BASE_URL}/live-predict`,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            latitude:
                                selectedLatitude,

                            longitude:
                                selectedLongitude,

                            radius_km:
                                RADIUS_KM

                        })

                }
            );


        // ----------------------------------------------------
        // CHECK RESPONSE
        // ----------------------------------------------------

        if (!response.ok) {

            const errorText =
                await response.text();


            throw new Error(
                `HTTP ${response.status}: ${errorText}`
            );

        }


        // ----------------------------------------------------
        // READ RESPONSE
        // ----------------------------------------------------

        const data =
            await response.json();


        console.log(
            "LIVE PREDICTION:",
            data
        );


        // ----------------------------------------------------
        // RISK CLASS
        // ----------------------------------------------------

        let riskClass =
            "risk-low";


        if (
            data.risk_level === "HIGH"
        ) {

            riskClass =
                "risk-high";

        }

        else if (
            data.risk_level === "MEDIUM"
        ) {

            riskClass =
                "risk-medium";

        }


        // ----------------------------------------------------
        // RISK DETAILS
        // ----------------------------------------------------

        if (riskElement) {

            riskElement.innerHTML = `

                <div class="${riskClass}">

                    ${data.risk_level}

                </div>

                <br>

                <strong>
                    Landslide Probability:
                </strong>

                ${(
                    Number(
                        data.landslide_probability
                    ) * 100
                ).toFixed(2)}%

                <br>

                <strong>
                    Prediction:
                </strong>

                ${data.prediction}

                <br>

                <strong>
                    Model:
                </strong>

                ${data.model}

            `;

        }


        // ----------------------------------------------------
        // CURRENT RISK
        // ----------------------------------------------------

        const currentRisk =
            document.getElementById(
                "current-risk"
            );


        if (currentRisk) {

            currentRisk.textContent =
                data.risk_level;

        }


        // ----------------------------------------------------
        // HIGHEST RISK
        // ----------------------------------------------------

        const highestRisk =
            document.getElementById(
                "highest-risk"
            );


        if (highestRisk) {

            highestRisk.textContent =
                data.risk_level;

        }


        // ----------------------------------------------------
        // ALERT
        // ----------------------------------------------------

        updateLiveAlert(
            data
        );


        // ----------------------------------------------------
        // TIME
        // ----------------------------------------------------

        updateLastUpdated();

    }

    catch (error) {

        console.error(
            "Live prediction error:",
            error
        );


        const riskElement =
            document.getElementById(
                "risk"
            );


        if (riskElement) {

            riskElement.innerHTML = `

                <div class="risk-high">

                    ❌ Live prediction unavailable

                </div>

                <br>

                <small>
                    ${error.message}
                </small>

            `;

        }

    }

}


// ============================================================
// LIVE ALERT SYSTEM
// ============================================================

function updateLiveAlert(data) {

    const alertsElement =
        document.getElementById(
            "alerts"
        );


    if (!alertsElement) {

        return;

    }


    const probability =
        (
            Number(
                data.landslide_probability
            ) * 100
        ).toFixed(2);


    // --------------------------------------------------------
    // HIGH
    // --------------------------------------------------------

    if (
        data.risk_level === "HIGH"
    ) {

        alertsElement.innerHTML = `

            <div class="alert high">

                🚨

                <strong>
                    HIGH LANDSLIDE RISK
                </strong>

                <br><br>

                Live satellite-based prediction
                indicates HIGH risk at the
                selected location.

                <br><br>

                Probability:

                <strong>
                    ${probability}%
                </strong>

            </div>

        `;

    }


    // --------------------------------------------------------
    // MEDIUM
    // --------------------------------------------------------

    else if (
        data.risk_level === "MEDIUM"
    ) {

        alertsElement.innerHTML = `

            <div class="alert medium">

                ⚠

                <strong>
                    MEDIUM LANDSLIDE RISK
                </strong>

                <br><br>

                Elevated landslide risk detected
                at the selected location.

                <br><br>

                Probability:

                <strong>
                    ${probability}%
                </strong>

            </div>

        `;

    }


    // --------------------------------------------------------
    // LOW
    // --------------------------------------------------------

    else {

        alertsElement.innerHTML = `

            <div class="alert low">

                ✓

                <strong>
                    LOW LANDSLIDE RISK
                </strong>

                <br><br>

                No immediate landslide warning
                at the selected location.

                <br><br>

                Probability:

                <strong>
                    ${probability}%
                </strong>

            </div>

        `;

    }

}


// ============================================================
// LOAD LOCAL DATABASE RISK
// ============================================================

async function loadLocalRisk() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/local-risk`,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            latitude:
                                selectedLatitude,

                            longitude:
                                selectedLongitude,

                            radius_km:
                                RADIUS_KM

                        })

                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "LOCAL RISK:",
            data
        );


        updateRiskDashboard(
            data
        );


        await loadNearbyRisks();


        updateLastUpdated();

    }

    catch (error) {

        console.error(
            "Local risk error:",
            error
        );

    }

}


// ============================================================
// UPDATE RISK DASHBOARD
// ============================================================

function updateRiskDashboard(data) {

    let riskClass =
        "";


    if (
        data.highest_risk === "HIGH"
    ) {

        riskClass =
            "risk-high";

    }

    else if (
        data.highest_risk === "MEDIUM"
    ) {

        riskClass =
            "risk-medium";

    }

    else if (
        data.highest_risk === "LOW"
    ) {

        riskClass =
            "risk-low";

    }


    const riskElement =
        document.getElementById(
            "risk"
        );


    if (riskElement) {

        riskElement.innerHTML = `

            <div class="${riskClass}">

                ${data.highest_risk}

            </div>

            <br>

            <strong>
                Nearby risks:
            </strong>

            ${data.nearby_risks}

            <br>

            <strong>
                Radius:
            </strong>

            ${data.radius_km} km

        `;

    }


    // --------------------------------------------------------
    // CURRENT RISK
    // --------------------------------------------------------

    const currentRisk =
        document.getElementById(
            "current-risk"
        );


    if (currentRisk) {

        currentRisk.textContent =
            data.highest_risk;

    }


    // --------------------------------------------------------
    // HIGHEST RISK
    // --------------------------------------------------------

    const highestRisk =
        document.getElementById(
            "highest-risk"
        );


    if (highestRisk) {

        highestRisk.textContent =
            data.highest_risk;

    }


    // --------------------------------------------------------
    // NEARBY COUNT
    // --------------------------------------------------------

    const nearbyCount =
        document.getElementById(
            "nearby-count"
        );


    if (nearbyCount) {

        nearbyCount.textContent =
            data.nearby_risks;

    }


    // --------------------------------------------------------
    // DATABASE ALERT
    // --------------------------------------------------------

    updateAlert(
        data
    );

}


// ============================================================
// DATABASE ALERT SYSTEM
// ============================================================

function updateAlert(data) {

    const alertsElement =
        document.getElementById(
            "alerts"
        );


    if (!alertsElement) {

        return;

    }


    if (!data.alert) {

        alertsElement.innerHTML = `

            <div class="alert low">

                ✓ No active local alerts.

                <br>

                Current nearby risk:

                <strong>
                    ${data.highest_risk}
                </strong>

            </div>

        `;

        return;

    }


    if (
        data.highest_risk === "HIGH"
    ) {

        alertsElement.innerHTML = `

            <div class="alert high">

                🚨

                <strong>
                    HIGH LANDSLIDE RISK
                </strong>

                <br><br>

                A high-risk prediction
                has been detected within
                ${data.radius_km} km.

                <br><br>

                Take necessary precautions.

            </div>

        `;

    }

    else {

        alertsElement.innerHTML = `

            <div class="alert medium">

                ⚠

                <strong>
                    MEDIUM LANDSLIDE RISK
                </strong>

                <br><br>

                Elevated landslide risk
                detected within
                ${data.radius_km} km.

            </div>

        `;

    }

}


// ============================================================
// LOAD NEARBY RISKS
// ============================================================

async function loadNearbyRisks() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/nearby-risks`,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            latitude:
                                selectedLatitude,

                            longitude:
                                selectedLongitude,

                            radius_km:
                                RADIUS_KM

                        })

                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "NEARBY RISKS:",
            data
        );


        displayRiskMarkers(
            data
        );

    }

    catch (error) {

        console.error(
            "Nearby risks error:",
            error
        );

    }

}


// ============================================================
// DISPLAY NEARBY RISK MARKERS
// ============================================================

function displayRiskMarkers(data) {

    // --------------------------------------------------------
    // REMOVE OLD NEARBY MARKERS
    // --------------------------------------------------------

    riskMarkers.forEach(
        marker =>
            map.removeLayer(
                marker
            )
    );


    riskMarkers = [];


    if (
        !data ||
        !Array.isArray(
            data.risks
        )
    ) {

        return;

    }


    data.risks.forEach(
        risk => {

            let markerColor;


            if (
                risk.risk_level === "HIGH"
            ) {

                markerColor =
                    "red";

            }

            else if (
                risk.risk_level === "MEDIUM"
            ) {

                markerColor =
                    "orange";

            }

            else {

                markerColor =
                    "green";

            }


            const marker =
                L.circleMarker(
                    [
                        Number(
                            risk.latitude
                        ),

                        Number(
                            risk.longitude
                        )
                    ],
                    {

                        radius:
                            9,

                        color:
                            markerColor,

                        fillColor:
                            markerColor,

                        fillOpacity:
                            0.8

                    }
                );


            marker.bindPopup(`

                <strong>
                    Landslide Risk
                </strong>

                <br><br>

                Risk:

                <strong>
                    ${risk.risk_level}
                </strong>

                <br>

                Probability:

                ${(
                    Number(
                        risk.landslide_probability
                    ) * 100
                ).toFixed(2)}%

                <br>

                Distance:

                ${Number(
                    risk.distance_km
                ).toFixed(2)} km

            `);


            marker.addTo(
                map
            );


            riskMarkers.push(
                marker
            );

        }
    );

}


// ============================================================
// LOAD ALL RISK POINTS
// ============================================================

async function loadAllRiskPoints() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/risk-points`
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "ALL RISK POINTS:",
            data
        );


        displayAllRiskPoints(
            data
        );

    }

    catch (error) {

        console.error(
            "Risk points error:",
            error
        );

    }

}


// ============================================================
// DISPLAY ALL RISK POINTS
// ============================================================

function displayAllRiskPoints(data) {

    // --------------------------------------------------------
    // REMOVE PREVIOUS ALL-RISK MARKERS
    // --------------------------------------------------------

    allRiskMarkers.forEach(
        marker =>
            map.removeLayer(
                marker
            )
    );


    allRiskMarkers = [];


    if (
        !Array.isArray(data)
    ) {

        return;

    }


    data.forEach(
        risk => {

            let markerColor;


            if (
                risk.risk_level === "HIGH"
            ) {

                markerColor =
                    "red";

            }

            else if (
                risk.risk_level === "MEDIUM"
            ) {

                markerColor =
                    "orange";

            }

            else {

                markerColor =
                    "green";

            }


            const marker =
                L.circleMarker(
                    [
                        Number(
                            risk.latitude
                        ),

                        Number(
                            risk.longitude
                        )
                    ],
                    {

                        radius:
                            7,

                        color:
                            markerColor,

                        fillColor:
                            markerColor,

                        fillOpacity:
                            0.75,

                        weight:
                            2

                    }
                );


            marker.bindPopup(`

                <strong>
                    Landslide Prediction
                </strong>

                <br><br>

                Risk:

                <strong>
                    ${risk.risk_level}
                </strong>

                <br>

                Probability:

                ${(
                    Number(
                        risk.landslide_probability
                    ) * 100
                ).toFixed(2)}%

                <br>

                Model:

                ${risk.model}

                <br>

                Time:

                ${new Date(
                    risk.created_at
                ).toLocaleString(
                    "en-IN"
                )}

            `);


            marker.addTo(
                map
            );


            allRiskMarkers.push(
                marker
            );

        }
    );

}


// ============================================================
// UPDATE LAST UPDATED TIME
// ============================================================

function updateLastUpdated() {

    const timeElement =
        document.getElementById(
            "last-updated"
        );


    if (!timeElement) {

        return;

    }


    const now =
        new Date();


    timeElement.textContent =
        now.toLocaleTimeString(
            "en-IN",
            {

                hour:
                    "2-digit",

                minute:
                    "2-digit",

                second:
                    "2-digit"

            }
        );

}


// ============================================================
// RISK HISTORY
// ============================================================

async function loadRiskHistory() {

    try {

        const url =
            `${API_BASE_URL}/risk-history` +
            `?latitude=${encodeURIComponent(
                selectedLatitude
            )}` +
            `&longitude=${encodeURIComponent(
                selectedLongitude
            )}` +
            `&limit=${HISTORY_LIMIT}`;


        console.log(
            "Loading risk history:",
            url
        );


        const response =
            await fetch(url);


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "RISK HISTORY:",
            data
        );


        displayRiskHistory(
            data
        );

    }

    catch (error) {

        console.error(
            "Risk history error:",
            error
        );


        showHistoryMessage(
            "Unable to load risk history."
        );

    }

}


// ============================================================
// DISPLAY RISK HISTORY
// ============================================================

function displayRiskHistory(data) {

    const canvas =
        document.getElementById(
            "riskHistoryChart"
        );


    const historyElement =
        document.getElementById(
            "history"
        );


    if (!canvas) {

        console.warn(
            "riskHistoryChart canvas not found."
        );

        return;

    }


    if (
        !data ||
        !Array.isArray(
            data.predictions
        )
    ) {

        showHistoryMessage(
            "No historical data available."
        );

        return;

    }


    // --------------------------------------------------------
    // NO HISTORY
    // --------------------------------------------------------

    if (
        data.predictions.length === 0
    ) {

        if (riskHistoryChart) {

            riskHistoryChart.destroy();

            riskHistoryChart =
                null;

        }


        if (historyElement) {

            historyElement.innerHTML = `

                <div class="history-chart-container">

                    <canvas id="riskHistoryChart"></canvas>

                </div>

                <p>
                    No historical predictions
                    available for this location.
                </p>

            `;

        }

        return;

    }


    // --------------------------------------------------------
    // SORT OLDEST → NEWEST
    // --------------------------------------------------------

    const predictions =
        [...data.predictions].sort(
            function (a, b) {

                return (
                    new Date(
                        a.created_at
                    ) -
                    new Date(
                        b.created_at
                    )
                );

            }
        );


    // --------------------------------------------------------
    // TIME LABELS
    // --------------------------------------------------------

    const labels =
        predictions.map(
            function (item) {

                return new Date(
                    item.created_at
                ).toLocaleTimeString(
                    "en-IN",
                    {

                        hour:
                            "2-digit",

                        minute:
                            "2-digit",

                        second:
                            "2-digit"

                    }
                );

            }
        );


    // --------------------------------------------------------
    // PROBABILITY DATA
    // --------------------------------------------------------

    const probabilities =
        predictions.map(
            function (item) {

                return (
                    Number(
                        item.landslide_probability
                    ) * 100
                );

            }
        );


    // --------------------------------------------------------
    // DESTROY OLD CHART
    // --------------------------------------------------------

    if (riskHistoryChart) {

        riskHistoryChart.destroy();

        riskHistoryChart =
            null;

    }


    // --------------------------------------------------------
    // CREATE NEW CHART
    // --------------------------------------------------------

    riskHistoryChart =
        new Chart(
            canvas,
            {

                type:
                    "line",


                data: {

                    labels:
                        labels,

                    datasets: [

                        {

                            label:
                                "Landslide Probability (%)",

                            data:
                                probabilities,

                            tension:
                                0.3,

                            fill:
                                true,

                            borderWidth:
                                2,

                            pointRadius:
                                4,

                            pointHoverRadius:
                                6

                        }

                    ]

                },


                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,


                    interaction: {

                        intersect:
                            false,

                        mode:
                            "index"

                    },


                    scales: {

                        y: {

                            min:
                                0,

                            max:
                                100,

                            title: {

                                display:
                                    true,

                                text:
                                    "Probability (%)"

                            }

                        },


                        x: {

                            title: {

                                display:
                                    true,

                                text:
                                    "Time"

                            }

                        }

                    },


                    plugins: {

                        legend: {

                            display:
                                true

                        },


                        tooltip: {

                            callbacks: {

                                label:
                                    function (
                                        context
                                    ) {

                                        return (
                                            "Probability: " +
                                            Number(
                                                context.raw
                                            ).toFixed(2) +
                                            "%"
                                        );

                                    }

                            }

                        }

                    }

                }

            }
        );

}


// ============================================================
// HISTORY MESSAGE
// ============================================================

function showHistoryMessage(message) {

    const historyElement =
        document.getElementById(
            "history"
        );


    if (!historyElement) {

        return;

    }


    historyElement.innerHTML = `

        <div class="history-chart-container">

            <canvas id="riskHistoryChart"></canvas>

        </div>

        <p>
            ${message}
        </p>

    `;

}


// ============================================================
// MANUAL AI PREDICTION
// ============================================================

async function runPrediction() {

    const resultElement =
        document.getElementById(
            "prediction-result"
        );


    if (!resultElement) {

        return;

    }


    resultElement.innerHTML =
        "⏳ Running AI prediction...";


    // --------------------------------------------------------
    // READ INPUTS
    // --------------------------------------------------------

    const requestData = {

        latitude:
            selectedLatitude,

        longitude:
            selectedLongitude,


        B2:
            Number(
                document.getElementById(
                    "pred-b2"
                ).value
            ),

        B3:
            Number(
                document.getElementById(
                    "pred-b3"
                ).value
            ),

        B4:
            Number(
                document.getElementById(
                    "pred-b4"
                ).value
            ),

        B5:
            Number(
                document.getElementById(
                    "pred-b5"
                ).value
            ),

        B6:
            Number(
                document.getElementById(
                    "pred-b6"
                ).value
            ),

        B7:
            Number(
                document.getElementById(
                    "pred-b7"
                ).value
            ),

        B8:
            Number(
                document.getElementById(
                    "pred-b8"
                ).value
            ),

        B8A:
            Number(
                document.getElementById(
                    "pred-b8a"
                ).value
            ),

        B11:
            Number(
                document.getElementById(
                    "pred-b11"
                ).value
            ),

        B12:
            Number(
                document.getElementById(
                    "pred-b12"
                ).value
            ),


        NDVI:
            Number(
                document.getElementById(
                    "pred-ndvi"
                ).value
            ),

        NDMI:
            Number(
                document.getElementById(
                    "pred-ndmi"
                ).value
            ),

        NDWI:
            Number(
                document.getElementById(
                    "pred-ndwi"
                ).value
            ),

        NBR:
            Number(
                document.getElementById(
                    "pred-nbr"
                ).value
            ),


        hls_image_count:
            Number(
                document.getElementById(
                    "pred-image-count"
                ).value
            ),

        hls_valid_image_count:
            Number(
                document.getElementById(
                    "pred-valid-count"
                ).value
            )

    };


    // --------------------------------------------------------
    // VALIDATE INPUTS
    // --------------------------------------------------------

    const featureValues = [

        requestData.B2,
        requestData.B3,
        requestData.B4,
        requestData.B5,
        requestData.B6,
        requestData.B7,
        requestData.B8,
        requestData.B8A,
        requestData.B11,
        requestData.B12,

        requestData.NDVI,
        requestData.NDMI,
        requestData.NDWI,
        requestData.NBR,

        requestData.hls_image_count,
        requestData.hls_valid_image_count

    ];


    if (
        featureValues.some(
            value => !Number.isFinite(value)
        )
    ) {

        resultElement.innerHTML = `

            <div class="risk-high">

                ❌ Please enter valid values
                for all prediction features.

            </div>

        `;

        return;

    }


    try {

        // ----------------------------------------------------
        // REQUEST MANUAL PREDICTION
        // ----------------------------------------------------

        const response =
            await fetch(
                `${API_BASE_URL}/predict`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            requestData
                        )

                }
            );


        if (!response.ok) {

            const errorText =
                await response.text();


            throw new Error(
                `HTTP ${response.status}: ${errorText}`
            );

        }


        const result =
            await response.json();


        console.log(
            "MANUAL PREDICTION:",
            result
        );


        // ----------------------------------------------------
        // RISK CLASS
        // ----------------------------------------------------

        let resultClass =
            "risk-low";


        if (
            result.risk_level === "HIGH"
        ) {

            resultClass =
                "risk-high";

        }

        else if (
            result.risk_level === "MEDIUM"
        ) {

            resultClass =
                "risk-medium";

        }


        // ----------------------------------------------------
        // DISPLAY RESULT
        // ----------------------------------------------------

        resultElement.innerHTML = `

            <div class="${resultClass}">

                <strong>
                    ${result.risk_level} RISK
                </strong>

            </div>

            <br>

            <strong>
                Landslide Probability:
            </strong>

            ${(
                Number(
                    result.landslide_probability
                ) * 100
            ).toFixed(2)}%

            <br>

            <strong>
                Prediction:
            </strong>

            ${result.prediction}

            <br>

            <strong>
                Model:
            </strong>

            ${result.model}

            <br>

            <strong>
                Location:
            </strong>

            ${Number(
                result.latitude
            ).toFixed(5)},

            ${Number(
                result.longitude
            ).toFixed(5)}

        `;


        // ----------------------------------------------------
        // REFRESH DASHBOARD
        // ----------------------------------------------------

        await loadLocalRisk();

        await loadNearbyRisks();

        await loadAllRiskPoints();

        await loadRiskHistory();

        updateLastUpdated();

    }

    catch (error) {

        console.error(
            "Prediction error:",
            error
        );


        resultElement.innerHTML = `

            <div class="risk-high">

                ❌ Prediction failed

            </div>

            <br>

            ${error.message}

        `;

    }

}


// ============================================================
// MANUAL PREDICTION BUTTON
// ============================================================

const predictButton =
    document.getElementById(
        "predict-button"
    );


if (predictButton) {

    predictButton.addEventListener(
        "click",
        runPrediction
    );

}


// ============================================================
// INITIALIZATION
// ============================================================

async function initializeDashboard() {

    updateSelectedLocation();

    updateMapSelection();


    // --------------------------------------------------------
    // LOAD DATABASE LOCAL RISK
    // --------------------------------------------------------

    await loadLocalRisk();


    // --------------------------------------------------------
    // LOAD ALL STORED RISK POINTS
    // --------------------------------------------------------

    await loadAllRiskPoints();


    // --------------------------------------------------------
    // LOAD HISTORY
    // --------------------------------------------------------

    await loadRiskHistory();

}


// ============================================================
// START DASHBOARD
// ============================================================

initializeDashboard();


// ============================================================
// LIVE REFRESH
// ============================================================

setInterval(
    async function () {

        // ----------------------------------------------------
        // Refresh local database risk
        // ----------------------------------------------------

        await loadLocalRisk();


        // ----------------------------------------------------
        // Refresh history
        // ----------------------------------------------------

        await loadRiskHistory();


        // ----------------------------------------------------
        // Refresh all risk points
        // ----------------------------------------------------

        await loadAllRiskPoints();

    },
    REFRESH_INTERVAL
);