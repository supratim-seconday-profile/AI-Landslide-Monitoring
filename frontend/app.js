/* ============================================================
   NER LANDSLIDE EARLY WARNING SYSTEM
   ============================================================

   app.js
   ROAD INTELLIGENCE + GIS DASHBOARD EDITION

   EXISTING FEATURES PRESERVED
   ----------------------------
   1. Leaflet map
   2. Selected location
   3. 5 km analysis radius
   4. Nearby landslide risks
   5. Stored risk predictions
   6. Potential landslide zones
   7. Risk ranking
   8. Live Google Earth Engine prediction
   9. SVM RBF prediction
   10. PostgreSQL risk history
   11. Weather and rainfall
   12. Local alerts

   ROAD FEATURES
   -------------
   13. Vulnerable roads
   14. Road summary
   15. Road filters
   16. Road search
   17. Road sorting
   18. Road vulnerability score
   19. Road landslide probability
   20. Road distance
   21. Road type
   22. Road geometry handling
   23. Road map layer
   24. Road highlighting
   25. Road popups
   26. Road map controls

   IMPORTANT
   ----------
   Risk markers and road layers are completely separate.
   Clearing roads NEVER clears landslide-risk markers.
   ============================================================ */


/* ============================================================
   CONFIGURATION
   ============================================================ */

const API_BASE_URL = "http://127.0.0.1:8000";

const DEFAULT_LATITUDE = 27.338;
const DEFAULT_LONGITUDE = 88.606;

const RADIUS_KM = 5;

const REFRESH_INTERVAL = 30000;

const HISTORY_LIMIT = 20;

const LIVE_PREDICTION_TIMEOUT = 90000;

const MAX_RISK_ZONES = 12;

const MAX_RANKING_ITEMS = 10;

const MAX_VULNERABLE_ROADS = 50;


/* ============================================================
   GLOBAL STATE
   ============================================================ */

let map = null;

let selectedLatitude = DEFAULT_LATITUDE;
let selectedLongitude = DEFAULT_LONGITUDE;

let selectedMarker = null;
let radiusCircle = null;


/* ------------------------------------------------------------
   LANDSLIDE RISK LAYERS
   ------------------------------------------------------------ */

let riskMarkers = [];
let allRiskMarkers = [];
let riskHeatLayer = null;


/* ------------------------------------------------------------
   ROAD LAYERS
   ------------------------------------------------------------ */

let vulnerableRoadLayer = null;
let selectedRoadLayer = null;
let roadLabelsLayer = null;


/* ------------------------------------------------------------
   CHART
   ------------------------------------------------------------ */

let riskHistoryChart = null;


/* ------------------------------------------------------------
   REQUEST CONTROLLERS
   ------------------------------------------------------------ */

let livePredictionController = null;
let weatherRequestController = null;


/* ------------------------------------------------------------
   APPLICATION STATE
   ------------------------------------------------------------ */

let hasLivePrediction = false;

let lastLivePrediction = null;

let lastWeatherData = null;

let latestRiskPoints = [];

let latestVulnerableRoads = [];

let dashboardInitialized = false;

let activeRoadFilter = "ALL";

let activeRoadSort = "RISK";

let roadSearchText = "";


/* ============================================================
   GENERAL HELPERS
   ============================================================ */

function escapeHtml(value) {

    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function safeNumber(value, fallback = 0) {

    const number = Number(value);

    return Number.isFinite(number)
        ? number
        : fallback;
}


function probabilityNumber(value) {

    let number = Number(value);

    if (!Number.isFinite(number)) {
        return 0;
    }

    if (number > 1) {
        number = number / 100;
    }

    return Math.max(
        0,
        Math.min(1, number)
    );
}


function formatProbability(value) {

    return (
        probabilityNumber(value) * 100
    ).toFixed(2);
}


function formatDistance(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "--";
    }

    return number.toFixed(2);
}


function formatScore(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "--";
    }

    return number.toFixed(0);
}


function formatTime(timestamp) {

    if (!timestamp) {
        return "--";
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "--";
    }

    return date.toLocaleTimeString(
        "en-IN",
        {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );
}


function formatDateTime(timestamp) {

    if (!timestamp) {
        return "--";
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "--";
    }

    return date.toLocaleString(
        "en-IN",
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );
}


function setText(id, value) {

    const element =
        document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


/* ============================================================
   RISK HELPERS
   ============================================================ */

function getRiskClass(level) {

    const risk =
        String(level || "")
            .toUpperCase();

    if (
        risk === "CRITICAL" ||
        risk === "HIGH"
    ) {
        return "risk-high";
    }

    if (
        risk === "MEDIUM" ||
        risk === "MODERATE"
    ) {
        return "risk-medium";
    }

    if (risk === "LOW") {
        return "risk-low";
    }

    return "risk-none";
}


function getRiskColor(level) {

    const risk =
        String(level || "")
            .toUpperCase();

    if (risk === "CRITICAL") {
        return "#991b1b";
    }

    if (risk === "HIGH") {
        return "#dc2626";
    }

    if (
        risk === "MEDIUM" ||
        risk === "MODERATE"
    ) {
        return "#f59e0b";
    }

    if (risk === "LOW") {
        return "#16a34a";
    }

    return "#64748b";
}


function getRiskLevel(item) {

    const raw =
        String(
            item?.risk_level ??
            item?.risk ??
            item?.level ??
            "LOW"
        ).toUpperCase();

    if (raw === "CRITICAL") {
        return "CRITICAL";
    }

    if (raw === "HIGH") {
        return "HIGH";
    }

    if (
        raw === "MEDIUM" ||
        raw === "MODERATE"
    ) {
        return "MEDIUM";
    }

    if (raw === "LOW") {
        return "LOW";
    }

    return "LOW";
}


function getProbability(item) {

    return probabilityNumber(
        item?.landslide_probability ??
        item?.risk_probability ??
        item?.probability ??
        0
    );
}


/* ============================================================
   DATA EXTRACTION
   ============================================================ */

function getLatitude(item) {

    const value =
        Number(
            item?.latitude ??
            item?.lat
        );

    return Number.isFinite(value)
        ? value
        : null;
}


function getLongitude(item) {

    const value =
        Number(
            item?.longitude ??
            item?.lon ??
            item?.lng
        );

    return Number.isFinite(value)
        ? value
        : null;
}


function getLocationName(item) {

    return (
        item?.location_name ??
        item?.location ??
        item?.place ??
        item?.district ??
        item?.state ??
        "Risk Location"
    );
}


function extractRiskArray(data) {

    if (Array.isArray(data)) {
        return data;
    }

    const possibleKeys = [
        "risks",
        "points",
        "predictions",
        "results",
        "data"
    ];

    for (
        const key of possibleKeys
    ) {

        if (
            Array.isArray(data?.[key])
        ) {
            return data[key];
        }
    }

    return [];
}


function extractRoadArray(data) {

    if (Array.isArray(data)) {
        return data;
    }

    const possibleKeys = [
        "roads",
        "vulnerable_roads",
        "road_segments",
        "results",
        "data",
        "features"
    ];

    for (
        const key of possibleKeys
    ) {

        if (
            Array.isArray(data?.[key])
        ) {
            return data[key];
        }
    }

    return [];
}


/* ============================================================
   ROAD HELPERS
   ============================================================ */

function getRoadName(road, index = 0) {

    return (
        road?.road_name ??
        road?.name ??
        road?.ref ??
        road?.road ??
        road?.road_id ??
        `Road Segment ${index + 1}`
    );
}


function getRoadType(road) {

    return (
        road?.road_type ??
        road?.highway ??
        road?.type ??
        "Road"
    );
}


function getRoadScore(road) {

    const candidates = [
        road?.vulnerability_score,
        road?.road_vulnerability_score,
        road?.score,
        road?.risk_score
    ];

    for (
        const value of candidates
    ) {

        const number = Number(value);

        if (
            Number.isFinite(number)
        ) {
            return Math.max(
                0,
                Math.min(100, number)
            );
        }
    }

    /*
       If backend has not supplied a road
       vulnerability score, derive a
       conservative display score from
       landslide probability.

       This is NOT a replacement for a
       trained road model.
    */

    return getProbability(road) * 100;
}


function getRoadRiskLevel(road) {

    const explicit =
        String(
            road?.risk_level ??
            road?.vulnerability ??
            road?.risk ??
            road?.level ??
            ""
        ).toUpperCase();

    if (explicit === "CRITICAL") {
        return "CRITICAL";
    }

    if (explicit === "HIGH") {
        return "HIGH";
    }

    if (
        explicit === "MEDIUM" ||
        explicit === "MODERATE"
    ) {
        return "MEDIUM";
    }

    if (explicit === "LOW") {
        return "LOW";
    }

    const score =
        getRoadScore(road);

    if (score >= 75) {
        return "CRITICAL";
    }

    if (score >= 50) {
        return "HIGH";
    }

    if (score >= 25) {
        return "MEDIUM";
    }

    return "LOW";
}


/* ============================================================
   ROAD GEOMETRY EXTRACTION
   ============================================================ */

function extractRoadCoordinates(road) {

    if (!road) {
        return null;
    }


    /*
       GeoJSON Feature
    */

    if (
        road.geometry?.type === "Feature"
    ) {

        return extractRoadCoordinates(
            road.geometry
        );
    }


    /*
       GeoJSON geometry object
    */

    if (
        road.geometry &&
        Array.isArray(
            road.geometry.coordinates
        )
    ) {

        return normalizeRoadCoordinates(
            road.geometry.coordinates
        );
    }


    /*
       Geometry as JSON string
    */

    if (
        typeof road.geometry === "string"
    ) {

        try {

            const geometry =
                JSON.parse(
                    road.geometry
                );

            if (
                Array.isArray(
                    geometry.coordinates
                )
            ) {

                return normalizeRoadCoordinates(
                    geometry.coordinates
                );
            }

        }
        catch (_) {
            // Ignore invalid geometry.
        }
    }


    /*
       Direct coordinates
    */

    if (
        Array.isArray(
            road.coordinates
        )
    ) {

        return normalizeRoadCoordinates(
            road.coordinates
        );
    }


    /*
       GeoJSON field
    */

    if (road.geojson) {

        try {

            const geometry =
                typeof road.geojson === "string"
                    ? JSON.parse(road.geojson)
                    : road.geojson;

            if (
                geometry?.geometry?.coordinates
            ) {

                return normalizeRoadCoordinates(
                    geometry.geometry.coordinates
                );
            }

            if (
                geometry?.coordinates
            ) {

                return normalizeRoadCoordinates(
                    geometry.coordinates
                );
            }

        }
        catch (_) {
            // Ignore malformed GeoJSON.
        }
    }


    /*
       Start/end points
    */

    if (
        road.start &&
        road.end
    ) {

        const start =
            extractRoadPoint(
                road.start
            );

        const end =
            extractRoadPoint(
                road.end
            );

        if (
            start &&
            end
        ) {

            return [
                start,
                end
            ];
        }
    }


    /*
       Explicit start/end coordinates
    */

    if (
        road.start_latitude !== undefined &&
        road.start_longitude !== undefined &&
        road.end_latitude !== undefined &&
        road.end_longitude !== undefined
    ) {

        return [
            [
                Number(road.start_latitude),
                Number(road.start_longitude)
            ],
            [
                Number(road.end_latitude),
                Number(road.end_longitude)
            ]
        ];
    }


    return null;
}


function normalizeRoadCoordinates(
    coordinates
) {

    if (
        !Array.isArray(coordinates)
    ) {
        return null;
    }


    /*
       MultiLineString

       [
         [
           [lng, lat],
           [lng, lat]
         ],
         [
           [lng, lat],
           [lng, lat]
         ]
       ]
    */

    if (
        coordinates.length &&
        Array.isArray(
            coordinates[0]
        ) &&
        Array.isArray(
            coordinates[0][0]
        )
    ) {

        const flattened = [];

        coordinates.forEach(
            part => {

                const normalized =
                    normalizeRoadCoordinates(
                        part
                    );

                if (
                    normalized
                ) {

                    normalized.forEach(
                        point =>
                            flattened.push(
                                point
                            )
                    );
                }
            }
        );

        return flattened.length >= 2
            ? flattened
            : null;
    }


    /*
       GeoJSON LineString:

       [longitude, latitude]
    */

    const result = [];

    coordinates.forEach(
        point => {

            if (
                !Array.isArray(point) ||
                point.length < 2
            ) {
                return;
            }

            const longitude =
                Number(point[0]);

            const latitude =
                Number(point[1]);

            if (
                Number.isFinite(latitude) &&
                Number.isFinite(longitude)
            ) {

                result.push(
                    [
                        latitude,
                        longitude
                    ]
                );
            }
        }
    );


    return result.length >= 2
        ? result
        : null;
}


function extractRoadPoint(point) {

    if (!point) {
        return null;
    }


    if (
        Array.isArray(point) &&
        point.length >= 2
    ) {

        return [
            Number(point[0]),
            Number(point[1])
        ];
    }


    const latitude =
        point.latitude ??
        point.lat;

    const longitude =
        point.longitude ??
        point.longitude ??
        point.lon ??
        point.lng;


    if (
        latitude !== undefined &&
        longitude !== undefined
    ) {

        return [
            Number(latitude),
            Number(longitude)
        ];
    }


    return null;
}


function roadHasGeometry(road) {

    const coordinates =
        extractRoadCoordinates(
            road
        );

    return Boolean(
        coordinates &&
        coordinates.length >= 2
    );
}


/* ============================================================
   MAP INITIALISATION
   ============================================================ */

function initializeMap() {

    if (map) {
        return true;
    }


    if (
        typeof L === "undefined"
    ) {

        console.error(
            "Leaflet is not loaded."
        );

        return false;
    }


    const mapElement =
        document.getElementById(
            "map"
        );

    if (!mapElement) {
        return false;
    }


    map = L.map(
        "map",
        {
            zoomControl: true,
            preferCanvas: true
        }
    ).setView(
        [
            DEFAULT_LATITUDE,
            DEFAULT_LONGITUDE
        ],
        9
    );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(
        map
    );


    /*
       Separate road layers.
    */

    vulnerableRoadLayer =
        L.layerGroup()
            .addTo(map);


    selectedRoadLayer =
        L.layerGroup()
            .addTo(map);


    roadLabelsLayer =
        L.layerGroup()
            .addTo(map);


    addMapLegend();

    addMapTools();


    return true;
}


/* ============================================================
   SELECTED LOCATION
   ============================================================ */

function updateSelectedLocation() {

    const element =
        document.getElementById(
            "location"
        );

    if (!element) {
        return;
    }


    element.innerHTML = `

        <div class="selected-location-grid">

            <div>
                <span>Latitude</span>
                <strong>
                    ${selectedLatitude.toFixed(5)}
                </strong>
            </div>

            <div>
                <span>Longitude</span>
                <strong>
                    ${selectedLongitude.toFixed(5)}
                </strong>
            </div>

            <div>
                <span>Analysis Radius</span>
                <strong>
                    ${RADIUS_KM} km
                </strong>
            </div>

        </div>

    `;
}


function updateMapSelection() {

    if (!map) {
        return;
    }


    if (selectedMarker) {

        map.removeLayer(
            selectedMarker
        );

        selectedMarker = null;
    }


    if (radiusCircle) {

        map.removeLayer(
            radiusCircle
        );

        radiusCircle = null;
    }


    selectedMarker =
        L.marker(
            [
                selectedLatitude,
                selectedLongitude
            ]
        ).addTo(map);


    selectedMarker.bindPopup(`

        <div class="selected-popup">

            <strong>
                📍 Selected Analysis Location
            </strong>

            <hr>

            <div>
                <b>Latitude:</b>
                ${selectedLatitude.toFixed(5)}
            </div>

            <div>
                <b>Longitude:</b>
                ${selectedLongitude.toFixed(5)}
            </div>

            <div>
                <b>Analysis radius:</b>
                ${RADIUS_KM} km
            </div>

        </div>

    `);


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
                    0.07,

                weight:
                    2
            }
        ).addTo(map);
}


