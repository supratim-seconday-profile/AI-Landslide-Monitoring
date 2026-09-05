/* ============================================================
   NER LANDSLIDE EARLY WARNING SYSTEM
   ALERT & NOTIFICATION CENTER
   ============================================================ */

"use strict";


/* ============================================================
   CONFIGURATION
   ============================================================ */

const ALERT_API =
    window.API_BASE_URL ||
    "http://127.0.0.1:8000";


const ALERT_SUBSCRIBER_STORAGE_KEY =
    "ner_alert_subscriber_id";


/* ============================================================
   STATE
   ============================================================ */

let registeredSubscriberId =
    localStorage.getItem(
        ALERT_SUBSCRIBER_STORAGE_KEY
    );


/* ============================================================
   HELPER
   ============================================================ */

function alertElement(id) {

    return document.getElementById(id);

}


function alertSetText(id, value) {

    const element =
        alertElement(id);

    if (element) {

        element.textContent =
            value;

    }

}


/* ============================================================
   GET CURRENT SELECTED LOCATION
   ============================================================ */

function getAlertSelectedCoordinates() {

    /*
     * IMPORTANT:
     *
     * We intentionally use the selected location.
     *
     * We NEVER use mouse coordinates.
     * We NEVER use map pointer position.
     *
     * The selected location is changed only by
     * the main dashboard's explicit map selection.
     */

    if (
        typeof window.selectedLatitude !==
        "undefined" &&
        typeof window.selectedLongitude !==
        "undefined"
    ) {

        const latitude =
            Number(
                window.selectedLatitude
            );

        const longitude =
            Number(
                window.selectedLongitude
            );


        if (
            Number.isFinite(latitude) &&
            Number.isFinite(longitude)
        ) {

            return {
                latitude,
                longitude
            };

        }

    }


    /*
     * Fallback.
     */

    return {

        latitude:
            27.338,

        longitude:
            88.606

    };

}


/* ============================================================
   UPDATE LOCATION DISPLAY
   ============================================================ */

function updateAlertCenterLocation() {

    const coordinates =
        getAlertSelectedCoordinates();


    const text =
        `${coordinates.latitude.toFixed(5)}, ` +
        `${coordinates.longitude.toFixed(5)}`;


    alertSetText(
        "alert-monitor-location",
        text
    );


    const locationInput =
        alertElement(
            "alert-subscriber-location"
        );


    if (locationInput) {

        locationInput.value =
            text;

    }

}


/* ============================================================
   NETWORK STATUS
   ============================================================ */

function updateNetworkState() {

    const online =
        navigator.onLine;


    const status =
        alertElement(
            "alert-system-status"
        );


    const badge =
        alertElement(
            "offline-alert-badge"
        );


    const title =
        alertElement(
            "offline-alert-title"
        );


    const message =
        alertElement(
            "offline-alert-message"
        );


    if (online) {

        if (status) {

            status.textContent =
                "● ALERT SYSTEM ONLINE";

            status.className =
                "alert-system-status online";

        }


        if (badge) {

            badge.textContent =
                "ONLINE";

            badge.className =
                "offline-alert-badge online";

        }


        if (title) {

            title.textContent =
                "Connectivity Monitoring Active";

        }


        if (message) {

            message.textContent =
                "The system is connected and " +
                "automatic emergency alerts can be delivered.";

        }

    }

    else {

        if (status) {

            status.textContent =
                "● OFFLINE MODE";

            status.className =
                "alert-system-status offline";

        }


        if (badge) {

            badge.textContent =
                "OFFLINE";

            badge.className =
                "offline-alert-badge offline";

        }


        if (title) {

            title.textContent =
                "Offline Alert Protection Active";

        }


        if (message) {

            message.textContent =
                "Internet connection is unavailable. " +
                "The dashboard will retain the last known " +
                "risk state locally.";

        }

    }

}


/* ============================================================
   REGISTER SUBSCRIBER
   ============================================================ */

