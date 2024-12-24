// src/components/SpotifyCallback.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { handleSpotifyCallback } from '../utils/spotifyApi.jsx';

const SpotifyCallback = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const handleCallback = async () => {
            try {
                // Get the authorization code from URL parameters
                const params = new URLSearchParams(window.location.search);
                const code = params.get('code');
                const error = params.get('error');

                if (error) {
                    throw new Error(`Spotify authorization failed: ${error}`);
                }

                if (!code) {
                    throw new Error('No authorization code received');
                }

                // Handle the callback with your backend
                await handleSpotifyCallback(code);

                // Successfully connected - navigate to dashboard
                navigate('/dashboard', {
                    state: {
                        spotifyConnected: true,
                        timestamp: Date.now() // Add timestamp to ensure state change
                    },
                    replace: true // Replace current history entry
                });

            } catch (error) {
                console.error('Spotify callback error:', error);
                setError(error.message);

                // Navigate to dashboard with error state
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

        // Cleanup function
        return () => {
            setIsLoading(false);
            setError(null);
        };
    }, [navigate, location]);

    if (error) {
        return (
            <div className="callback-error" role="alert">
                <h2>Connection Error</h2>
                <p>{error}</p>
                <p>Redirecting to dashboard...</p>
            </div>
        );
    }

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