/* ============================================================
   MAP CLICK
   ============================================================ */

function registerMapClick() {

    if (!map) {
        return;
    }


    map.on(
        "click",
        async event => {

            selectedLatitude =
                event.latlng.lat;

            selectedLongitude =
                event.latlng.lng;


            hasLivePrediction =
                false;

            lastLivePrediction =
                null;


            updateSelectedLocation();

            updateMapSelection();

            clearVulnerableRoads();

            resetRiskPanel();

            resetPredictionPanel();


            updateMapStatus(
                "Location selected — loading surrounding conditions.",
                "loading"
            );


            await Promise.allSettled(
                [
                    loadWeather(
                        selectedLatitude,
                        selectedLongitude
                    ),

                    loadLocalRisk(),

                    loadRiskHistory()
                ]
            );

        }
    );
}


/* ============================================================
   MAP STATUS
   ============================================================ */

function updateMapStatus(
    message,
    type = "normal"
) {

    const element =
        document.getElementById(
            "map-status"
        );

    if (!element) {
        return;
    }


    element.textContent =
        message;


    element.className =
        `map-status ${type}`;
}


/* ============================================================
   MAP LEGEND
   ============================================================ */

function addMapLegend() {

    if (!map) {
        return;
    }


    const legend =
        L.control(
            {
                position:
                    "bottomleft"
            }
        );


    legend.onAdd =
        function() {

            const div =
                L.DomUtil.create(
                    "div",
                    "map-legend"
                );


            div.innerHTML = `

                <div class="legend-title">
                    Map Layers
                </div>

                <div class="legend-row">
                    <span class="legend-circle low"></span>
                    Low risk
                </div>

                <div class="legend-row">
                    <span class="legend-circle medium"></span>
                    Medium risk
                </div>

                <div class="legend-row">
                    <span class="legend-circle high"></span>
                    High risk
                </div>

                <div class="legend-row">
                    <span class="legend-circle critical"></span>
                    Critical risk
                </div>

                <div class="legend-divider"></div>

                <div class="legend-row">
                    <span class="legend-road low"></span>
                    Low road vulnerability
                </div>

                <div class="legend-row">
                    <span class="legend-road medium"></span>
                    Medium road vulnerability
                </div>

                <div class="legend-row">
                    <span class="legend-road high"></span>
                    High road vulnerability
                </div>

                <div class="legend-row">
                    <span class="legend-road critical"></span>
                    Critical road vulnerability
                </div>

            `;


            L.DomEvent.disableClickPropagation(
                div
            );


            return div;
        };


    legend.addTo(
        map
    );
}


/* ============================================================
   MAP TOOLS
   ============================================================ */

function addMapTools() {

    if (!map) {
        return;
    }


    const control =
        L.control(
            {
                position:
                    "topright"
            }
        );


    control.onAdd =
        function() {

            const div =
                L.DomUtil.create(
                    "div",
                    "map-tools"
                );


            div.innerHTML = `

                <button
                    id="fit-analysis-area"
                    type="button"
                    title="Fit 5 km analysis area"
                >
                    ⛶
                </button>

                <button
                    id="center-location"
                    type="button"
                    title="Center selected location"
                >
                    ◎
                </button>

                <button
                    id="show-roads"
                    type="button"
                    title="Show vulnerable roads"
                >
                    🛣
                </button>

            `;


            L.DomEvent.disableClickPropagation(
                div
            );


            return div;
        };


    control.addTo(
        map
    );


    setTimeout(
        () => {

            const fitButton =
                document.getElementById(
                    "fit-analysis-area"
                );


            if (fitButton) {

                fitButton.onclick =
                    function() {

                        if (
                            radiusCircle
                        ) {

                            map.fitBounds(
                                radiusCircle.getBounds(),
                                {
                                    padding:
                                        [
                                            30,
                                            30
                                        ]
                                }
                            );
                        }
                    };
            }


            const centerButton =
                document.getElementById(
                    "center-location"
                );


            if (centerButton) {

                centerButton.onclick =
                    function() {

                        map.setView(
                            [
                                selectedLatitude,
                                selectedLongitude
                            ],
                            Math.max(
                                map.getZoom(),
                                11
                            )
                        );
                    };
            }


            const roadButton =
                document.getElementById(
                    "show-roads"
                );


            if (roadButton) {

                roadButton.onclick =
                    function() {

                        if (
                            latestVulnerableRoads.length
                        ) {

                            renderVulnerableRoads(
                                latestVulnerableRoads
                            );

                            focusRoadLayer();

                        }
                        else {

                            updateMapStatus(
                                "Run live analysis first to identify vulnerable roads.",
                                "loading"
                            );
                        }
                    };
            }

        },
        100
    );
}


/* ============================================================
   WEATHER
   ============================================================ */

async function loadWeather(
    latitude,
    longitude
) {

    const status =
        document.getElementById(
            "weather-status"
        );

    const content =
        document.getElementById(
            "weather-content"
        );


    if (
        !status ||
        !content
    ) {
        return null;
    }


    if (
        weatherRequestController
    ) {

        try {
            weatherRequestController.abort();
        }
        catch (_) {}
    }


    weatherRequestController =
        new AbortController();


    status.textContent =
        "Fetching live weather data…";


    content.classList.add(
        "hidden"
    );


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/weather`,
                {
                    method:
                        "POST",

                    headers:
                        {
                            "Content-Type":
                                "application/json"
                        },

                    body:
                        JSON.stringify(
                            {
                                latitude,
                                longitude
                            }
                        ),

                    signal:
                        weatherRequestController.signal
                }
            );


        if (!response.ok) {

            throw new Error(
                `Weather service failed (HTTP ${response.status}).`
            );
        }


        const data =
            await response.json();


        lastWeatherData =
            data;


        const current =
            data.current ?? {};


        const rainfall =
            data.rainfall ?? {};


        const alert =
            data.rainfall_alert ?? {};


        setText(
            "weather-temperature",
            Number.isFinite(
                Number(
                    current.temperature_c
                )
            )
                ? `${Number(current.temperature_c).toFixed(1)} °C`
                : "--"
        );


        setText(
            "weather-humidity",
            Number.isFinite(
                Number(
                    current.relative_humidity_percent
                )
            )
                ? `${Number(current.relative_humidity_percent).toFixed(0)} %`
                : "--"
        );


        setText(
            "weather-current-rain",
            Number.isFinite(
                Number(
                    current.rain_mm
                )
            )
                ? `${Number(current.rain_mm).toFixed(2)} mm`
                : "--"
        );


        setText(
            "weather-wind",
            Number.isFinite(
                Number(
                    current.wind_speed_kmh
                )
            )
                ? `${Number(current.wind_speed_kmh).toFixed(1)} km/h`
                : "--"
        );


        setText(
            "weather-rainfall-24",
            Number.isFinite(
                Number(
                    rainfall.last_24h_mm
                )
            )
                ? `${Number(rainfall.last_24h_mm).toFixed(2)} mm`
                : "--"
        );


        setText(
            "weather-rainfall-72",
            Number.isFinite(
                Number(
                    rainfall.last_72h_mm
                )
            )
                ? `${Number(rainfall.last_72h_mm).toFixed(2)} mm`
                : "--"
        );


        const alertElement =
            document.getElementById(
                "rainfall-alert"
            );


        if (alertElement) {

            const level =
                String(
                    alert.level ??
                    "LOW"
                ).toUpperCase();


            let className =
                "low";


            if (
                level === "HIGH"
            ) {

                className =
                    "high";

            }
            else if (
                level === "MEDIUM"
            ) {

                className =
                    "medium";
            }


            alertElement.className =
                `weather-alert ${className}`;


            alertElement.innerHTML = `

                <strong>
                    🌧️ ${escapeHtml(level)}
                    RAINFALL ALERT
                </strong>

                <br>

                <span>
                    ${escapeHtml(
                        alert.message ??
                        "No significant rainfall warning."
                    )}
                </span>

            `;
        }


        status.textContent =
            `Weather loaded for ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;


        content.classList.remove(
            "hidden"
        );


        return data;

    }
    catch (error) {

        if (
            error.name === "AbortError"
        ) {
            return null;
        }


        console.error(
            "Weather error:",
            error
        );


        status.textContent =
            `Unable to load weather data: ${error.message}`;


        content.classList.add(
            "hidden"
        );


        return null;
    }
}


/* ============================================================
   LOCAL DATABASE RISK
   ============================================================ */

