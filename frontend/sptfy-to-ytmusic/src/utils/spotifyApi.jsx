/**
 * Spotify API integration utilities
 * This module provides functions for Spotify authentication and data fetching
 */

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

/**
 * Checks if user is logged into Spotify
 * * @returns {Promise<{statusCode: number, body: {message: string, isLoggedIn: boolean}}>} Response containing status code, message and login status
 * * @throws {Error} If login status cannot be retrieved
 */
export const isLoggedIntoSpotify = async () => {
    try {
        // Get user and auth details in parallel
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);
        // TODO: look into using JWT tokens that contain the user ID and access on backend
        const response = await fetch(`${VITE_API_BASE_URL}/spotify/isLoggedIn/${user.userId}`, {
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
        console.error('Error checking Spotify login status:', error);
        throw error;
    }
};

/**
 * Initiates Spotify login flow
 * @returns {Promise<string>} Spotify authorization URL
 * @throws {Error} If login URL cannot be retrieved
 */
export const loginSpotify = async () => {
    try {
        // Get user and auth details in parallel
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);
        const response = await fetch(`${VITE_API_BASE_URL}/spotify/login/${user.userId}`, {
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
        return data.url;
    } catch (error) {
        console.error('Error getting Spotify login URL:', error);
        throw error;
    }
};

/**
 * Handles the Spotify OAuth callback
 * @param {string} code - Authorization code from Spotify
 * @returns {Promise<Object>} Response from callback endpoint
 * @throws {Error} If callback handling fails
 */
export const handleSpotifyCallback = async (code) => {
    try {
        // Get user and auth details in parallel
        const [user, authHeader] = await Promise.all([
            getCurrentUser(),
            getAuthHeader()
        ]);

        const response = await fetch(`${VITE_API_BASE_URL}/spotify/callback`, {
                    method: 'POST',
                    headers: {
                        'Authorization': authHeader,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: JSON.stringify({
                        code: code,
                        userId: user.userId,
                    }),
                    credentials: 'include'
                });
                const data = await response.json();
                console.log('Response:', data)
                return await data;
            } catch (error) {
                console.error('Error handling Spotify callback:', error);
                throw error;
            }
};

/**
 * Fetches user's Spotify playlists
 * @returns {Promise<Object>} Playlists data
 * @throws {Error} If playlists cannot be retrieved
 */
export const fetchPlaylists = async () => {
    // Get user and auth details in parallel
    const [user, authHeader] = await Promise.all([
        getCurrentUser(),
        getAuthHeader()
    ]);
    try {
        const response = await fetch(`${VITE_API_BASE_URL}/spotify/playlists/${user.userId}`, {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        // if (!response.ok) {
        //     throw new Error(`HTTP error! status: ${response.status}`);
        // }
        const data = await response.json();
        console.log('Response:', data)
        return await data;
    } catch (error) {
        console.error('Error fetching playlists:', error);
        throw error;
    }
};