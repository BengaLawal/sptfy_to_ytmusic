import {fetchAuthSession, getCurrentUser} from "aws-amplify/auth";

// Base URL for API endpoints
const VITE_API_BASE_URL = "https://1c99dvz6y4.execute-api.eu-west-1.amazonaws.com/Prod"

/**
 * Gets the authentication header using AWS Amplify session
 * @returns {Promise<string>} Bearer token string
 * @throws {Error} If unable to get auth token
 */
const getAuthHeader = async () => {
    try {
        const session = await fetchAuthSession();
        const accessToken = session.tokens.accessToken;
        return `Bearer ${accessToken.toString()}`;
    } catch (error) {
        console.error('Error getting auth token:', error);
        throw error;
    }
};

export const isLoggedIntoYtMusic = async () => {
    try {
        // Get user and auth details in parallel
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);
        const response = await fetch(`${VITE_API_BASE_URL}/ytmusic/isLoggedIn/${user.userId}`, {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await data;
    } catch (error) {
        console.error('Error checking YtMusic login status:', error);
        throw error;
    }
};


/**
 * Initiates ytmusic login flow
 * @returns {Promise<string>} Spotify authorization URL
 * @throws {Error} If login URL cannot be retrieved
 */
export const loginYtmusic = async () => {
    try {
        // Get user and auth details in parallel
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);
        const response = await fetch(`${VITE_API_BASE_URL}/ytmusic/login/${user.userId}`, {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.data;
    } catch (error) {
        console.error('Error getting ytmusic login URL:', error);
        throw error;
    }
};

// Start polling for token status
export const pollInterval = async (device_code, interval) => {
    // Get user and auth details in parallel
    const [user, authHeader] = await Promise.all([
        getCurrentUser(),
        getAuthHeader()
    ]);

    const response = await fetch(`${VITE_API_BASE_URL}/ytmusic/poll-token`, {
        method: 'POST',
        headers: {
            'Authorization': authHeader,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: JSON.stringify({
            device_code: device_code,
            userId: user.userId,
        }),
        credentials: 'include'
    });
    return await response.json()
};