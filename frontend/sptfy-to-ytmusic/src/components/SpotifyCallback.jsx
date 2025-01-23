/**
 * SpotifyCallback Component
 *
 * Handles the OAuth callback from Spotify after user authorization.
 * Processes the authorization code or error from URL parameters and
 * manages the connection state with Spotify.
 *
 * @component
 * @returns {JSX.Element} Rendered component showing loading or error state
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { handleSpotifyCallback } from '../api/spotifyApi.jsx';

const SpotifyCallback = () => {
    // Navigation hook for redirecting after callback processing
    const navigate = useNavigate();
    const location = useLocation();
    // State for managing error and loading status
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    const navigateToTransfer = useCallback((state) => {
        navigate('/transfer', {
            state: {
                ...state,
                timestamp: Date.now()
            },
            replace: true
        });
    }, [navigate]);

    const processCallback = useCallback(async (code) => {
        try {
            await handleSpotifyCallback(code);
            return { spotifyConnected: true };
        } catch (error) {
            throw new Error(`Failed to process Spotify callback: ${error.message}`);
        }
    }, []);

    useEffect(() => {
        /**
         * Processes the Spotify OAuth callback
         * - Extracts code/error from URL
         * - Handles the authorization with backend
         * - Navigates to dashboard with appropriate state
         */
        let mounted = true;

        const handleCallback = async () => {
            try {
                // Extract parameters from the OAuth callback URL
                const params = new URLSearchParams(window.location.search);
                const code = params.get('code');
                const error = params.get('error');

                console.log('Callback parameters:', { code, error });

                // Handle potential authorization errors
                if (error) {
                    throw new Error(`Spotify authorization failed: ${error}`);
                }

                if (!code) {
                    throw new Error('No authorization code received');
                }

                const result = await processCallback(code);

                if (mounted) {
                    navigateToTransfer(result);
                }

            } catch (error) {
                // Handle any errors during the callback process
                console.error('Spotify callback error:', error);

                if (mounted) {
                    setError(error.message);
                    // Automatically redirect to dashboard after error
                    setTimeout(() => {
                        if (mounted) {
                            navigateToTransfer({
                                spotifyError: error.message
                            });
                        }
                    }, 3000);
                }
            } finally {
                if (mounted) {
                    setIsLoading(false);
                }
            }
        };

        handleCallback();

        // Cleanup function
        return () => {
            mounted = false;
        };
    }, [navigateToTransfer, processCallback]);

    // Show error state if connection failed
    if (error) {
        return (
            <div className="callback-error" role="alert">
                <h2>Connection Error</h2>
                <p>{error}</p>
                <p>Redirecting to dashboard...</p>
            </div>
        );
    }

    // Show loading state while processing callback
    return (
        <div className="callback-loading" role="status">
            <h2>Connecting to Spotify...</h2>
            {isLoading && (
                <div className="loading-spinner" aria-label="Loading">
                    <div className="spinner"></div>
                </div>
            )}
        </div>
    );
};

export default React.memo(SpotifyCallback);