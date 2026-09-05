/* ============================================================
   NER LANDSLIDE EARLY WARNING SYSTEM
   OFFLINE + PUSH SERVICE WORKER
   ============================================================ */

"use strict";


const CACHE_NAME =
    "ner-landslide-v1";


const APP_SHELL = [

    "./",

    "./index.html",

    "./style.css",

    "./app.js",

    "./final_alert_runtime.js"

];


self.addEventListener(
    "install",
    event => {

        event.waitUntil(

            caches
                .open(
                    CACHE_NAME
                )
                .then(
                    cache =>
                        cache.addAll(
                            APP_SHELL
                        )
                )

        );


        self.skipWaiting();

    }
);


self.addEventListener(
    "activate",
    event => {

        event.waitUntil(

            caches.keys()
                .then(
                    keys =>

                        Promise.all(

                            keys
                                .filter(
                                    key =>
                                        key !==
                                        CACHE_NAME
                                )

                                .map(
                                    key =>
                                        caches.delete(
                                            key
                                        )
                                )

                        )

                )

        );


        self.clients.claim();

    }
);


/* ============================================================
   OFFLINE FETCH
   ============================================================ */

self.addEventListener(
    "fetch",
    event => {

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

                        if (
                            response &&
                            response.status ===
                            200 &&
                            response.type !==
                            "opaque"
                        ) {

                            const clone =
                                response.clone();


                            caches
                                .open(
                                    CACHE_NAME
                                )
                                .then(
                                    cache =>
                                        cache.put(
                                            event.request,
                                            clone
                                        )
                                );

                        }


                        return response;

                    }
                )
                .catch(
                    () =>
                        caches
                            .match(
                                event.request
                            )
                )

        );

    }
);


/* ============================================================
   PUSH
   ============================================================ */

self.addEventListener(
    "push",
    event => {

        let payload = {

            title:
                "NER Landslide Warning",

            body:
                "New landslide risk information is available.",

            data:
                {}

        };


        try {

            if (
                event.data
            ) {

                payload =
                    event.data.json();

            }

        }
        catch (_) {

            try {

                payload.body =
                    event.data
                        ?.text()
                        ||
                        payload.body;

            }
            catch (_) {}

        }


        const title =
            payload.title
            ||
            "NER Landslide Warning";


        const options = {

            body:
                payload.body
                ||
                "New landslide warning.",

            icon:
                "/icon-192.png",

            badge:
                "/icon-192.png",

            tag:
                payload.data?.alert_id
                ?
                    `landslide-${payload.data.alert_id}`
                :
                    "ner-landslide-alert",

            requireInteraction:
                payload.data?.level ===
                "CRITICAL",

            data:
                payload.data
                ||
                {}

        };


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

        event.notification.close();


        const data =
            event.notification.data
            ||
            {};


        const latitude =
            Number(
                data.latitude
            );


        const longitude =
            Number(
                data.longitude
            );


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
                    clientList => {

                        for (
                            const client
                            of
                            clientList
                        ) {

                            if (
                                "focus"
                                in
                                client
                            ) {

                                client.focus();


                                if (
                                    Number.isFinite(
                                        latitude
                                    )
                                    &&
                                    Number.isFinite(
                                        longitude
                                    )
                                ) {

                                    client.postMessage({

                                        type:
                                            "CENTER_MAP",

                                        latitude,

                                        longitude

                                    });

                                }


                                return;

                            }

                        }


                        if (
                            clients.openWindow
                        ) {

                            return clients
                                .openWindow(
                                    "/"
                                );

                        }

                    }
                )

        );

    }
);