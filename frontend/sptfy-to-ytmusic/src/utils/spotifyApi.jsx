// src/utils/spotifyApi.js
import {fetchAuthSession, getCurrentUser} from "aws-amplify/auth";

const VITE_API_BASE_URL = "https://1c99dvz6y4.execute-api.eu-west-1.amazonaws.com/Prod"

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

export const loginSpotify = async () => {
    try {
        const response = await fetch(`${VITE_API_BASE_URL}/login-spotify`, {
            method: 'GET',
            headers: {
                'Authorization': await getAuthHeader(),
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.url;
    } catch (error) {
        console.error('Error getting Spotify login URL:', error);
        throw error;
    }
};

export const handleSpotifyCallback = async (code) => {
    try {
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);

        const response = await fetch(`${VITE_API_BASE_URL}/spotify-callback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': authHeader,
            },
            body: JSON.stringify({
                code,
                userId: user.userId
            }),
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.message ||
                `Failed to complete Spotify authentication. Status: ${response.status}`
            );
        }
        console.log('Response:', response)
        return await response.json();
    } catch (error) {
        console.error('Error handling Spotify callback:', error);
        throw error;
    }
};


export const fetchPlaylists = async () => {
    try {
        const response = await fetch(`${VITE_API_BASE_URL}/playlists`, {
            method: 'GET',
            headers: {
                'Authorization': await getAuthHeader(),
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log('Response:', response)
        return await response.json();
    } catch (error) {
        console.error('Error fetching playlists:', error);
        throw error;
    }
};