async function registerAlertSubscriber() {

    const nameInput =
        alertElement(
            "alert-subscriber-name"
        );


    const phoneInput =
        alertElement(
            "alert-subscriber-phone"
        );


    const radiusInput =
        alertElement(
            "alert-radius"
        );


    const smsInput =
        alertElement(
            "enable-subscriber-sms"
        );


    const pushInput =
        alertElement(
            "enable-subscriber-push"
        );


    const status =
        alertElement(
            "alert-registration-status"
        );


    const name =
        nameInput
            ?.value
            ?.trim();


    const phone =
        phoneInput
            ?.value
            ?.trim();


    const radius =
        Number(
            radiusInput?.value ||
            5
        );


    const smsEnabled =
        Boolean(
            smsInput?.checked
        );


    const pushEnabled =
        Boolean(
            pushInput?.checked
        );


    const coordinates =
        getAlertSelectedCoordinates();


    /* --------------------------------------------------------
       VALIDATION
    -------------------------------------------------------- */

    if (!name) {

        if (status) {

            status.textContent =
                "Please enter the subscriber name.";

        }

        return;

    }


    if (
        smsEnabled &&
        !phone
    ) {

        if (status) {

            status.textContent =
                "Please enter a mobile number for SMS alerts.";

        }

        return;

    }


    if (
        !Number.isFinite(
            radius
        ) ||
        radius <= 0
    ) {

        if (status) {

            status.textContent =
                "Please select a valid alert radius.";

        }

        return;

    }


    if (status) {

        status.textContent =
            "Registering emergency alert recipient...";

    }


    try {

        const response =
            await fetch(
                `${ALERT_API}/alerts/subscribe`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            name,

                            phone:
                                phone ||
                                null,

                            latitude:
                                coordinates.latitude,

                            longitude:
                                coordinates.longitude,

                            radius_km:
                                radius,

                            sms_enabled:
                                smsEnabled,

                            push_enabled:
                                pushEnabled

                        })

                }
            );


        if (!response.ok) {

            const text =
                await response.text();


            throw new Error(
                `HTTP ${response.status}: ${text}`
            );

        }


        const data =
            await response.json();


        /*
         * Backend should return subscriber_id.
         */

        if (
            data.subscriber_id ===
            undefined ||
            data.subscriber_id ===
            null
        ) {

            throw new Error(
                "Backend did not return subscriber_id."
            );

        }


        registeredSubscriberId =
            String(
                data.subscriber_id
            );


        localStorage.setItem(
            ALERT_SUBSCRIBER_STORAGE_KEY,
            registeredSubscriberId
        );


        /* ----------------------------------------------------
           UI
        ---------------------------------------------------- */

        if (status) {

            status.textContent =
                `✓ Registered successfully. ` +
                `Alerts within ${radius} km ` +
                `will be processed automatically.`;

        }


        if (smsEnabled) {

            alertSetText(
                "sms-status",
                "Configured"
            );

        }
        else {

            alertSetText(
                "sms-status",
                "Disabled"
            );

        }


        if (pushEnabled) {

            alertSetText(
                "push-status",
                "Ready"
            );

        }
        else {

            alertSetText(
                "push-status",
                "Disabled"
            );

        }


        /*
         * Push subscription is done only after
         * successful subscriber registration.
         */

        if (pushEnabled) {

            const enabled =
                await enableAlertPushNotifications();


            if (!enabled) {

                if (status) {

                    status.textContent +=
                        " Push permission/subscription still needs setup.";

                }

            }

        }

    }
    catch (error) {

        console.error(
            "Alert subscriber registration:",
            error
        );


        if (status) {

            status.textContent =
                `Registration failed: ${error.message}`;

        }

    }

}


/* ============================================================
   ENABLE PUSH NOTIFICATIONS
   ============================================================ */

async function enableAlertPushNotifications() {

    const status =
        alertElement(
            "alert-registration-status"
        );


    if (
        !("Notification" in window)
    ) {

        alertSetText(
            "push-status",
            "Unsupported"
        );

        return false;

    }


    try {

        const permission =
            await Notification.requestPermission();


        if (
            permission !==
            "granted"
        ) {

            alertSetText(
                "push-status",
                "Permission denied"
            );

            return false;

        }


        if (
            !("serviceWorker" in navigator)
        ) {

            alertSetText(
                "push-status",
                "Service worker unsupported"
            );

            return false;

        }


        const registration =
            await navigator.serviceWorker.register(
                "/service-worker.js"
            );


        await navigator.serviceWorker.ready;


        /*
         * VAPID public key should be defined in index.html:
         *
         * window.VAPID_PUBLIC_KEY = "...";
         */

        const vapidPublicKey =
            window.VAPID_PUBLIC_KEY ||
            "";


        if (
            !vapidPublicKey
        ) {

            console.warn(
                "VAPID public key is not configured."
            );


            alertSetText(
                "push-status",
                "VAPID key required"
            );


            if (status) {

                status.textContent =
                    "Browser permission granted, but VAPID public key is not configured.";

            }


            return false;

        }


        const applicationServerKey =
            urlBase64ToUint8Array(
                vapidPublicKey
            );


        let subscription =
            await registration
                .pushManager
                .getSubscription();


        if (!subscription) {

            subscription =
                await registration
                    .pushManager
                    .subscribe({

                        userVisibleOnly:
                            true,

                        applicationServerKey

                    });

        }


        if (
            !registeredSubscriberId
        ) {

            /*
             * Push cannot be linked to a subscriber
             * until registration is completed.
             */

            alertSetText(
                "push-status",
                "Register subscriber first"
            );

            return false;

        }


        const json =
            subscription.toJSON();


        if (
            !json.endpoint ||
            !json.keys ||
            !json.keys.p256dh ||
            !json.keys.auth
        ) {

            throw new Error(
                "Browser returned an invalid push subscription."
            );

        }


        /*
         * IMPORTANT:
         *
         * This is the single push-subscription format
         * used by the alert center.
         */

        const response =
            await fetch(
                `${ALERT_API}/alerts/push-subscription`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            subscriber_id:
                                Number(
                                    registeredSubscriberId
                                ),

                            endpoint:
                                json.endpoint,

                            p256dh:
                                json.keys.p256dh,

                            auth:
                                json.keys.auth

                        })

                }
            );


        if (!response.ok) {

            const text =
                await response.text();


            throw new Error(
                `Push backend HTTP ${response.status}: ${text}`
            );

        }


        alertSetText(
            "push-status",
            "Enabled"
        );


        if (status) {

            status.textContent =
                "✓ Browser push notifications enabled.";

        }


        return true;

    }
    catch (error) {

        console.error(
            "Push notification setup:",
            error
        );


        alertSetText(
            "push-status",
            "Setup failed"
        );


        if (status) {

            status.textContent =
                `Push setup failed: ${error.message}`;

        }


        return false;

    }

}