async function loadLocalRisk() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/local-risk`,
                {
                    method:
                        "POST",

                    headers:
                        {
                            "Content-Type":
                                "application/json"
                        },

                    body:
                        JSON.stringify(
                            {
                                latitude:
                                    selectedLatitude,

                                longitude:
                                    selectedLongitude,

                                radius_km:
                                    RADIUS_KM
                            }
                        )
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        updateRiskDashboard(
            data
        );


        await loadNearbyRisks();


        return data;

    }
    catch (error) {

        console.error(
            "Local risk:",
            error
        );

        return null;
    }
}


function updateRiskDashboard(data) {

    if (!data) {
        return;
    }


    const level =
        String(
            data.highest_risk ??
            "NONE"
        ).toUpperCase();


    if (
        !hasLivePrediction
    ) {

        setText(
            "current-risk",
            level
        );
    }


    setText(
        "highest-risk",
        level
    );


    setText(
        "nearby-count",
        data.nearby_risks ??
        data.count ??
        0
    );


    if (
        !hasLivePrediction &&
        data.alert === true
    ) {

        updateDatabaseAlert(
            data
        );
    }
}


function updateDatabaseAlert(data) {

    const element =
        document.getElementById(
            "alerts"
        );

    if (!element) {
        return;
    }


    const risk =
        String(
            data.highest_risk ??
            "LOW"
        ).toUpperCase();


    const high =
        risk === "HIGH" ||
        risk === "CRITICAL";


    const medium =
        risk === "MEDIUM" ||
        risk === "MODERATE";


    element.innerHTML = `

        <div
            class="alert
            ${high
                ? "high"
                : medium
                    ? "medium"
                    : "low"}"
        >

            <span class="alert-symbol">

                ${high
                    ? "🚨"
                    : medium
                        ? "⚠"
                        : "✓"}

            </span>

            <div>

                <strong>

                    ${
                        high
                            ? "HIGH LOCAL RISK"
                            : medium
                                ? "MEDIUM LOCAL RISK"
                                : "NO ACTIVE LOCAL ALERT"
                    }

                </strong>

                <p>

                    Current nearby risk:
                    ${escapeHtml(risk)}

                    within
                    ${RADIUS_KM} km.

                </p>

            </div>

        </div>

    `;
}


/* ============================================================
   NEARBY RISKS
   ============================================================ */

async function loadNearbyRisks() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/nearby-risks`,
                {
                    method:
                        "POST",

                    headers:
                        {
                            "Content-Type":
                                "application/json"
                        },

                    body:
                        JSON.stringify(
                            {
                                latitude:
                                    selectedLatitude,

                                longitude:
                                    selectedLongitude,

                                radius_km:
                                    RADIUS_KM
                            }
                        )
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        displayRiskMarkers(
            data
        );


        return data;

    }
    catch (error) {

        console.error(
            "Nearby risks:",
            error
        );

        return null;
    }
}


function displayRiskMarkers(data) {

    if (!map) {
        return;
    }


    riskMarkers.forEach(
        marker =>
            map.removeLayer(
                marker
            )
    );


    riskMarkers = [];


    const risks =
        extractRiskArray(
            data
        );


    risks.forEach(
        risk => {

            const latitude =
                getLatitude(risk);

            const longitude =
                getLongitude(risk);


            if (
                latitude === null ||
                longitude === null
            ) {
                return;
            }


            const level =
                getRiskLevel(risk);


            const color =
                getRiskColor(level);


            const marker =
                L.circleMarker(
                    [
                        latitude,
                        longitude
                    ],
                    {
                        radius:
                            9,

                        color,

                        fillColor:
                            color,

                        fillOpacity:
                            0.82,

                        weight:
                            2
                    }
                );


            marker.bindPopup(`

                <div class="risk-popup">

                    <strong>
                        ⚠ Nearby Landslide Risk
                    </strong>

                    <hr>

                    <div>
                        <b>Risk:</b>
                        ${escapeHtml(level)}
                    </div>

                    <div>
                        <b>Probability:</b>
                        ${formatProbability(
                            getProbability(risk)
                        )}%
                    </div>

                    <div>
                        <b>Distance:</b>
                        ${
                            Number.isFinite(
                                Number(
                                    risk.distance_km
                                )
                            )
                                ? Number(
                                    risk.distance_km
                                ).toFixed(2)
                                : "--"
                        } km
                    </div>

                </div>

            `);


            marker.addTo(
                map
            );


            riskMarkers.push(
                marker
            );
        }
    );


    renderRiskHeatVisual(
        risks
    );
}


/* ============================================================
   ALL RISK POINTS
   ============================================================ */

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


        displayAllRiskPoints(
            data
        );


        return data;

    }
    catch (error) {

        console.error(
            "Risk points:",
            error
        );

        return null;
    }
}


function displayAllRiskPoints(data) {

    if (!map) {
        return;
    }


    allRiskMarkers.forEach(
        marker =>
            map.removeLayer(
                marker
            )
    );


    allRiskMarkers = [];


    const points =
        extractRiskArray(
            data
        );


    latestRiskPoints =
        [...points];


    points.forEach(
        risk => {

            const latitude =
                getLatitude(risk);

            const longitude =
                getLongitude(risk);


            if (
                latitude === null ||
                longitude === null
            ) {
                return;
            }


            const level =
                getRiskLevel(risk);


            const color =
                getRiskColor(level);


            const marker =
                L.circleMarker(
                    [
                        latitude,
                        longitude
                    ],
                    {
                        radius:
                            7,

                        color,

                        fillColor:
                            color,

                        fillOpacity:
                            0.62,

                        weight:
                            2
                    }
                );


            marker.bindPopup(`

                <div class="risk-popup">

                    <strong>
                        📍 Stored Landslide Prediction
                    </strong>

                    <hr>

                    <div>
                        <b>Risk:</b>
                        ${escapeHtml(level)}
                    </div>

                    <div>
                        <b>Probability:</b>
                        ${formatProbability(
                            getProbability(risk)
                        )}%
                    </div>

                    <div>
                        <b>Model:</b>
                        ${escapeHtml(
                            risk.model ??
                            "SVM RBF"
                        )}
                    </div>

                    <div>
                        <b>Coordinates:</b>
                        ${latitude.toFixed(5)},
                        ${longitude.toFixed(5)}
                    </div>

                    ${
                        risk.created_at
                            ? `
                                <div>
                                    <b>Updated:</b>
                                    ${formatDateTime(
                                        risk.created_at
                                    )}
                                </div>
                              `
                            : ""
                    }

                </div>

            `);


            marker.addTo(
                map
            );


            allRiskMarkers.push(
                marker
            );
        }
    );


    renderPotentialLandslideZones(
        points
    );


    renderRiskRanking(
        points
    );


    renderRiskHeatVisual(
        points
    );
}


/* ============================================================
   RISK VISUAL
   ============================================================ */

function renderRiskHeatVisual(points) {

    if (!map) {
        return;
    }


    if (riskHeatLayer) {

        map.removeLayer(
            riskHeatLayer
        );
    }


    riskHeatLayer =
        L.layerGroup();


    points.forEach(
        point => {

            const latitude =
                getLatitude(point);

            const longitude =
                getLongitude(point);


            if (
                latitude === null ||
                longitude === null
            ) {
                return;
            }


            const probability =
                getProbability(
                    point
                );


            const level =
                getRiskLevel(
                    point
                );


            L.circle(
                [
                    latitude,
                    longitude
                ],
                {
                    radius:
                        250 +
                        probability * 900,

                    stroke:
                        false,

                    fillColor:
                        getRiskColor(
                            level
                        ),

                    fillOpacity:
                        0.04 +
                        probability * 0.10,

                    interactive:
                        false
                }
            ).addTo(
                riskHeatLayer
            );

        }
    );


    riskHeatLayer.addTo(
        map
    );
}


/* ============================================================
   POTENTIAL LANDSLIDE ZONES
   ============================================================ */

function renderPotentialLandslideZones(
    points
) {

    const container =
        document.getElementById(
            "risk-zones"
        );


    if (!container) {
        return;
    }


    const valid =
        points.filter(
            point =>
                getLatitude(point) !== null &&
                getLongitude(point) !== null
        );


    const sorted =
        [...valid].sort(
            (a, b) =>
                getProbability(b) -
                getProbability(a)
        );


    const displayed =
        sorted.slice(
            0,
            MAX_RISK_ZONES
        );


    setText(
        "risk-zone-count",
        valid.length
    );


    if (
        !displayed.length
    ) {

        container.innerHTML = `

            <div class="empty-state">
                No current risk predictions available.
            </div>

        `;

        return;
    }


    container.innerHTML =
        displayed.map(
            (risk, index) => {

                const level =
                    getRiskLevel(
                        risk
                    );


                const latitude =
                    getLatitude(
                        risk
                    );


                const longitude =
                    getLongitude(
                        risk
                    );


                return `

                    <div
                        class="risk-zone-card"
                        data-risk-index="${index}"
                    >

                        <div
                            class="risk-zone-top"
                        >

                            <div
                                class="risk-zone-number"
                            >
                                ${index + 1}
                            </div>

                            <div
                                class="
                                risk-zone-level
                                ${getRiskClass(level)}
                                "
                            >
                                ${escapeHtml(level)}
                            </div>

                        </div>


                        <div
                            class="
                            risk-zone-probability
                            ${getRiskClass(level)}
                            "
                        >

                            ${formatProbability(
                                getProbability(risk)
                            )}%

                        </div>


                        <div
                            class="
                            risk-zone-coordinates
                            "
                        >

                            <strong>
                                ${escapeHtml(
                                    getLocationName(risk)
                                )}
                            </strong>

                            <br>

                            ${latitude.toFixed(5)},
                            ${longitude.toFixed(5)}

                        </div>

                    </div>

                `;
            }
        ).join("");


    container
        .querySelectorAll(
            ".risk-zone-card"
        )
        .forEach(
            (card, index) => {

                card.onclick =
                    function() {

                        focusRiskLocation(
                            displayed[index]
                        );

                    };
            }
        );
}


/* ============================================================
   RISK RANKING
   ============================================================ */

function renderRiskRanking(
    points
) {

    const container =
        document.getElementById(
            "risk-ranking"
        );


    if (!container) {
        return;
    }


    const sorted =
        points
            .filter(
                point =>
                    getLatitude(point) !== null &&
                    getLongitude(point) !== null
            )
            .sort(
                (a, b) =>
                    getProbability(b) -
                    getProbability(a)
            )
            .slice(
                0,
                MAX_RANKING_ITEMS
            );


    if (
        !sorted.length
    ) {

        container.innerHTML = `

            <div class="empty-state">
                No current risk predictions available.
            </div>

        `;

        return;
    }


    container.innerHTML =
        sorted.map(
            (risk, index) => {

                const level =
                    getRiskLevel(
                        risk
                    );


                return `

                    <div
                        class="ranking-item"
                        data-ranking-index="${index}"
                    >

                        <div
                            class="ranking-number"
                        >
                            ${index + 1}
                        </div>


                        <div
                            class="ranking-location-block"
                        >

                            <div
                                class="
                                ranking-location
                                "
                            >

                                ${escapeHtml(
                                    getLocationName(
                                        risk
                                    )
                                )}

                            </div>


                            <div
                                class="
                                ranking-coordinates
                                "
                            >

                                ${getLatitude(
                                    risk
                                ).toFixed(5)},

                                ${getLongitude(
                                    risk
                                ).toFixed(5)}

                            </div>

                        </div>


                        <div
                            class="
                            ranking-probability
                            ${getRiskClass(level)}
                            "
                        >

                            ${formatProbability(
                                getProbability(risk)
                            )}%

                        </div>


                        <div
                            class="
                            ranking-risk
                            ${getRiskClass(level)}
                            "
                        >

                            ${escapeHtml(level)}

                        </div>

                    </div>

                `;
            }
        ).join("");


    container
        .querySelectorAll(
            ".ranking-item"
        )
        .forEach(
            (row, index) => {

                row.onclick =
                    function() {

                        focusRiskLocation(
                            sorted[index]
                        );

                    };
            }
        );
}


function focusRiskLocation(
    risk
) {

    const latitude =
        getLatitude(
            risk
        );


    const longitude =
        getLongitude(
            risk
        );


    if (
        latitude === null ||
        longitude === null ||
        !map
    ) {
        return;
    }


    selectedLatitude =
        latitude;

    selectedLongitude =
        longitude;


    hasLivePrediction =
        false;

    lastLivePrediction =
        null;


    map.setView(
        [
            latitude,
            longitude
        ],
        12,
        {
            animate:
                true
        }
    );


    updateSelectedLocation();

    updateMapSelection();

    clearVulnerableRoads();

    resetRiskPanel();

    resetPredictionPanel();


    L.popup()
        .setLatLng(
            [
                latitude,
                longitude
            ]
        )
        .setContent(`

            <strong>
                Potential Landslide Zone
            </strong>

            <br><br>

            Risk:
            <strong>
                ${escapeHtml(
                    getRiskLevel(risk)
                )}
            </strong>

            <br>

            Probability:
            ${formatProbability(
                getProbability(risk)
            )}%

            <br>

            Coordinates:
            ${latitude.toFixed(5)},
            ${longitude.toFixed(5)}

        `)
        .openOn(
            map
        );


    loadWeather(
        latitude,
        longitude
    );


    loadLocalRisk();


    loadRiskHistory();
}


