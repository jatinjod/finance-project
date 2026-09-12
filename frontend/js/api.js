// frontend/js/api.js
// Central API communication layer with error handling

const API_BASE =
    (window.location.hostname === 'localhost' ||
     window.location.hostname === '127.0.0.1')
        ? 'https://finance-project-zf24.onrender.com'
        : `http://${window.location.hostname}:5000`;

// ─────────────────────────────────────────────
// TOKEN MANAGEMENT
// ─────────────────────────────────────────────

function getToken() {
    return localStorage.getItem('access_token');
}

function storeAuthData(token, user) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user', JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
}

// ─────────────────────────────────────────────
// CORE API REQUEST
// ─────────────────────────────────────────────

async function apiRequest(endpoint, method = 'GET', data = null) {

    const headers = {
        'Content-Type': 'application/json'
    };

    const token = getToken();

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {

        const response = await fetch(
            `${API_BASE}${endpoint}`,
            options
        );

        // Read response body first
        const text = await response.text();

        let result = {};

        if (text) {
            try {
                result = JSON.parse(text);
            } catch (error) {
                console.error(
                    'Response is not valid JSON:',
                    text
                );

                return {
                    error: 'Server returned an invalid response.',
                    status_code: response.status
                };
            }
        }

        // ─────────────────────────────────────────
        // AUTH ERROR HANDLING
        // ─────────────────────────────────────────

        if (response.status === 401) {

            /*
             * IMPORTANT:
             * Do NOT redirect automatically on the login request.
             *
             * Otherwise:
             * "Invalid email or password"
             * gets hidden by redirecting back to login.
             */

            if (endpoint !== '/api/auth/login') {

                clearAuthData();

                window.location.href = 'login.html';

                return null;
            }

            // Login request failed
            return {
                ...result,
                error: result.error || 'Invalid email or password.',
                status_code: 401
            };
        }

        // ─────────────────────────────────────────
        // OTHER HTTP ERRORS
        // ─────────────────────────────────────────

        if (!response.ok) {

            return {
                ...result,
                error:
                    result.error ||
                    result.message ||
                    `Request failed with status ${response.status}.`,
                status_code: response.status
            };
        }

        // ─────────────────────────────────────────
        // SUCCESS
        // ─────────────────────────────────────────

        return result;

    } catch (networkError) {

        console.error(
            'Network error:',
            networkError
        );

        return {
            error:
                'Cannot connect to server. ' +
                'Make sure the backend is running on https://finance-project-t8zo.onrender.com',
            status_code: 0
        };
    }
}

// ─────────────────────────────────────────────
// HTTP SHORTCUTS
// ─────────────────────────────────────────────

const API = {

    get: (endpoint) =>
        apiRequest(endpoint, 'GET'),

    post: (endpoint, data) =>
        apiRequest(endpoint, 'POST', data),

    put: (endpoint, data) =>
        apiRequest(endpoint, 'PUT', data),

    delete: (endpoint) =>
        apiRequest(endpoint, 'DELETE')
};

// ─────────────────────────────────────────────
// CONNECTION TEST
// ─────────────────────────────────────────────

async function testConnection() {

    try {

        const response = await fetch(
            `${API_BASE}/api/health`
        );

        return response.ok;

    } catch {

        return false;
    }
}