/* ============================================================
   NER LANDSLIDE EARLY WARNING SYSTEM
   OFFLINE + PUSH SERVICE WORKER
   ============================================================ */

"use strict";


/* ============================================================
   CACHE CONFIGURATION
   ============================================================ */

/*
 * IMPORTANT:
 *
 * Increase this version whenever frontend files are changed.
 * This forces the browser to create a fresh cache and remove
 * the previous cached application files.
 */

const CACHE_NAME =
    "ner-landslide-v2";


/*
 * Files required for the offline application shell.
 */

const APP_SHELL = [

    "./",

    "./index.html",

    "./style.css",

    "./app.js",

    "./alert_center.js",

    "./final_alert_runtime.js",

    "./service-worker.js"

];


/* ============================================================
   INSTALL
   ============================================================ */

self.addEventListener(
    "install",
    event => {

        event.waitUntil(

            caches
                .open(
                    CACHE_NAME
                )
                .then(
                    cache => {

                        return cache
                            .addAll(
                                APP_SHELL
                            );

                    }
                )
                .catch(
                    error => {

                        console.error(
                            "Service worker cache installation failed:",
                            error
                        );

                    }
                )

        );


        /*
         * Activate the new service worker immediately.
         */

        self.skipWaiting();

    }
);


/* ============================================================
   ACTIVATE
   ============================================================ */

self.addEventListener(
    "activate",
    event => {

        event.waitUntil(

            caches
                .keys()
                .then(
                    cacheNames => {

                        return Promise.all(

                            cacheNames
                                .filter(
                                    cacheName =>
                                        cacheName !==
                                        CACHE_NAME
                                )
                                .map(
                                    cacheName =>
                                        caches.delete(
                                            cacheName
                                        )
                                )

                        );

                    }
                )
                .then(
                    () =>
                        self.clients.claim()
                )

        );

    }
);


/* ============================================================
   FETCH
   ============================================================ */

/*
 * Strategy:
 *
 * 1. Try the network first.
 * 2. If successful, update the cache.
 * 3. If network fails, return cached version.
 *
 * This allows the dashboard to continue working when
 * internet connectivity temporarily disappears.
 */

self.addEventListener(
    "fetch",
    event => {

        /*
         * Only handle GET requests.
         */

        if (
            event.request.method !==
            "GET"
        ) {

            return;

        }


        event.respondWith(

            fetch(
                event.request
            )
                .then(
                    response => {

                        /*
                         * Cache only valid responses.
                         */

                        if (
                            response &&
                            response.status ===
                            200 &&
                            (
                                response.type ===
                                "basic" ||
                                response.type ===
                                "cors"
                            )
                        ) {

                            const responseClone =
                                response.clone();


                            caches
                                .open(
                                    CACHE_NAME
                                )
                                .then(
                                    cache => {

                                        cache.put(
                                            event.request,
                                            responseClone
                                        );

                                    }
                                )
                                .catch(
                                    error => {

                                        console.warn(
                                            "Unable to update cache:",
                                            error
                                        );

                                    }
                                );

                        }


                        return response;

                    }
                )
                .catch(
                    async () => {

                        /*
                         * Network unavailable.
                         *
                         * Return the cached resource.
                         */

                        const cachedResponse =
                            await caches.match(
                                event.request
                            );


                        if (
                            cachedResponse
                        ) {

                            return cachedResponse;

                        }


                        /*
                         * If nothing is cached, return
                         * a controlled offline response.
                         */

                        return new Response(

                            `
                            <!DOCTYPE html>

                            <html>

                            <head>

                                <meta charset="UTF-8">

                                <title>
                                    NER Landslide System - Offline
                                </title>

                                <meta
                                    name="viewport"
                                    content="width=device-width, initial-scale=1"
                                >

                                <style>

                                    body {
                                        margin: 0;
                                        min-height: 100vh;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        font-family:
                                            Arial,
                                            sans-serif;
                                        background: #f8fafc;
                                        color: #0f172a;
                                    }

                                    .offline-box {
                                        max-width: 460px;
                                        margin: 20px;
                                        padding: 30px;
                                        border-radius: 16px;
                                        background: #ffffff;
                                        border: 1px solid #e2e8f0;
                                        text-align: center;
                                        box-shadow:
                                            0 10px 30px
                                            rgba(
                                                15,
                                                23,
                                                42,
                                                0.08
                                            );
                                    }

                                    h1 {
                                        margin-top: 0;
                                        font-size: 22px;
                                    }

                                    p {
                                        color: #64748b;
                                        line-height: 1.6;
                                    }

                                </style>

                            </head>

                            <body>

                                <div
                                    class="offline-box"
                                >

                                    <h1>
                                        🛰 NER Landslide System
                                    </h1>

                                    <p>
                                        The requested resource
                                        is unavailable because
                                        the device is currently
                                        offline.
                                    </p>

                                    <p>
                                        Please reconnect to the
                                        internet and try again.
                                    </p>

                                </div>

                            </body>

                            </html>
                            `,

                            {
                                status:
                                    503,

                                headers:
                                    {
                                        "Content-Type":
                                            "text/html; charset=UTF-8"
                                    }

                            }

                        );

                    }
                )

        );

    }
);


/* ============================================================
   PUSH NOTIFICATION
   ============================================================ */