/* ============================================================
   VULNERABLE ROAD PANEL
   ============================================================ */

function ensureVulnerableRoadPanel() {

    let panel =
        document.getElementById(
            "vulnerable-roads-panel"
        );


    /*
       If old HTML exists with
       #vulnerable-roads, transform it
       into the new road intelligence
       structure.
    */

    const oldList =
        document.getElementById(
            "vulnerable-roads"
        );


    if (
        !panel &&
        oldList
    ) {

        panel =
            oldList.closest(
                ".roads-panel"
            ) ||
            oldList.closest(
                ".panel"
            );
    }


    if (!panel) {

        panel =
            document.createElement(
                "section"
            );


        panel.id =
            "vulnerable-roads-panel";


        panel.className =
            "panel vulnerable-roads-panel";


        const dashboard =
            document.querySelector(
                ".dashboard"
            );


        const weather =
            document.querySelector(
                ".weather-panel"
            );


        if (weather) {

            weather.insertAdjacentElement(
                "afterend",
                panel
            );

        }
        else if (dashboard) {

            dashboard.appendChild(
                panel
            );

        }
        else {

            document.body.appendChild(
                panel
            );
        }
    }


    /*
       Always use the new road UI.
    */

    panel.innerHTML = `

        <div class="road-panel-header">

            <div>

                <div class="road-title-row">

                    <span
                        class="road-title-icon"
                    >
                        🛣️
                    </span>

                    <div>

                        <h2>
                            Vulnerable Roads
                        </h2>

                        <p>
                            Road exposure analysis within
                            the selected ${RADIUS_KM} km area
                        </p>

                    </div>

                </div>

            </div>


            <div
                id="road-count-badge"
                class="road-count-badge"
            >
                0
            </div>

        </div>


        <div
            id="road-status"
            class="road-status"
        >

            Analyze a location to identify
            potentially vulnerable road segments.

        </div>


        <div
            id="road-summary"
            class="road-summary"
        >
        </div>


        <div
            class="road-toolbar"
        >

            <div
                class="road-search-wrapper"
            >

                <span>
                    🔎
                </span>

                <input
                    id="road-search"
                    type="search"
                    placeholder="Search road name or type..."
                    autocomplete="off"
                >

            </div>


            <select
                id="road-sort"
                class="road-sort"
            >

                <option value="RISK">
                    Highest vulnerability
                </option>

                <option value="PROBABILITY">
                    Highest landslide probability
                </option>

                <option value="DISTANCE">
                    Nearest roads
                </option>

                <option value="NAME">
                    Road name
                </option>

            </select>

        </div>


        <div
            id="road-list"
            class="road-list"
        >

            <div class="road-empty">

                <div class="road-empty-icon">
                    🛣️
                </div>

                <strong>
                    No road analysis yet
                </strong>

                <span>
                    Run Live Risk Analysis to identify
                    potentially vulnerable roads.
                </span>

            </div>

        </div>

    `;


    registerRoadControls();
}


/* ============================================================
   ROAD CONTROLS
   ============================================================ */

function registerRoadControls() {

    const search =
        document.getElementById(
            "road-search"
        );


    if (search) {

        search.oninput =
            function() {

                roadSearchText =
                    search.value
                        .trim()
                        .toLowerCase();


                renderVulnerableRoadList(
                    latestVulnerableRoads
                );
            };
    }


    const sort =
        document.getElementById(
            "road-sort"
        );


    if (sort) {

        sort.value =
            activeRoadSort;


        sort.onchange =
            function() {

                activeRoadSort =
                    sort.value;


                renderVulnerableRoadList(
                    latestVulnerableRoads
                );
            };
    }
}


/* ============================================================
   LOAD VULNERABLE ROADS
   ============================================================ */

