/* ============================================================
   OFFICIAL INTERFACE SESSION & AUTH GUARD
   ============================================================ */
"use strict";

const AUTH_STORAGE_KEY = "ner_official_auth_token";

// Check authentication on startup
function checkAuth() {
    const token = sessionStorage.getItem(AUTH_STORAGE_KEY);
    const modal = document.getElementById("auth-modal");
    const consoleWrapper = document.getElementById("console-wrapper");

    if (token) {
        if (modal) modal.classList.add("hidden");
        if (consoleWrapper) consoleWrapper.classList.remove("hidden");
        
        // Let Leaflet know the container resized
        setTimeout(() => {
            if (window.map) window.map.invalidateSize();
        }, 200);
    } else {
        if (modal) modal.classList.remove("hidden");
        if (consoleWrapper) consoleWrapper.classList.add("hidden");
    }
}

// Handle login attempt
async function handleOfficialLogin(event) {
    event.preventDefault();
    const user = document.getElementById("auth-username").value.trim();
    const pass = document.getElementById("auth-password").value.trim();
    const errEl = document.getElementById("auth-error-msg");

    // Default demonstration credential check(For development purposes only):
    if ((user === "admin" || user === "officer@ner.gov.in") && pass === "Admin@123") {
        const mockJwt = "token_authorized_" + btoa(user + ":" + Date.now());
        sessionStorage.setItem(AUTH_STORAGE_KEY, mockJwt);
        if (errEl) errEl.classList.add("hidden");
        checkAuth();
    } else {
        if (errEl) {
            errEl.textContent = "Unauthorized: Invalid username or password.";
            errEl.classList.remove("hidden");
        }
    }
}

// Log out and clear tokens
function handleLogout() {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
    window.location.reload();
}

window.addEventListener("DOMContentLoaded", checkAuth);