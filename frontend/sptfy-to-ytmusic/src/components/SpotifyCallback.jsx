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
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { handleSpotifyCallback } from '../utils/spotifyApi.jsx';

const SpotifyCallback = () => {
    // Navigation hook for redirecting after callback processing
    const navigate = useNavigate();
    const location = useLocation();
    // State for managing error and loading status
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        /**
         * Processes the Spotify OAuth callback
         * - Extracts code/error from URL
         * - Handles the authorization with backend
         * - Navigates to dashboard with appropriate state
         */
        const handleCallback = async () => {
            try {
                // Extract parameters from the OAuth callback URL
                const params = new URLSearchParams(window.location.search);
                const code = params.get('code');
                const error = params.get('error');

                // Handle potential authorization errors
                if (error) {
                    throw new Error(`Spotify authorization failed: ${error}`);
                }

                if (!code) {
                    throw new Error('No authorization code received');
                }

                // Process the authorization code with backend
                await handleSpotifyCallback(code);

                // On successful connection, redirect to dashboard
                navigate('/dashboard', {
                    state: {
                        spotifyConnected: true,
                        timestamp: Date.now() // Ensures state change detection
                    },
                    replace: true // Prevents back navigation to callback
                });

            } catch (error) {
                // Handle any errors during the callback process
                console.error('Spotify callback error:', error);
                setError(error.message);

                // Redirect to dashboard with error state after delay
                setTimeout(() => {
                    navigate('/dashboard', {
                        state: {
                            spotifyError: error.message,
                            timestamp: Date.now()
                        },
                        replace: true
                    });
                }, 3000);
            } finally {
                setIsLoading(false);
            }
        };

        handleCallback();

        // Cleanup state on component unmount
        return () => {
            setIsLoading(false);
            setError(null);
        };
    }, [navigate, location]);

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
                <div className="loading-spinner">
                    {/* Add your spinner component or animation here */}
                    <div className="spinner"></div>
                </div>
            )}
        </div>
    );
};

export default SpotifyCallback;