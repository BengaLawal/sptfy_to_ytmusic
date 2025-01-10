import { loginYtmusic, pollInterval, isLoggedIntoYtMusic } from '../api/ytmusicApi';

/**
 * Maximum number of polling attempts before timing out
 */
const MAX_RETRIES = 60;

/**
 * Handles the YouTube Music authentication flow
 * @param {Function} setLoading - Function to set loading state
 * @param {Function} setYoutubeConnected - Function to set YouTube connection state
 * @returns {Promise<boolean>} True if authentication successful, false otherwise
 * @throws {Error} If authentication fails or popup is blocked
 */
export const handleYouTubeMusicAuth = async (setLoading, setYoutubeConnected) => {
    try {
        const response = await isLoggedIntoYtMusic();

        if (response.isLoggedIn) {
            setYoutubeConnected(true);
            return true;
        }

        setLoading(true);
        const authResponse = await loginYtmusic();
        const { verification_url, device_code, interval } = authResponse;

        const newWindow = window.open(verification_url, '_blank');
        if (!newWindow) {
            throw new Error('Popup blocked. Please enable popups and try again.');
        }

        const success = await pollForYouTubeToken(device_code, interval);

        if (success) {
            setYoutubeConnected(true);
            window.location.href = '/dashboard';
            return true;
        }

        return false;
    } catch (error) {
        console.error('YouTube Music authentication error:', error);
        setYoutubeConnected(false);
        throw error;
    } finally {
        setLoading(false);
    }
};

/**
 * Polls for YouTube authentication token status
 * @param {string} device_code - Device code received from initial auth request
 * @param {number} interval - Polling interval in seconds
 * @returns {Promise<boolean>} True if token exchange successful
 * @throws {Error} If token exchange fails or times out
 */
const pollForYouTubeToken = async (device_code, interval) => {
    let attempts = 0;

    while (attempts < MAX_RETRIES) {
        const tokenStatus = await pollInterval(device_code);

        if (tokenStatus.status === 'completed') {
            return true;
        }

        if (tokenStatus.status === 'error') {
            throw new Error(tokenStatus.message || 'Token exchange failed');
        }

        await new Promise(resolve => setTimeout(resolve, interval * 1000));
        attempts++;
    }

    throw new Error('Polling timeout: Token exchange took too long');
};