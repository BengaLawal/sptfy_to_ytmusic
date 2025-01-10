import { loginSpotify, fetchPlaylists, isLoggedIntoSpotify } from '../api/spotifyApi';

/**
 * Handles Spotify authentication flow
 * @param {Function} setSpotifyConnected - Callback to update Spotify connection state
 * @param {Function} fetchPlaylistsData - Callback to fetch playlists after successful auth
 * @returns {Promise<void>}
 * @throws {Error} If authentication fails
 */
export const handleSpotifyAuthentication = async (setSpotifyConnected, fetchPlaylistsData) => {
    try {
        const response = await isLoggedIntoSpotify();

        if (response.isLoggedIn) {
            setSpotifyConnected(true);
            await fetchPlaylistsData();
            return;
        }

        const authUrl = await loginSpotify();
        if (!authUrl) {
            throw new Error('Failed to get Spotify login URL');
        }

        window.location.href = authUrl;
    } catch (error) {
        console.error('Spotify authentication error:', error);
        throw new Error('Spotify authentication failed');
    }
};

/**
 * Fetches user's Spotify playlists
 * @returns {Promise<Array>} Array of playlist objects
 * @throws {Error} If playlist fetching fails
 */
export const fetchSpotifyPlaylists = async () => {
    try {
        const playlistsData = await fetchPlaylists();
        return playlistsData.playlists;
    } catch (error) {
        console.error('Error fetching playlists:', error);
        throw new Error('Error fetching playlists');
    }
};