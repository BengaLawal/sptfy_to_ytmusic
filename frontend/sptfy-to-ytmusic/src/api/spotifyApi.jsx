/**
 * Spotify API integration utilities
 * This module provides functions for Spotify authentication and data fetching
 */
import {getUserAndAuth, makeAuthenticatedRequest} from './sharedApi.jsx';

/**
 * Checks if user is logged into Spotify
 * * @returns {Promise<{statusCode: number, body: {message: string, isLoggedIn: boolean}}>} Response containing status code, message and login status
 * * @throws {Error} If login status cannot be retrieved
 */
export const isLoggedIntoSpotify = async () => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest(`/spotify/isLoggedIn/${user.userId}`);
};


/**
 * Initiates Spotify login flow
 * @returns {Promise<string>} Spotify authorization URL
 * @throws {Error} If login URL cannot be retrieved
 */
export const loginSpotify = async () => {
    const [user] = await getUserAndAuth();
    const data = await makeAuthenticatedRequest(`/spotify/login/${user.userId}`);
    return data.url;
};

/**
 * Handles the Spotify OAuth callback
 * @param {string} code - Authorization code from Spotify
 * @returns {Promise<Object>} Response from callback endpoint
 * @throws {Error} If callback handling fails
 */
export const handleSpotifyCallback = async (code) => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest('/spotify/callback', {
        method: 'POST',
        body: JSON.stringify({ code, userId: user.userId }),
    });
};

/**
 * Fetches user's Spotify playlists
 * @returns {Promise<Object>} Playlists data
 * @throws {Error} If playlists cannot be retrieved
 */
export const fetchPlaylists = async () => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest(`/spotify/playlists/${user.userId}`);
};

/**
 * Initiates the transfer of a playlist to YouTube Music
 * @param {string} selectedPlaylists - The Spotify playlist ID to transfer
 * @returns {Promise<Response>} The API response
 */
export const initiateSpotifyTransferToYtmusic = async (selectedPlaylists ) => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest(`/transfer/sptfy-to-ytmusic`, {
        method: 'POST',
        body: JSON.stringify({ playlistIds: selectedPlaylists, userId: user.userId  })
    })
};

export const checkTransferStatus = async (transferId) => {
    const [user] = await getUserAndAuth();
    return makeAuthenticatedRequest(`/transfer/status`, {
        method: 'POST',
        body: JSON.stringify({
            transfer_id: transferId,
            user_id: user.userId
        })
    });
};