async function loadVulnerableRoads(
    predictionData = lastLivePrediction
) {

    ensureVulnerableRoadPanel();


    const status =
        document.getElementById(
            "road-status"
        );


    const list =
        document.getElementById(
            "road-list"
        );


    if (status) {

        status.innerHTML = `

            <span class="road-status-spinner">
                ⟳
            </span>

            Analysing roads around the selected location…

        `;
    }


    if (list) {

        list.innerHTML = `

            <div class="road-loading">

                <div
                    class="road-loading-spinner"
                >
                    ⟳
                </div>

                <div>

                    <strong>
                        Analysing road exposure
                    </strong>

                    <span>
                        Checking nearby road segments
                        against landslide risk.
                    </span>

                </div>

            </div>

        `;
    }


    const payload = {

        latitude:
            selectedLatitude,

        longitude:
            selectedLongitude,

        radius_km:
            RADIUS_KM,

        probability:
            getProbability(
                predictionData
            ),

        risk_level:
            String(
                predictionData?.risk_level ??
                "LOW"
            ).toUpperCase()

    };


    try {

        /*
           Preferred:
           POST JSON
        */

        let response =
            await fetch(
                `${API_BASE_URL}/vulnerable-roads`,
                {
                    method:
                        "POST",

                    headers:
                        {
                            "Content-Type":
                                "application/json"
                        },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        /*
           Compatibility fallback:
           GET query parameters
        */

        if (
            !response.ok &&
            [
                404,
                405,
                422
            ].includes(
                response.status
            )
        ) {

            const params =
                new URLSearchParams(
                    {
                        latitude:
                            String(
                                selectedLatitude
                            ),

                        longitude:
                            String(
                                selectedLongitude
                            ),

                        radius_km:
                            String(
                                RADIUS_KM
                            ),

                        probability:
                            String(
                                payload.probability
                            ),

                        risk_level:
                            payload.risk_level
                    }
                );


            response =
                await fetch(
                    `${API_BASE_URL}/vulnerable-roads?${params}`
                );
        }


        if (!response.ok) {

            let detail =
                `Road service failed (HTTP ${response.status}).`;


            try {

                const errorData =
                    await response.json();


                if (
                    errorData?.detail
                ) {

                    detail =
                        typeof errorData.detail === "string"
                            ? errorData.detail
                            : JSON.stringify(
                                errorData.detail
                            );
                }

            }
            catch (_) {}


            throw new Error(
                detail
            );
        }


        const data =
            await response.json();


        const roads =
            extractRoadArray(
                data
            );


        latestVulnerableRoads =
            [...roads];


        renderVulnerableRoadSummary(
            roads
        );


        renderVulnerableRoadList(
            roads
        );


        renderVulnerableRoads(
            roads
        );


        updateRoadCount(
            roads.length
        );


        if (status) {

            status.innerHTML =
                roads.length
                    ? `
                        <span
                            class="road-status-success"
                        >
                            ✓
                        </span>

                        <strong>
                            ${roads.length}
                        </strong>

                        road segments analysed within
                        ${RADIUS_KM} km.
                      `
                    : `
                        <span
                            class="road-status-success"
                        >
                            ✓
                        </span>

                        No potentially vulnerable
                        road segments detected within
                        ${RADIUS_KM} km.
                      `;
        }


        if (
            roads.some(
                road =>
                    roadHasGeometry(
                        road
                    )
            )
        ) {

            focusRoadLayer();
        }


        return data;

    }
    catch (error) {

        console.error(
            "Vulnerable roads:",
            error
        );


        latestVulnerableRoads =
            [];


        if (status) {

            status.innerHTML = `

                <span
                    class="road-status-error"
                >
                    ⚠
                </span>

                Road analysis unavailable:
                ${escapeHtml(
                    error.message
                )}

            `;
        }


        if (list) {

            list.innerHTML = `

                <div class="road-error">

                    <div
                        class="road-error-icon"
                    >
                        ⚠
                    </div>

                    <div>

                        <strong>
                            Unable to load road analysis
                        </strong>

                        <span>
                            ${escapeHtml(
                                error.message
                            )}
                        </span>

                    </div>

                </div>

            `;
        }


        vulnerableRoadLayer?.clearLayers();

        selectedRoadLayer?.clearLayers();

        roadLabelsLayer?.clearLayers();


        updateRoadCount(
            0
        );


        return null;
    }
}


/* ============================================================
   ROAD SUMMARY
   ============================================================ */

function renderVulnerableRoadSummary(
    roads
) {

    const container =
        document.getElementById(
            "road-summary"
        );


    if (!container) {
        return;
    }


    const counts = {

        CRITICAL:
            0,

        HIGH:
            0,

        MEDIUM:
            0,

        LOW:
            0
    };


    roads.forEach(
        road => {

            const level =
                getRoadRiskLevel(
                    road
                );


            if (
                counts[level] !== undefined
            ) {

                counts[level]++;
            }

        }
    );


    container.innerHTML = `

        <div
            class="road-summary-card total"
        >

            <div
                class="road-summary-icon"
            >
                🛣️
            </div>

            <div>

                <span>
                    Total Roads
                </span>

                <strong>
                    ${roads.length}
                </strong>

            </div>

        </div>


        <div
            class="
            road-summary-card
            critical
            "
        >

            <div
                class="road-summary-icon"
            >
                🚨
            </div>

            <div>

                <span>
                    Critical
                </span>

                <strong>
                    ${counts.CRITICAL}
                </strong>

            </div>

        </div>


        <div
            class="
            road-summary-card
            high
            "
        >

            <div
                class="road-summary-icon"
            >
                🔴
            </div>

            <div>

                <span>
                    High
                </span>

                <strong>
                    ${counts.HIGH}
                </strong>

            </div>

        </div>


        <div
            class="
            road-summary-card
            medium
            "
        >

            <div
                class="road-summary-icon"
            >
                🟠
            </div>

            <div>

                <span>
                    Medium
                </span>

                <strong>
                    ${counts.MEDIUM}
                </strong>

            </div>

        </div>


        <div
            class="
            road-summary-card
            low
            "
        >

            <div
                class="road-summary-icon"
            >
                🟢
            </div>

            <div>

                <span>
                    Low
                </span>

                <strong>
                    ${counts.LOW}
                </strong>

            </div>

        </div>

    `;
}


/* ============================================================
   ROAD COUNT
   ============================================================ */

function updateRoadCount(
    count
) {

    setText(
        "road-count-badge",
        count
    );

    setText(
        "vulnerable-road-count",
        count
    );

    setText(
        "road-count",
        count
    );
}


/* ============================================================
   ROAD LIST
   ============================================================ */

function renderVulnerableRoadList(
    roads
) {

    const container =
        document.getElementById(
            "road-list"
        );


    if (!container) {
        return;
    }


    if (!roads.length) {

        container.innerHTML = `

            <div class="road-empty">

                <div
                    class="road-empty-icon"
                >
                    🛣️
                </div>

                <strong>
                    No vulnerable roads detected
                </strong>

                <span>
                    No road segments matching the
                    current analysis were returned.
                </span>

            </div>

        `;

        return;
    }


    let filtered =
        [...roads];


    /*
       Risk filter
    */

    if (
        activeRoadFilter !== "ALL"
    ) {

        filtered =
            filtered.filter(
                road =>
                    getRoadRiskLevel(
                        road
                    ) === activeRoadFilter
            );
    }


    /*
       Search filter
    */

    if (
        roadSearchText
    ) {

        filtered =
            filtered.filter(
                road => {

                    const name =
                        getRoadName(
                            road
                        ).toLowerCase();


                    const type =
                        getRoadType(
                            road
                        ).toLowerCase();


                    return (
                        name.includes(
                            roadSearchText
                        ) ||
                        type.includes(
                            roadSearchText
                        )
                    );
                }
            );
    }


    /*
       Sorting
    */

    filtered.sort(
        (a, b) => {

            if (
                activeRoadSort ===
                "PROBABILITY"
            ) {

                return (
                    getProbability(b) -
                    getProbability(a)
                );
            }


            if (
                activeRoadSort ===
                "DISTANCE"
            ) {

                const aDistance =
                    safeNumber(
                        a.distance_km,
                        Infinity
                    );


                const bDistance =
                    safeNumber(
                        b.distance_km,
                        Infinity
                    );


                return (
                    aDistance -
                    bDistance
                );
            }


            if (
                activeRoadSort ===
                "NAME"
            ) {

                return getRoadName(a)
                    .localeCompare(
                        getRoadName(b)
                    );
            }


            return (
                getRoadScore(b) -
                getRoadScore(a)
            );
        }
    );


    /*
       Maximum display count
    */

    const displayed =
        filtered.slice(
            0,
            MAX_VULNERABLE_ROADS
        );


    /*
       Filter bar
    */

    const counts = {

        ALL:
            roads.length,

        CRITICAL:
            roads.filter(
                road =>
                    getRoadRiskLevel(
                        road
                    ) === "CRITICAL"
            ).length,

        HIGH:
            roads.filter(
                road =>
                    getRoadRiskLevel(
                        road
                    ) === "HIGH"
            ).length,

        MEDIUM:
            roads.filter(
                road =>
                    getRoadRiskLevel(
                        road
                    ) === "MEDIUM"
            ).length,

        LOW:
            roads.filter(
                road =>
                    getRoadRiskLevel(
                        road
                    ) === "LOW"
            ).length
    };


    container.innerHTML = `

        <div
            class="road-filter-bar"
        >

            ${
                [
                    "ALL",
                    "CRITICAL",
                    "HIGH",
                    "MEDIUM",
                    "LOW"
                ]
                    .map(
                        level => `

                            <button
                                type="button"
                                class="
                                road-filter
                                ${
                                    activeRoadFilter ===
                                    level
                                        ? "active"
                                        : ""
                                }
                                ${
                                    level ===
                                    "CRITICAL"
                                        ? "critical"
                                        : level ===
                                          "HIGH"
                                            ? "high"
                                            : level ===
                                              "MEDIUM"
                                                ? "medium"
                                                : level ===
                                                  "LOW"
                                                    ? "low"
                                                    : ""
                                }
                                "
                                data-road-filter="${level}"
                            >

                                ${
                                    level ===
                                    "ALL"
                                        ? "All"
                                        : level
                                }

                                <span>
                                    ${counts[level]}
                                </span>

                            </button>

                        `
                    )
                    .join("")
            }

        </div>


        ${
            displayed.length
                ? displayed
                    .map(
                        (road, index) =>
                            buildRoadCard(
                                road,
                                index
                            )
                    )
                    .join("")
                : `

                    <div
                        class="road-empty filtered"
                    >

                        <div
                            class="road-empty-icon"
                        >
                            🔎
                        </div>

                        <strong>
                            No matching roads
                        </strong>

                        <span>
                            Try another risk filter
                            or search term.
                        </span>

                    </div>

                  `
        }

    `;


    /*
       Filter events
    */

    container
        .querySelectorAll(
            "[data-road-filter]"
        )
        .forEach(
            button => {

                button.onclick =
                    function() {

                        activeRoadFilter =
                            button.dataset
                                .roadFilter;


                        renderVulnerableRoadList(
                            latestVulnerableRoads
                        );


                        renderVulnerableRoads(
                            latestVulnerableRoads
                        );
                    };
            }
        );


    /*
       Road card events
    */

    container
        .querySelectorAll(
            "[data-road-card]"
        )
        .forEach(
            card => {

                card.onclick =
                    function() {

                        const index =
                            Number(
                                card.dataset
                                    .roadIndex
                            );


                        const road =
                            displayed[index];


                        focusRoadFromData(
                            road
                        );
                    };
            }
        );
}


/* ============================================================
   ROAD CARD
   ============================================================ */

function buildRoadCard(
    road,
    index
) {

    const level =
        getRoadRiskLevel(
            road
        );


    const score =
        getRoadScore(
            road
        );


    const probability =
        getProbability(
            road
        );


    const name =
        getRoadName(
            road,
            index
        );


    const type =
        getRoadType(
            road
        );


    const distance =
        road?.distance_km;


    const geometryAvailable =
        roadHasGeometry(
            road
        );


    const geometryBadge =
        geometryAvailable
            ? `
                <span
                    class="
                    road-geometry-badge
                    available
                    "
                >
                    ● Map available
                </span>
              `
            : `
                <span
                    class="
                    road-geometry-badge
                    unavailable
                    "
                >
                    ○ Map geometry unavailable
                </span>
              `;


    let actionText =
        geometryAvailable
            ? "View on map"
            : "Details";


    return `

        <article
            class="
            road-card
            ${getRiskClass(level)}
            "
            data-road-card
            data-road-index="${index}"
        >

            <div
                class="road-card-accent"
            ></div>


            <div
                class="road-card-main"
            >

                <div
                    class="road-card-header"
                >

                    <div
                        class="
                        road-card-name-block
                        "
                    >

                        <div
                            class="
                            road-icon
                            ${level.toLowerCase()}
                            "
                        >
                            🛣
                        </div>


                        <div>

                            <h3>

                                ${escapeHtml(
                                    name
                                )}

                            </h3>


                            <div
                                class="
                                road-type
                                "
                            >

                                ${escapeHtml(
                                    type
                                )}

                            </div>

                        </div>

                    </div>


                    <div
                        class="
                        road-risk-badge
                        ${level.toLowerCase()}
                        "
                    >

                        <span>
                            ${escapeHtml(level)}
                        </span>

                    </div>

                </div>


                <div
                    class="
                    road-score-section
                    "
                >

                    <div>

                        <span
                            class="
                            road-score-label
                            "
                        >
                            Vulnerability Score
                        </span>


                        <div
                            class="
                            road-score
                            ${getRiskClass(level)}
                            "
                        >

                            ${formatScore(
                                score
                            )}

                            <small>
                                / 100
                            </small>

                        </div>

                    </div>


                    <div
                        class="
                        road-score-bar
                        "
                    >

                        <div
                            class="
                            road-score-fill
                            ${level.toLowerCase()}
                            "
                            style="
                                width:
                                ${Math.min(
                                    100,
                                    Math.max(
                                        0,
                                        score
                                    )
                                )}%;
                            "
                        ></div>

                    </div>

                </div>


                <div
                    class="
                    road-metrics
                    "
                >

                    <div
                        class="
                        road-metric
                        "
                    >

                        <span>
                            Landslide risk
                        </span>

                        <strong
                            class="
                            ${getRiskClass(level)}
                            "
                        >

                            ${formatProbability(
                                probability
                            )}%

                        </strong>

                    </div>


                    <div
                        class="
                        road-metric
                        "
                    >

                        <span>
                            Distance
                        </span>

                        <strong>

                            ${
                                distance !==
                                undefined &&
                                Number.isFinite(
                                    Number(
                                        distance
                                    )
                                )
                                    ? `${formatDistance(
                                        distance
                                    )} km`
                                    : "--"
                            }

                        </strong>

                    </div>


                    <div
                        class="
                        road-metric
                        "
                    >

                        <span>
                            Road type
                        </span>

                        <strong>
                            ${escapeHtml(type)}
                        </strong>

                    </div>

                </div>


                <div
                    class="
                    road-card-footer
                    "
                >

                    ${geometryBadge}


                    <span
                        class="
                        road-card-action
                        "
                    >

                        ${actionText}
                        →

                    </span>

                </div>

            </div>

        </article>

    `;
}


/* ============================================================
   FOCUS ROAD
   ============================================================ */

function focusRoadFromData(
    road
) {

    const coordinates =
        extractRoadCoordinates(
            road
        );


    /*
       If backend did not return
       geometry, do not fabricate it.
    */

    if (
        !coordinates ||
        coordinates.length < 2
    ) {

        const name =
            getRoadName(
                road
            );


        updateMapStatus(
            `${name}: map geometry is currently unavailable.`,
            "loading"
        );


        return;
    }


    const bounds =
        L.latLngBounds(
            coordinates
        );


    map.fitBounds(
        bounds,
        {
            padding:
                [
                    70,
                    70
                ],

            maxZoom:
                15
        }
    );


    /*
       Find corresponding road line
       and highlight it.
    */

    let matchingLine =
        null;


    vulnerableRoadLayer?.eachLayer(
        layer => {

            if (
                layer._roadData ===
                road
            ) {

                matchingLine =
                    layer;
            }
        }
    );


    if (matchingLine) {

        highlightRoad(
            matchingLine
        );

        matchingLine.openPopup();

    }
    else {

        L.popup()
            .setLatLng(
                bounds.getCenter()
            )
            .setContent(
                buildRoadPopup(
                    road,
                    0
                )
            )
            .openOn(
                map
            );
    }
}


/* ============================================================
   ROAD MAP RENDERING
   ============================================================ */

function renderVulnerableRoads(
    roads
) {

    if (
        !map ||
        !vulnerableRoadLayer
    ) {
        return;
    }


    vulnerableRoadLayer.clearLayers();

    selectedRoadLayer?.clearLayers();

    roadLabelsLayer?.clearLayers();


    let visible =
        roads.filter(
            road =>
                activeRoadFilter ===
                "ALL" ||
                getRoadRiskLevel(
                    road
                ) === activeRoadFilter
        );


    if (
        roadSearchText
    ) {

        visible =
            visible.filter(
                road => {

                    const name =
                        getRoadName(
                            road
                        ).toLowerCase();


                    const type =
                        getRoadType(
                            road
                        ).toLowerCase();


                    return (
                        name.includes(
                            roadSearchText
                        ) ||
                        type.includes(
                            roadSearchText
                        )
                    );
                }
            );
    }


    visible =
        visible.slice(
            0,
            MAX_VULNERABLE_ROADS
        );


    visible.forEach(
        (road, index) => {

            const coordinates =
                extractRoadCoordinates(
                    road
                );


            /*
               Skip roads without
               actual geometry.

               They remain visible
               in the road list.
            */

            if (
                !coordinates ||
                coordinates.length < 2
            ) {
                return;
            }


            const level =
                getRoadRiskLevel(
                    road
                );


            const color =
                getRiskColor(
                    level
                );


            const normalWeight =
                level === "CRITICAL"
                    ? 9
                    : level === "HIGH"
                        ? 8
                        : 6;


            const line =
                L.polyline(
                    coordinates,
                    {
                        color,

                        weight:
                            normalWeight,

                        opacity:
                            0.90,

                        lineCap:
                            "round",

                        lineJoin:
                            "round"
                    }
                );


            line._roadData =
                road;


            line.on(
                "mouseover",
                function() {

                    line.setStyle(
                        {
                            weight:
                                normalWeight + 4,

                            opacity:
                                1
                        }
                    );


                    line.bringToFront();

                }
            );


            line.on(
                "mouseout",
                function() {

                    line.setStyle(
                        {
                            weight:
                                normalWeight,

                            opacity:
                                0.90
                        }
                    );
                }
            );


            line.on(
                "click",
                function(event) {

                    highlightRoad(
                        line
                    );


                    map.panTo(
                        event.latlng,
                        {
                            animate:
                                true
                        }
                    );
                }
            );


            line.bindPopup(
                buildRoadPopup(
                    road,
                    index
                )
            );


            line.addTo(
                vulnerableRoadLayer
            );


            /*
               Labels only for high
               and critical roads.
            */

            if (
                level === "CRITICAL" ||
                level === "HIGH"
            ) {

                const midpoint =
                    coordinates[
                        Math.floor(
                            coordinates.length / 2
                        )
                    ];


                L.marker(
                    midpoint,
                    {
                        interactive:
                            false,

                        icon:
                            L.divIcon(
                                {
                                    className:
                                        "road-risk-label",

                                    html:
                                        `
                                            <span>
                                                ${escapeHtml(
                                                    getRoadName(
                                                        road,
                                                        index
                                                    )
                                                )}
                                            </span>
                                        `,

                                    iconSize:
                                        null
                                }
                            )
                    }
                ).addTo(
                    roadLabelsLayer
                );
            }

        }
    );
}


/* ============================================================
   ROAD POPUP
   ============================================================ */

function buildRoadPopup(
    road,
    index
) {

    const level =
        getRoadRiskLevel(
            road
        );


    const score =
        getRoadScore(
            road
        );


    const probability =
        getProbability(
            road
        );


    const distance =
        road?.distance_km;


    const length =
        road?.length_km ??
        road?.road_length_km ??
        road?.length;


    const roadType =
        getRoadType(
            road
        );


    const geometryAvailable =
        roadHasGeometry(
            road
        );


    return `

        <div
            class="
            road-popup
            "
        >

            <div
                class="
                road-popup-title
                "
            >

                🛣

                <strong>
                    ${escapeHtml(
                        getRoadName(
                            road,
                            index
                        )
                    )}
                </strong>

            </div>


            <div
                class="
                road-popup-risk
                ${level.toLowerCase()}
                "
            >

                ${escapeHtml(level)}

            </div>


            <hr>


            <div
                class="
                road-popup-grid
                "
            >

                <div>

                    <span>
                        Vulnerability
                    </span>

                    <strong>
                        ${formatScore(score)}/100
                    </strong>

                </div>


                <div>

                    <span>
                        Landslide probability
                    </span>

                    <strong>
                        ${formatProbability(
                            probability
                        )}%
                    </strong>

                </div>


                <div>

                    <span>
                        Road type
                    </span>

                    <strong>
                        ${escapeHtml(
                            roadType
                        )}
                    </strong>

                </div>


                <div>

                    <span>
                        Distance
                    </span>

                    <strong>
                        ${
                            distance !==
                                undefined &&
                            Number.isFinite(
                                Number(
                                    distance
                                )
                            )
                                ? `${formatDistance(
                                    distance
                                )} km`
                                : "--"
                        }
                    </strong>

                </div>

            </div>


            ${
                length !==
                undefined
                    ? `
                        <div
                            class="
                            road-popup-line
                            "
                        >

                            <span>
                                Road length
                            </span>

                            <strong>
                                ${escapeHtml(
                                    length
                                )} km
                            </strong>

                        </div>
                      `
                    : ""
            }


            <div
                class="
                road-popup-geometry
                ${
                    geometryAvailable
                        ? "available"
                        : "unavailable"
                }
                "
            >

                ${
                    geometryAvailable
                        ? "✓ Road geometry available on map"
                        : "○ Road geometry unavailable"
                }

            </div>


            ${
                road?.reason
                    ? `
                        <div
                            class="
                            road-popup-reason
                            "
                        >

                            <strong>
                                Why vulnerable?
                            </strong>

                            <p>
                                ${escapeHtml(
                                    road.reason
                                )}
                            </p>

                        </div>
                      `
                    : ""
            }


            ${
                road?.recommended_action
                    ? `
                        <div
                            class="
                            road-popup-action
                            "
                        >

                            <strong>
                                Recommended action
                            </strong>

                            <p>
                                ${escapeHtml(
                                    road.recommended_action
                                )}
                            </p>

                        </div>
                      `
                    : ""
            }

        </div>

    `;
}


/* ============================================================
   HIGHLIGHT ROAD
   ============================================================ */

function highlightRoad(
    line
) {

    if (
        !line ||
        !selectedRoadLayer
    ) {
        return;
    }


    selectedRoadLayer.clearLayers();


    const coordinates =
        line.getLatLngs();


    L.polyline(
        coordinates,
        {
            color:
                "#111827",

            weight:
                15,

            opacity:
                0.30,

            lineCap:
                "round",

            lineJoin:
                "round"
        }
    ).addTo(
        selectedRoadLayer
    );


    line.bringToFront();

    line.openPopup();
}


/* ============================================================
   FOCUS ALL ROADS
   ============================================================ */

function focusRoadLayer() {

    if (
        !map ||
        !vulnerableRoadLayer
    ) {
        return;
    }


    const bounds =
        vulnerableRoadLayer.getBounds();


    if (
        bounds.isValid()
    ) {

        map.fitBounds(
            bounds,
            {
                padding:
                    [
                        35,
                        35
                    ],

                maxZoom:
                    14
            }
        );
    }
}


/* ============================================================
   CLEAR ROADS
   ============================================================ */

function clearVulnerableRoads() {

    vulnerableRoadLayer?.clearLayers();

    selectedRoadLayer?.clearLayers();

    roadLabelsLayer?.clearLayers();


    latestVulnerableRoads =
        [];


    activeRoadFilter =
        "ALL";


    activeRoadSort =
        "RISK";


    roadSearchText =
        "";


    updateRoadCount(
        0
    );


    const search =
        document.getElementById(
            "road-search"
        );


    if (search) {
        search.value =
            "";
    }


    const sort =
        document.getElementById(
            "road-sort"
        );


    if (sort) {
        sort.value =
            "RISK";
    }


    const status =
        document.getElementById(
            "road-status"
        );


    if (status) {

        status.innerHTML = `

            <span
                class="road-status-neutral"
            >
                ⓘ
            </span>

            Run Live Risk Analysis to
            identify potentially vulnerable roads.

        `;
    }


    const list =
        document.getElementById(
            "road-list"
        );


    if (list) {

        list.innerHTML = `

            <div class="road-empty">

                <div
                    class="road-empty-icon"
                >
                    🛣️
                </div>

                <strong>
                    Road analysis ready
                </strong>

                <span>
                    Run Live Risk Analysis to
                    identify potentially vulnerable
                    road segments.
                </span>

            </div>

        `;
    }


    const summary =
        document.getElementById(
            "road-summary"
        );


    if (summary) {
        summary.innerHTML =
            "";
    }
}


/* ============================================================
   LIVE ANALYSIS
   ============================================================ */

function registerAnalyzeButton() {

    const button =
        document.getElementById(
            "analyze-button"
        );


    if (!button) {
        return;
    }


    button.onclick =
        runLiveAnalysis;
}


async function runLiveAnalysis() {

    const button =
        document.getElementById(
            "analyze-button"
        );


    if (!button) {
        return;
    }


    if (
        livePredictionController
    ) {

        try {
            livePredictionController.abort();
        }
        catch (_) {}
    }


    const oldHTML =
        button.innerHTML;


    button.disabled =
        true;


    button.innerHTML =
        "Analyzing satellite data… ⏳";


    setAnalysisStatus(
        "loading",
        "🛰 Fetching satellite data from Google Earth Engine…"
    );


    updateMapStatus(
        "🛰 Google Earth Engine analysis running…",
        "loading"
    );


    setPipelineActive(
        2
    );


    try {

        const result =
            await loadLivePrediction();


        if (!result) {

            throw new Error(
                "Live prediction returned no result."
            );
        }


        setAnalysisStatus(
            "success",
            "✓ Live satellite risk analysis completed."
        );


        updateMapStatus(
            "✓ Live risk analysis completed.",
            "normal"
        );


        setPipelineActive(
            5
        );


        await Promise.allSettled(
            [
                loadAllRiskPoints(),

                loadRiskHistory()
            ]
        );


        /*
           Road analysis comes AFTER
           live landslide prediction.
        */

        await loadVulnerableRoads(
            result
        );


    }
    catch (error) {

        console.error(
            "Live analysis:",
            error
        );


        setAnalysisStatus(
            "error",
            `❌ ${error.message}`
        );


        updateMapStatus(
            "Live analysis failed.",
            "error"
        );

    }
    finally {

        button.disabled =
            false;


        button.innerHTML =
            oldHTML;
    }
}


/* ============================================================
   LIVE PREDICTION
   ============================================================ */

async function loadLivePrediction() {

    const riskElement =
        document.getElementById(
            "risk"
        );


    const resultElement =
        document.getElementById(
            "prediction-result"
        );


    if (riskElement) {

        riskElement.innerHTML = `

            <div
                class="prediction-loading"
            >

                <div>
                    🛰
                </div>

                <strong>
                    Processing live satellite data…
                </strong>

                <span>
                    Google Earth Engine is extracting
                    environmental features.
                </span>

            </div>

        `;
    }


    if (resultElement) {

        resultElement.className =
            "prediction-result loading";


        resultElement.innerHTML = `

            <div
                class="prediction-placeholder"
            >

                <div
                    class="
                    prediction-placeholder-icon
                    "
                >
                    🛰
                </div>

                <div>

                    <strong>
                        Running satellite analysis…
                    </strong>

                    <p>
                        Google Earth Engine
                        →
                        Feature Extraction
                        →
                        SVM RBF
                    </p>

                </div>

            </div>

        `;
    }


    livePredictionController =
        new AbortController();


    const timeout =
        setTimeout(
            () => {

                try {
                    livePredictionController.abort();
                }
                catch (_) {}

            },
            LIVE_PREDICTION_TIMEOUT
        );


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/live-predict`,
                {
                    method:
                        "POST",

                    headers:
                        {
                            "Content-Type":
                                "application/json"
                        },

                    body:
                        JSON.stringify(
                            {
                                latitude:
                                    selectedLatitude,

                                longitude:
                                    selectedLongitude,

                                radius_km:
                                    RADIUS_KM
                            }
                        ),

                    signal:
                        livePredictionController.signal
                }
            );


        clearTimeout(
            timeout
        );


        if (!response.ok) {

            let message =
                `Live prediction failed (HTTP ${response.status}).`;


            try {

                const errorData =
                    await response.json();


                if (
                    errorData?.detail
                ) {

                    message =
                        typeof errorData.detail === "string"
                            ? errorData.detail
                            : JSON.stringify(
                                errorData.detail
                            );
                }

            }
            catch (_) {}


            throw new Error(
                message
            );
        }


        const data =
            await response.json();


        lastLivePrediction =
            data;


        hasLivePrediction =
            true;


        displayLivePrediction(
            data
        );


        displayPredictionResult(
            data
        );


        updateLiveAlert(
            data
        );


        updateLastUpdated(
            data.created_at
        );


        await loadAllRiskPoints();


        return data;

    }
    catch (error) {

        clearTimeout(
            timeout
        );


        const message =
            error.name === "AbortError"
                ? "Satellite analysis timed out after 90 seconds."
                : error.message;


        if (resultElement) {

            resultElement.className =
                "prediction-result high";


            resultElement.innerHTML = `

                <strong>
                    ❌ AI analysis failed
                </strong>

                <br><br>

                ${escapeHtml(
                    message
                )}

            `;
        }


        throw new Error(
            message
        );
    }
}


/* ============================================================
   DISPLAY LIVE PREDICTION
   ============================================================ */

function displayLivePrediction(
    data
) {

    const element =
        document.getElementById(
            "risk"
        );


    if (!element) {
        return;
    }


    const level =
        String(
            data.risk_level ??
            "UNKNOWN"
        ).toUpperCase();


    const probability =
        formatProbability(
            data.landslide_probability ??
            data.risk_probability ??
            data.probability
        );


    element.innerHTML = `

        <div
            class="
            risk-main
            ${getRiskClass(level)}
            "
        >

            ${escapeHtml(level)}

        </div>


        <div
            class="
            risk-probability
            "
        >

            ${probability}%

            <span>
                landslide probability
            </span>

        </div>


        <div
            class="
            risk-meta
            "
        >

            <strong>
                Prediction:
            </strong>

            ${escapeHtml(
                data.prediction ??
                "--"
            )}

            <br>


            <strong>
                Model:
            </strong>

            ${escapeHtml(
                data.model ??
                "SVM RBF"
            )}

            <br>


            <strong>
                Latitude:
            </strong>

            ${safeNumber(
                data.latitude,
                selectedLatitude
            ).toFixed(5)}

            <br>


            <strong>
                Longitude:
            </strong>

            ${safeNumber(
                data.longitude,
                selectedLongitude
            ).toFixed(5)}

            ${
                data.created_at
                    ? `
                        <br>

                        <strong>
                            Updated:
                        </strong>

                        ${formatDateTime(
                            data.created_at
                        )}
                      `
                    : ""
            }


            ${
                data.recommended_action
                    ? `
                        <br><br>

                        <strong>
                            Recommended Action:
                        </strong>

                        <br>

                        ${escapeHtml(
                            data.recommended_action
                        )}
                      `
                    : ""
            }

        </div>

    `;


    setText(
        "current-risk",
        level
    );


    setText(
        "highest-risk",
        level
    );


    setText(
        "prediction-model",
        data.model ??
        "SVM RBF"
    );
}


/* ============================================================
   PREDICTION RESULT
   ============================================================ */

function displayPredictionResult(
    data
) {

    const element =
        document.getElementById(
            "prediction-result"
        );


    if (!element) {
        return;
    }


    const level =
        String(
            data.risk_level ??
            "UNKNOWN"
        ).toUpperCase();


    const probability =
        formatProbability(
            data.landslide_probability ??
            data.risk_probability ??
            data.probability
        );


    element.className =
        `prediction-result ${getRiskClass(level)}`;


    element.innerHTML = `

        <div
            class="
            prediction-risk
            ${getRiskClass(level)}
            "
        >

            ${escapeHtml(level)}
            RISK

        </div>


        <div
            class="
            prediction-probability
            "
        >

            ${probability}%

            <span>
                estimated probability
            </span>

        </div>


        <div
            class="
            prediction-meta
            "
        >

            <strong>
                Model:
            </strong>

            ${escapeHtml(
                data.model ??
                "SVM RBF"
            )}

            <br>


            <strong>
                Prediction:
            </strong>

            ${escapeHtml(
                data.prediction ??
                "--"
            )}

            <br>


            <strong>
                Location:
            </strong>

            ${selectedLatitude.toFixed(5)},
            ${selectedLongitude.toFixed(5)}

            ${
                data.recommended_action
                    ? `
                        <br><br>

                        <strong>
                            Recommended Action:
                        </strong>

                        ${escapeHtml(
                            data.recommended_action
                        )}
                      `
                    : ""
            }

        </div>

    `;
}


/* ============================================================
   LIVE ALERT
   ============================================================ */

function updateLiveAlert(
    data
) {

    const element =
        document.getElementById(
            "alerts"
        );


    if (!element) {
        return;
    }


    const level =
        String(
            data.risk_level ??
            "LOW"
        ).toUpperCase();


    const probability =
        formatProbability(
            data.landslide_probability ??
            data.risk_probability ??
            data.probability
        );


    const configuration = {

        CRITICAL:
            [
                "high",
                "🚨",
                "CRITICAL LANDSLIDE RISK",
                "Very high landslide risk detected."
            ],

        HIGH:
            [
                "high",
                "🚨",
                "HIGH LANDSLIDE RISK",
                "Live satellite analysis indicates high risk."
            ],

        MEDIUM:
            [
                "medium",
                "⚠",
                "MEDIUM LANDSLIDE RISK",
                "Elevated landslide risk detected."
            ],

        LOW:
            [
                "low",
                "✓",
                "LOW LANDSLIDE RISK",
                "No immediate landslide warning detected."
            ]

    };


    const config =
        configuration[level] ??
        configuration.LOW;


    element.innerHTML = `

        <div
            class="
            alert
            ${config[0]}
            "
        >

            <span
                class="alert-symbol"
            >
                ${config[1]}
            </span>


            <div>

                <strong>
                    ${config[2]}
                </strong>


                <p>

                    ${config[3]}

                    <br>

                    Probability:

                    <strong>
                        ${probability}%
                    </strong>


                    ${
                        data.recommended_action
                            ? `
                                <br>

                                Recommended:

                                ${escapeHtml(
                                    data.recommended_action
                                )}
                              `
                            : ""
                    }

                </p>

            </div>

        </div>

    `;
}


/* ============================================================
   RISK HISTORY
   ============================================================ */

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
            `&radius_km=${RADIUS_KM}` +
            `&limit=${HISTORY_LIMIT}`;


        const response =
            await fetch(
                url
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        displayRiskHistory(
            data
        );


        return data;

    }
    catch (error) {

        console.error(
            "Risk history:",
            error
        );


        showHistoryMessage(
            "Unable to load risk history."
        );


        return null;
    }
}


function displayRiskHistory(
    data
) {

    const container =
        document.getElementById(
            "history"
        );


    if (!container) {
        return;
    }


    let predictions =
        Array.isArray(
            data?.predictions
        )
            ? data.predictions
            : extractRiskArray(
                data
            );


    predictions =
        [...predictions].sort(
            (a, b) =>
                new Date(
                    a.created_at
                ) -
                new Date(
                    b.created_at
                )
        );


    if (
        !predictions.length
    ) {

        destroyHistoryChart();


        container.innerHTML = `

            <div
                class="
                history-chart-container
                "
            >

                <canvas
                    id="riskHistoryChart"
                ></canvas>

            </div>


            <div
                class="
                history-empty
                "
            >

                No historical predictions
                available for this location.

            </div>

        `;


        return;
    }


    container.innerHTML = `

        <div
            class="
            history-chart-container
            "
        >

            <canvas
                id="riskHistoryChart"
            ></canvas>

        </div>

    `;


    const canvas =
        document.getElementById(
            "riskHistoryChart"
        );


    if (
        !canvas ||
        typeof Chart === "undefined"
    ) {
        return;
    }


    destroyHistoryChart();


    riskHistoryChart =
        new Chart(
            canvas,
            {
                type:
                    "line",

                data:
                    {
                        labels:
                            predictions.map(
                                prediction =>
                                    formatTime(
                                        prediction.created_at
                                    )
                            ),

                        datasets:
                            [
                                {
                                    label:
                                        "Landslide Probability (%)",

                                    data:
                                        predictions.map(
                                            prediction =>
                                                getProbability(
                                                    prediction
                                                ) * 100
                                        ),

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

                options:
                    {
                        responsive:
                            true,

                        maintainAspectRatio:
                            false,

                        interaction:
                            {
                                intersect:
                                    false,

                                mode:
                                    "index"
                            },

                        scales:
                            {
                                y:
                                    {
                                        min:
                                            0,

                                        max:
                                            100,

                                        title:
                                            {
                                                display:
                                                    true,

                                                text:
                                                    "Probability (%)"
                                            }
                                    }
                            }
                    }
            }
        );
}


function destroyHistoryChart() {

    if (
        riskHistoryChart
    ) {

        try {

            riskHistoryChart.destroy();

        }
        catch (_) {}


        riskHistoryChart =
            null;
    }
}


function showHistoryMessage(
    message
) {

    const element =
        document.getElementById(
            "history"
        );


    if (!element) {
        return;
    }


    destroyHistoryChart();


    element.innerHTML = `

        <div
            class="
            history-empty
            "
        >

            ${escapeHtml(message)}

        </div>

    `;
}


/* ============================================================
   UI RESET
   ============================================================ */

function resetRiskPanel() {

    const element =
        document.getElementById(
            "risk"
        );


    if (!element) {
        return;
    }


    element.innerHTML = `

        <div
            class="
            risk-placeholder
            "
        >

            <div
                class="
                placeholder-icon
                "
            >
                🛰
            </div>


            <strong>
                Ready for analysis
            </strong>


            <span>
                Click "Analyze Live Risk"
                to run satellite-based prediction.
            </span>

        </div>

    `;
}


function resetPredictionPanel() {

    const element =
        document.getElementById(
            "prediction-result"
        );


    if (!element) {
        return;
    }


    element.className =
        "prediction-result";


    element.innerHTML = `

        <div
            class="
            prediction-placeholder
            "
        >

            <div
                class="
                prediction-placeholder-icon
                "
            >
                🤖
            </div>


            <div>

                <strong>
                    Ready for AI analysis
                </strong>


                <p>

                    Select a location and click
                    <strong>
                        Analyze Live Risk
                    </strong>.

                </p>

            </div>

        </div>

    `;


    setPipelineActive(
        1
    );
}


function setAnalysisStatus(
    type,
    message
) {

    const element =
        document.getElementById(
            "analysis-status"
        );


    if (!element) {
        return;
    }


    element.className =
        `analysis-status ${type}`;


    element.textContent =
        message;
}


function setPipelineActive(
    stage
) {

    document
        .querySelectorAll(
            ".pipeline-step"
        )
        .forEach(
            (step, index) => {

                if (
                    index < stage
                ) {

                    step.style.borderColor =
                        "#bfdbfe";


                    step.style.background =
                        "#eff6ff";

                }
                else {

                    step.style.borderColor =
                        "#e2e8f0";


                    step.style.background =
                        "#f8fafc";
                }

            }
        );
}


function updateLastUpdated(
    timestamp = null
) {

    setText(
        "last-updated",
        timestamp
            ? formatTime(timestamp)
            : new Date()
                .toLocaleTimeString(
                    "en-IN"
                )
    );
}


/* ============================================================
   ROAD + MAP UI CSS
   ============================================================ */

function injectRoadStyles() {

    if (
        document.getElementById(
            "road-intelligence-styles"
        )
    ) {
        return;
    }


    const style =
        document.createElement(
            "style"
        );


    style.id =
        "road-intelligence-styles";


    style.textContent = `

        /* ====================================================
           ROAD PANEL
           ==================================================== */

        .vulnerable-roads-panel {
            position: relative;
            overflow: hidden;
        }


        .road-panel-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 16px;
        }


        .road-title-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }


        .road-title-icon {
            width: 46px;
            height: 46px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            background: #eff6ff;
            font-size: 24px;
            flex-shrink: 0;
        }


        .road-panel-header h2 {
            margin: 0;
            font-size: 21px;
            color: #0f172a;
        }


        .road-panel-header p {
            margin: 4px 0 0;
            color: #64748b;
            font-size: 13px;
        }


        .road-count-badge {
            min-width: 46px;
            height: 46px;
            padding: 0 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: #f1f5f9;
            color: #0f172a;
            font-weight: 800;
            font-size: 17px;
        }


        /* ====================================================
           STATUS
           ==================================================== */

        .road-status {
            display: flex;
            align-items: center;
            gap: 7px;
            min-height: 42px;
            padding: 11px 14px;
            border-radius: 10px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            color: #475569;
            font-size: 13px;
            margin-bottom: 16px;
        }


        .road-status-success {
            color: #16a34a;
            font-weight: 800;
        }


        .road-status-error {
            color: #dc2626;
            font-weight: 800;
        }


        .road-status-neutral {
            color: #2563eb;
            font-weight: 800;
        }


        .road-status-spinner {
            display: inline-block;
            animation: road-spin 1s linear infinite;
        }


        @keyframes road-spin {
            from {
                transform: rotate(0deg);
            }

            to {
                transform: rotate(360deg);
            }
        }


        /* ====================================================
           SUMMARY
           ==================================================== */

        .road-summary {
            display: grid;
            grid-template-columns:
                repeat(5, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 18px;
        }


        .road-summary-card {
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 72px;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            background: #ffffff;
        }


        .road-summary-icon {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9px;
            background: #f8fafc;
            font-size: 16px;
        }


        .road-summary-card span {
            display: block;
            color: #64748b;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 2px;
        }


        .road-summary-card strong {
            display: block;
            color: #0f172a;
            font-size: 20px;
        }


        .road-summary-card.critical strong {
            color: #991b1b;
        }


        .road-summary-card.high strong {
            color: #dc2626;
        }


        .road-summary-card.medium strong {
            color: #d97706;
        }


        .road-summary-card.low strong {
            color: #16a34a;
        }


        /* ====================================================
           TOOLBAR
           ==================================================== */

        .road-toolbar {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }


        .road-search-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            height: 42px;
            border: 1px solid #dbe3ec;
            border-radius: 10px;
            background: #ffffff;
        }


        .road-search-wrapper span {
            color: #64748b;
        }


        .road-search-wrapper input {
            width: 100%;
            height: 100%;
            border: 0;
            outline: 0;
            background: transparent;
            color: #0f172a;
            font-size: 13px;
        }


        .road-sort {
            height: 42px;
            min-width: 210px;
            padding: 0 11px;
            border: 1px solid #dbe3ec;
            border-radius: 10px;
            background: #ffffff;
            color: #334155;
            font-size: 13px;
            outline: none;
        }


        /* ====================================================
           FILTERS
           ==================================================== */

        .road-filter-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-bottom: 13px;
        }


        .road-filter {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 8px 12px;
            border: 1px solid #dbe3ec;
            border-radius: 999px;
            background: #ffffff;
            color: #475569;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition:
                transform .15s ease,
                background .15s ease,
                border-color .15s ease;
        }


        .road-filter:hover {
            transform: translateY(-1px);
            background: #f8fafc;
        }


        .road-filter span {
            min-width: 21px;
            height: 21px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: #f1f5f9;
            color: #64748b;
            font-size: 10px;
        }


        .road-filter.active {
            background: #0f172a;
            border-color: #0f172a;
            color: #ffffff;
        }


        .road-filter.active span {
            background: rgba(255,255,255,.18);
            color: #ffffff;
        }


        .road-filter.critical.active {
            background: #991b1b;
            border-color: #991b1b;
        }


        .road-filter.high.active {
            background: #dc2626;
            border-color: #dc2626;
        }


        .road-filter.medium.active {
            background: #d97706;
            border-color: #d97706;
        }


        .road-filter.low.active {
            background: #16a34a;
            border-color: #16a34a;
        }


        /* ====================================================
           ROAD CARD
           ==================================================== */

        .road-card {
            position: relative;
            display: flex;
            overflow: hidden;
            margin-bottom: 10px;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            background: #ffffff;
            cursor: pointer;
            transition:
                transform .18s ease,
                box-shadow .18s ease,
                border-color .18s ease;
        }


        .road-card:hover {
            transform: translateY(-2px);
            border-color: #cbd5e1;
            box-shadow:
                0 8px 24px rgba(15,23,42,.08);
        }


        .road-card-accent {
            width: 5px;
            flex-shrink: 0;
            background: #16a34a;
        }


        .road-card.risk-medium
        .road-card-accent {
            background: #d97706;
        }


        .road-card.risk-high
        .road-card-accent {
            background: #dc2626;
        }


        .road-card-main {
            flex: 1;
            padding: 15px 17px;
        }


        .road-card-header {
            display: flex;
            justify-content: space-between;
            gap: 15px;
            align-items: flex-start;
        }


        .road-card-name-block {
            display: flex;
            gap: 11px;
            align-items: center;
        }


        .road-icon {
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            background: #f0fdf4;
            font-size: 18px;
        }


        .road-icon.medium {
            background: #fffbeb;
        }


        .road-icon.high,
        .road-icon.critical {
            background: #fef2f2;
        }


        .road-card h3 {
            margin: 0;
            color: #0f172a;
            font-size: 15px;
        }


        .road-type {
            margin-top: 3px;
            color: #64748b;
            font-size: 11px;
        }


        .road-risk-badge {
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: .03em;
        }


        .road-risk-badge.low {
            background: #dcfce7;
            color: #15803d;
        }


        .road-risk-badge.medium {
            background: #fef3c7;
            color: #b45309;
        }


        .road-risk-badge.high {
            background: #fee2e2;
            color: #b91c1c;
        }


        .road-risk-badge.critical {
            background: #fecaca;
            color: #991b1b;
        }


        /* ====================================================
           SCORE
           ==================================================== */

        .road-score-section {
            margin-top: 14px;
        }


        .road-score-label {
            color: #64748b;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .04em;
        }


        .road-score {
            margin-top: 2px;
            font-size: 21px;
            font-weight: 900;
        }


        .road-score small {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 600;
        }


        .road-score-bar {
            height: 6px;
            margin-top: 7px;
            overflow: hidden;
            border-radius: 99px;
            background: #f1f5f9;
        }


        .road-score-fill {
            height: 100%;
            border-radius: inherit;
            transition: width .4s ease;
        }


        .road-score-fill.low {
            background: #16a34a;
        }


        .road-score-fill.medium {
            background: #f59e0b;
        }


        .road-score-fill.high {
            background: #dc2626;
        }


        .road-score-fill.critical {
            background: #991b1b;
        }


        /* ====================================================
           METRICS
           ==================================================== */

        .road-metrics {
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin-top: 13px;
        }


        .road-metric {
            padding: 9px 10px;
            border-radius: 9px;
            background: #f8fafc;
        }


        .road-metric span {
            display: block;
            color: #64748b;
            font-size: 10px;
        }


        .road-metric strong {
            display: block;
            margin-top: 3px;
            color: #0f172a;
            font-size: 12px;
        }


        /* ====================================================
           FOOTER
           ==================================================== */

        .road-card-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #f1f5f9;
        }


        .road-geometry-badge {
            font-size: 10px;
            font-weight: 700;
        }


        .road-geometry-badge.available {
            color: #16a34a;
        }


        .road-geometry-badge.unavailable {
            color: #94a3b8;
        }


        .road-card-action {
            color: #2563eb;
            font-size: 11px;
            font-weight: 800;
        }


        /* ====================================================
           EMPTY / LOADING / ERROR
           ==================================================== */

        .road-empty,
        .road-loading,
        .road-error {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            min-height: 145px;
            padding: 28px;
            border: 1px dashed #cbd5e1;
            border-radius: 13px;
            background: #f8fafc;
            text-align: center;
        }


        .road-empty {
            flex-direction: column;
        }


        .road-empty-icon {
            font-size: 30px;
            opacity: .75;
        }


        .road-empty strong {
            color: #334155;
            font-size: 14px;
        }


        .road-empty span {
            color: #64748b;
            font-size: 12px;
        }


        .road-loading {
            justify-content: flex-start;
            text-align: left;
        }


        .road-loading-spinner {
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: #eff6ff;
            color: #2563eb;
            animation: road-spin 1s linear infinite;
        }


        .road-loading strong,
        .road-loading span,
        .road-error strong,
        .road-error span {
            display: block;
        }


        .road-loading strong,
        .road-error strong {
            color: #334155;
            font-size: 13px;
        }


        .road-loading span,
        .road-error span {
            margin-top: 3px;
            color: #64748b;
            font-size: 11px;
        }


        .road-error {
            justify-content: flex-start;
            text-align: left;
            background: #fff7f7;
            border-color: #fecaca;
        }


        .road-error-icon {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9px;
            background: #fee2e2;
            color: #dc2626;
        }


        /* ====================================================
           MAP TOOLS
           ==================================================== */

        .map-tools {
            display: flex;
            gap: 4px;
            padding: 4px;
            border-radius: 10px;
            background: #ffffff;
            box-shadow:
                0 4px 16px rgba(15,23,42,.18);
        }


        .map-tools button {
            width: 34px;
            height: 34px;
            border: 0;
            border-radius: 7px;
            background: #ffffff;
            color: #334155;
            cursor: pointer;
            font-size: 15px;
        }


        .map-tools button:hover {
            background: #f1f5f9;
        }


        /* ====================================================
           MAP LEGEND
           ==================================================== */

        .map-legend {
            min-width: 165px;
            padding: 11px 13px;
            border-radius: 10px;
            background: rgba(255,255,255,.96);
            box-shadow:
                0 4px 18px rgba(15,23,42,.16);
            color: #475569;
            font-size: 11px;
            line-height: 1.8;
        }


        .legend-title {
            margin-bottom: 4px;
            color: #0f172a;
            font-weight: 800;
        }


        .legend-row {
            display: flex;
            align-items: center;
            gap: 7px;
        }


        .legend-circle {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            display: inline-block;
        }


        .legend-circle.low {
            background: #16a34a;
        }


        .legend-circle.medium {
            background: #f59e0b;
        }


        .legend-circle.high {
            background: #dc2626;
        }


        .legend-circle.critical {
            background: #991b1b;
        }


        .legend-road {
            width: 22px;
            height: 4px;
            border-radius: 99px;
            display: inline-block;
        }


        .legend-road.low {
            background: #16a34a;
        }


        .legend-road.medium {
            background: #f59e0b;
        }


        .legend-road.high {
            background: #dc2626;
        }


        .legend-road.critical {
            background: #991b1b;
        }


        .legend-divider {
            height: 1px;
            margin: 5px 0;
            background: #e2e8f0;
        }


        /* ====================================================
           ROAD LABEL
           ==================================================== */

        .road-risk-label {
            background: transparent;
            border: 0;
        }


        .road-risk-label span {
            display: block;
            padding: 3px 6px;
            border-radius: 5px;
            background: rgba(15,23,42,.88);
            color: #ffffff;
            white-space: nowrap;
            font-size: 10px;
            font-weight: 700;
            box-shadow:
                0 2px 8px rgba(0,0,0,.18);
        }


        /* ====================================================
           POPUP
           ==================================================== */

        .road-popup {
            min-width: 235px;
            color: #334155;
        }


        .road-popup-title {
            display: flex;
            gap: 7px;
            align-items: center;
            color: #0f172a;
            font-size: 14px;
        }


        .road-popup hr {
            border: 0;
            border-top: 1px solid #e2e8f0;
            margin: 9px 0;
        }


        .road-popup-risk {
            display: inline-block;
            margin-top: 7px;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 800;
        }


        .road-popup-risk.low {
            background: #dcfce7;
            color: #15803d;
        }


        .road-popup-risk.medium {
            background: #fef3c7;
            color: #b45309;
        }


        .road-popup-risk.high {
            background: #fee2e2;
            color: #b91c1c;
        }


        .road-popup-risk.critical {
            background: #fecaca;
            color: #991b1b;
        }


        .road-popup-grid {
            display: grid;
            grid-template-columns:
                repeat(2, minmax(0, 1fr));
            gap: 8px;
        }


        .road-popup-grid div {
            padding: 7px;
            border-radius: 7px;
            background: #f8fafc;
        }


        .road-popup-grid span,
        .road-popup-line span {
            display: block;
            color: #64748b;
            font-size: 9px;
        }


        .road-popup-grid strong,
        .road-popup-line strong {
            display: block;
            margin-top: 2px;
            color: #0f172a;
            font-size: 11px;
        }


        .road-popup-line {
            margin-top: 8px;
            padding: 8px;
            border-radius: 7px;
            background: #f8fafc;
        }


        .road-popup-geometry {
            margin-top: 9px;
            font-size: 10px;
            font-weight: 700;
        }


        .road-popup-geometry.available {
            color: #16a34a;
        }


        .road-popup-geometry.unavailable {
            color: #64748b;
        }


        .road-popup-reason,
        .road-popup-action {
            margin-top: 10px;
            padding: 9px;
            border-radius: 8px;
            background: #f8fafc;
        }


        .road-popup-reason strong,
        .road-popup-action strong {
            font-size: 10px;
            color: #334155;
        }


        .road-popup-reason p,
        .road-popup-action p {
            margin: 4px 0 0;
            font-size: 10px;
            line-height: 1.45;
        }


        /* ====================================================
           SELECTED LOCATION
           ==================================================== */

        .selected-location-grid {
            display: grid;
            gap: 8px;
        }


        .selected-location-grid div {
            display: flex;
            justify-content: space-between;
            gap: 15px;
            padding-bottom: 6px;
            border-bottom: 1px solid #f1f5f9;
        }


        .selected-location-grid span {
            color: #64748b;
            font-size: 11px;
        }


        .selected-location-grid strong {
            color: #0f172a;
            font-size: 12px;
        }


        /* ====================================================
           RESPONSIVE
           ==================================================== */

        @media (max-width: 850px) {

            .road-summary {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }


            .road-toolbar {
                flex-direction: column;
                align-items: stretch;
            }


            .road-sort {
                width: 100%;
            }


            .road-metrics {
                grid-template-columns:
                    1fr;
            }
        }


        @media (max-width: 520px) {

            .road-summary {
                grid-template-columns:
                    1fr;
            }


            .road-panel-header {
                align-items: center;
            }


            .road-card-header {
                flex-direction: column;
            }


            .road-count-badge {
                min-width: 40px;
                height: 40px;
            }
        }

    `;


    document.head.appendChild(
        style
    );
}


/* ============================================================
   AUTO REFRESH
   ============================================================ */

setInterval(
    async () => {

        if (
            !dashboardInitialized
        ) {
            return;
        }


        /*
           Refresh database/weather
           information.

           Do NOT automatically rerun
           Earth Engine every 30 seconds.
        */

        await Promise.allSettled(
            [
                loadLocalRisk(),

                loadRiskHistory(),

                loadAllRiskPoints()
            ]
        );


        updateLastUpdated();

    },
    REFRESH_INTERVAL
);


/* ============================================================
   RESIZE
   ============================================================ */

window.addEventListener(
    "resize",
    () => {

        setTimeout(
            () => {

                if (map) {

                    map.invalidateSize();
                }

            },
            150
        );

    }
);


/* ============================================================
   INITIALISATION
   ============================================================ */

async function initializeDashboard() {

    if (
        dashboardInitialized
    ) {
        return;
    }


    /*
       Inject road-specific
       professional UI styles.
    */

    injectRoadStyles();


    /*
       Initialise Leaflet.
    */

    if (
        !initializeMap()
    ) {
        return;
    }


    dashboardInitialized =
        true;


    /*
       Build road intelligence panel.
    */

    ensureVulnerableRoadPanel();


    /*
       Register events.
    */

    registerMapClick();

    registerAnalyzeButton();


    /*
       Initial map/location.
    */

    updateSelectedLocation();

    updateMapSelection();


    /*
       Do NOT show road data until
       live analysis is performed.
    */

    clearVulnerableRoads();


    updateMapStatus(
        "🛰 Live monitoring active",
        "normal"
    );


    setPipelineActive(
        1
    );


    /*
       Initial data loading.
    */

    await Promise.allSettled(
        [

            loadWeather(
                selectedLatitude,
                selectedLongitude
            ),

            loadLocalRisk(),

            loadAllRiskPoints(),

            loadRiskHistory()

        ]
    );


    updateLastUpdated();


    /*
       Leaflet needs a size refresh
       after the dashboard becomes visible.
    */

    setTimeout(
        () => {

            if (map) {

                map.invalidateSize();
            }

        },
        250
    );
}


/* ============================================================
   COMPATIBILITY
   ============================================================ */

function runPrediction() {

    return runLiveAnalysis();
}


/* ============================================================
   START
   ============================================================ */

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeDashboard
    );

}
else {

    initializeDashboard();
}


console.log(
    "NER Landslide Early Warning System — Road Intelligence app.js loaded."
);