/* ============================================================
   BASE64 → UINT8 ARRAY
   ============================================================ */

function urlBase64ToUint8Array(
    base64String
) {

    const padding =
        "=".repeat(
            (
                4 -
                base64String.length % 4
            ) % 4
        );


    const base64 =
        (
            base64String +
            padding
        )
        .replace(
            /-/g,
            "+"
        )
        .replace(
            /_/g,
            "/"
        );


    const rawData =
        window.atob(
            base64
        );


    return Uint8Array.from(
        [...rawData].map(
            char =>
                char.charCodeAt(0)
        )
    );

}


/* ============================================================
   TEST CRITICAL ALERT
   ============================================================ */

async function testCriticalAlert() {

    const coordinates =
        getAlertSelectedCoordinates();


    const button =
        alertElement(
            "test-critical-alert"
        );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "Sending...";

    }


    try {

        const response =
            await fetch(
                `${ALERT_API}/alerts/dispatch`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            alert_type:
                                "LOCATION",

                            level:
                                "CRITICAL",

                            title:
                                "Critical Landslide Warning",

                            message:
                                "SIH demonstration alert. " +
                                "Critical landslide risk has been " +
                                "detected at the selected location.",

                            latitude:
                                coordinates.latitude,

                            longitude:
                                coordinates.longitude,

                            probability:
                                0.91

                        })

                }
            );


        if (!response.ok) {

            const text =
                await response.text();


            throw new Error(
                `HTTP ${response.status}: ${text}`
            );

        }


        const data =
            await response.json();


        console.log(
            "CRITICAL ALERT RESULT:",
            data
        );


        /*
         * Update statistics.
         */

        alertSetText(
            "last-alert-time",
            new Date().toLocaleTimeString(
                "en-IN"
            )
        );


        const smsCount =
            Array.isArray(
                data.sms
            )
                ? data.sms.length
                : Number(
                    data.sms_deliveries ||
                    0
                );


        const pushCount =
            Array.isArray(
                data.push
            )
                ? data.push.length
                : Number(
                    data.push_deliveries ||
                    0
                );


        alertSetText(
            "sms-delivery-count",
            smsCount
        );


        alertSetText(
            "push-delivery-count",
            pushCount
        );


        /*
         * Show useful test result.
         */

        const status =
            alertElement(
                "alert-registration-status"
            );


        if (status) {

            status.textContent =
                `✓ Test alert dispatched. ` +
                `SMS: ${smsCount}, Push: ${pushCount}.`;

        }

    }
    catch (error) {

        console.error(
            "Critical alert test:",
            error
        );


        alert(
            `Alert test failed:\n${error.message}`
        );

    }
    finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "🚨 Test Critical Alert";

        }

    }

}


/* ============================================================
   WARNING COUNT
   ============================================================ */

function updateCenterWarningCount() {

    const source =
        alertElement(
            "active-warning-count"
        );


    const target =
        alertElement(
            "center-warning-count"
        );


    if (
        source &&
        target
    ) {

        target.textContent =
            source.textContent;

    }

}


/* ============================================================
   EXPOSE LOCATION UPDATE
   ============================================================ */

window.updateAlertCenterLocation =
    updateAlertCenterLocation;


/* ============================================================
   INITIALIZATION
   ============================================================ */

function initializeAlertCenter() {

    updateNetworkState();

    updateAlertCenterLocation();


    const registerButton =
        alertElement(
            "register-alert-subscriber"
        );


    if (registerButton) {

        registerButton.addEventListener(
            "click",
            registerAlertSubscriber
        );

    }


    const pushButton =
        alertElement(
            "enable-push-alerts"
        );


    if (pushButton) {

        pushButton.addEventListener(
            "click",
            enableAlertPushNotifications
        );

    }


    const testButton =
        alertElement(
            "test-critical-alert"
        );


    if (testButton) {

        testButton.addEventListener(
            "click",
            testCriticalAlert
        );

    }


    window.addEventListener(
        "online",
        updateNetworkState
    );


    window.addEventListener(
        "offline",
        updateNetworkState
    );


    /*
     * DO NOT attach map "moveend" here.
     *
     * Map panning must NOT change the alert location.
     */

    setInterval(
        updateCenterWarningCount,
        1000
    );

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
        initializeAlertCenter
    );

}
else {

    initializeAlertCenter();

}