// apiUtils.js
import { fetchAuthSession, getCurrentUser } from "aws-amplify/auth";

export const BASE_URL = import.meta.env.VITE_API_BASE_URL
// const BASE_URL = 'https://1c99dvz6y4.execute-api.eu-west-1.amazonaws.com/Prod'

/**
 * Gets the authentication header using AWS Amplify session
 * @returns {Promise<string>} Bearer token string
 */
export const getAuthHeader = async () => {
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
 * Gets current user and auth header in parallel
 * @returns {Promise<[Object, string]>} Array containing user object and auth header
 */
export const getUserAndAuth = async () => {
    return Promise.all([getCurrentUser(), getAuthHeader()]);
};

/**
 * Makes an authenticated API request
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Request options
 * @returns {Promise<Object>} Response data
 */
export const makeAuthenticatedRequest = async (endpoint, options = {}) => {
    try {
        const [user, authHeader] = await getUserAndAuth();

        const defaultOptions = {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        };

        const response = await fetch(
            `${BASE_URL}${endpoint}`,
            { ...defaultOptions, ...options }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP error! status: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API request failed: ${error.message}`);
        throw error;
    }
};