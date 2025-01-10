import {makeAuthenticatedRequest, getUserAndAuth} from './sharedApi.jsx';


export const isLoggedIntoYtMusic = async () => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest(`/ytmusic/isLoggedIn/${user.userId}`);
};


/**
 * Initiates ytmusic login flow
 * @returns {Promise<string>} Spotify authorization URL
 * @throws {Error} If login URL cannot be retrieved
 */
export const loginYtmusic = async () => {
    const [user] = await getUserAndAuth();
    const data = await makeAuthenticatedRequest(`/ytmusic/login/${user.userId}`);
    return data.data;
};

/**
 * Polls the server to check YouTube Music token status
 * @param {string} device_code - The device code received from YouTube Music auth flow
 * @returns {Promise<Object>} Response from polling endpoint
 * @throws {Error} If polling request fails
 */
export const pollInterval = async (device_code) => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest('/ytmusic/poll-token', {
        method: 'POST',
        body: JSON.stringify({ device_code, userId: user.userId }),
    });
};