self.addEventListener(
    "push",
    event => {

        /*
         * Default notification payload.
         */

        let payload = {

            title:
                "NER Landslide Warning",

            body:
                "New landslide risk information is available.",

            data:
                {}

        };


        /* ----------------------------------------------------
           READ PUSH PAYLOAD
           ---------------------------------------------------- */

        try {

            if (
                event.data
            ) {

                payload =
                    event.data.json();

            }

        }
        catch (jsonError) {

            /*
             * If JSON parsing fails, try plain text.
             */

            try {

                if (
                    event.data
                ) {

                    payload.body =
                        event.data.text();

                }

            }
            catch (textError) {

                console.error(
                    "Unable to read push payload:",
                    textError
                );

            }

        }


        /*
         * Make sure data always exists.
         */

        if (
            !payload.data ||
            typeof payload.data !==
            "object"
        ) {

            payload.data =
                {};

        }


        /* ----------------------------------------------------
           NORMALIZE LEVEL
           ---------------------------------------------------- */

        const level =
            String(
                payload.level ??
                payload.data.level ??
                ""
            ).toUpperCase();


        /* ----------------------------------------------------
           NORMALIZE TITLE
           ---------------------------------------------------- */

        const title =
            payload.title ||
            "NER Landslide Warning";


        /* ----------------------------------------------------
           NORMALIZE BODY
           ---------------------------------------------------- */

        const body =
            payload.body ||
            payload.message ||
            "New landslide warning.";


        /* ----------------------------------------------------
           ALERT ID
           ---------------------------------------------------- */

        const alertId =
            payload.alert_id ??
            payload.data.alert_id ??
            null;


        /* ----------------------------------------------------
           LOCATION
           ---------------------------------------------------- */

        const latitude =
            Number(
                payload.latitude ??
                payload.data.latitude
            );


        const longitude =
            Number(
                payload.longitude ??
                payload.data.longitude
            );


        /*
         * Add location to notification data so that
         * clicking the notification can center the map.
         */

        const notificationData = {

            ...payload.data,

            alert_id:
                alertId,

            level,

            latitude:
                Number.isFinite(latitude)
                    ? latitude
                    : undefined,

            longitude:
                Number.isFinite(longitude)
                    ? longitude
                    : undefined

        };


        /* ----------------------------------------------------
           NOTIFICATION OPTIONS
           ---------------------------------------------------- */

        const options = {

            body,

            /*
             * Use relative paths so the notification works
             * regardless of the application's deployment path.
             */

            icon:
                "./icon-192.png",

            badge:
                "./icon-192.png",

            /*
             * Prevent duplicate notifications when the same
             * alert is sent repeatedly.
             */

            tag:
                alertId
                    ? `landslide-${alertId}`
                    : "ner-landslide-alert",

            /*
             * Critical warnings remain visible until the
             * user interacts with them.
             */

            requireInteraction:
                level === "CRITICAL",

            /*
             * Store complete alert information for the
             * notification click handler.
             */

            data:
                notificationData

        };


        /* ----------------------------------------------------
           SHOW NOTIFICATION
           ---------------------------------------------------- */

        event.waitUntil(

            self.registration
                .showNotification(
                    title,
                    options
                )

        );

    }
);


/* ============================================================
   NOTIFICATION CLICK
   ============================================================ */

self.addEventListener(
    "notificationclick",
    event => {

        /*
         * Close the notification immediately.
         */

        event.notification.close();


        /*
         * Read the notification payload.
         */

        const data =
            event.notification.data ||
            {};


        const latitude =
            Number(
                data.latitude
            );


        const longitude =
            Number(
                data.longitude
            );


        const hasValidLocation =
            Number.isFinite(
                latitude
            ) &&
            Number.isFinite(
                longitude
            );


        /* ----------------------------------------------------
           FIND OPEN DASHBOARD
           ---------------------------------------------------- */

        event.waitUntil(

            clients
                .matchAll(
                    {
                        type:
                            "window",

                        includeUncontrolled:
                            true
                    }
                )
                .then(
                    async clientList => {

                        /*
                         * Prefer an already-open dashboard.
                         */

                        for (
                            const client
                            of
                            clientList
                        ) {

                            if (
                                !client
                            ) {

                                continue;

                            }


                            /*
                             * Focus existing dashboard.
                             */

                            if (
                                "focus"
                                in
                                client
                            ) {

                                await client.focus();

                            }


                            /*
                             * Send selected location to app.js.
                             *
                             * app.js handles:
                             *
                             * CENTER_MAP
                             *
                             * and changes the selected location
                             * only because the user explicitly
                             * clicked the notification.
                             */

                            if (
                                hasValidLocation
                            ) {

                                try {

                                    client.postMessage({

                                        type:
                                            "CENTER_MAP",

                                        latitude,

                                        longitude

                                    });

                                }
                                catch (error) {

                                    console.error(
                                        "Unable to send location to dashboard:",
                                        error
                                    );

                                }

                            }


                            return;

                        }


                        /* ------------------------------------------------
                           NO OPEN DASHBOARD
                           ------------------------------------------------ */

                        if (
                            clients.openWindow
                        ) {

                            /*
                             * If there is no open dashboard,
                             * open the application.
                             *
                             * The application itself can then
                             * initialize normally.
                             */

                            return clients.openWindow(
                                "./"
                            );

                        }

                    }
                )

        );

    }
);


/* ============================================================
   SERVICE WORKER MESSAGE HANDLER
   ============================================================ */

/*
 * Optional control channel for the frontend.
 *
 * This allows app.js or another page script to send commands
 * to the service worker if required in the future.
 */

self.addEventListener(
    "message",
    event => {

        if (
            !event.data
        ) {

            return;

        }


        if (
            event.data.type ===
            "SKIP_WAITING"
        ) {

            self.skipWaiting();

        }

    }
);


/* ============================================================
   DEBUG
   ============================================================ */

console.log(
    "NER Landslide Early Warning System — Service Worker v2 loaded."
);