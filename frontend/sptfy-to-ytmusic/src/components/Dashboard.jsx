/**
 * Dashboard Component
 * Main dashboard interface for the playlist transfer application.
 * Handles user authentication, service connections, and playlist management.
 */
import React, {useCallback, useEffect, useState} from 'react';
import {fetchUserAttributes, getCurrentUser, signOut} from 'aws-amplify/auth';
import {useNavigate} from 'react-router-dom';
import {loginSpotify, fetchPlaylists, isLoggedIntoSpotify} from '../utils/spotifyApi';

const Dashboard = () => {
    // Navigation hook
    const navigate = useNavigate();

    // State management
    const [user, setUser] = useState(null);                    // Current authenticated user
    const [userAttributes, setUserAttributes] = useState(null); // User profile attributes
    const [loading, setLoading] = useState(true);              // Loading state
    const [spotifyConnected, setSpotifyConnected] = useState(false);  // Spotify connection status
    const [youtubeConnected, setYoutubeConnected] = useState(false); // YouTube connection status
    const [playlists, setPlaylists] = useState([]);           // User's playlists
    const [error, setError] = useState(null);                 // Error state

    /**
     * Checks user authentication status and fetches user attributes
     * Redirects to login if not authenticated
     */
    const checkAuth = useCallback(async () => {
        try {
            const [currentUser, attributes] = await Promise.all([
                getCurrentUser(),
                fetchUserAttributes()
            ]);
            setUser(currentUser);
            setUserAttributes(attributes);
            setLoading(false);
        } catch (error) {
            console.error('Not authenticated', error);
            navigate('/login');
        }
    }, [navigate]);

    /**
     * Fetches user's playlists from Spotify
     * Updates playlists state and handles loading/error states
     */
    const fetchPlaylistsData = useCallback(async () => {
        try {
            setLoading(true);
            const playlistsData = await fetchPlaylists();
            setPlaylists(playlistsData.playlists);
        } catch (error) {
            setError('Error fetching playlists');
            console.error('Error fetching playlists:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    // Check authentication on component mount
    useEffect(() => {
        checkAuth();
    }, []);

    // Fetch playlists when Spotify is connected
    useEffect(() => {
        if (spotifyConnected) {
            fetchPlaylistsData();
        }
    }, [spotifyConnected, fetchPlaylistsData]);

    /**
     * Handles user sign out
     * Clears authentication and redirects to login
     */
    const handleSignOut = async () => {
        try {
            await signOut();
            navigate('/login');
        } catch (error) {
            setError('Error signing out');
            console.error('Error signing out:', error);
        }
    };

    /**
     * Initiates Spotify OAuth flow
     * Redirects user to Spotify login page if not already connected
     */
    const handleSpotifyAuth = async () => {
        try {
            console.log('Checking Spotify connection...');
            const response =  await isLoggedIntoSpotify();
            console.log('Spotify connection response:', response)

            if (response.isLoggedIn) {
                console.log('Already connected to Spotify');
                setSpotifyConnected(true);
                await fetchPlaylistsData();
                return;
            }

            const authUrl = await loginSpotify();
            if (authUrl) {
                window.location.href = authUrl;
            } else {
                throw new Error('Failed to get Spotify login URL');
            }
        } catch (error) {
            setError('Spotify authentication failed');
            console.error('Spotify authentication error:', error);
        }
    };

    /**
     * Initiates YouTube Music OAuth flow
     * TODO: Implement actual YouTube Music authentication
     */
    const handleYouTubeAuth = async () => {
        try {
            // Implement YouTube Music OAuth flow
            console.log('Connecting to YouTube Music...');
            // After successful connection:
            setYoutubeConnected(true);
        } catch (error) {
            console.error('YouTube Music authentication error:', error);
        }
    };

    // Loading state render
    if (loading) {
        return <div className="loading-container">Loading...</div>;
    }

    // Error state render
    if (error) {
        return <div className="error-container">{error}</div>;
    }

    // Main dashboard render
    return (
        <div className="dashboard-container">
            {/* Navigation bar */}
            <nav className="dashboard-nav">
                <div className="nav-content">
                    <div className="nav-left">
                        <h1>Welcome to Your Dashboard</h1>
                        <h2>Hello, {userAttributes?.name}!</h2>
                    </div>
                    <button onClick={handleSignOut} className="signout-button">
                        Sign Out
                    </button>
                </div>
            </nav>

            {/* Service connection buttons */}
            <div className="service-buttons">
                <button
                    onClick={handleSpotifyAuth}
                    className={`service-button spotify-button ${spotifyConnected ? 'connected' : ''}`}
                    disabled={spotifyConnected}
                >
                    {spotifyConnected ? 'Connected to Spotify' : 'Connect Spotify'}
                </button>

                <button
                    onClick={handleYouTubeAuth}
                    className={`service-button youtube-button ${youtubeConnected ? 'connected' : ''}`}
                    disabled={youtubeConnected}
                >
                    {youtubeConnected ? 'Connected to YouTube Music' : 'Connect YouTube Music'}
                </button>
            </div>

            {/* Main content area */}
            <main className="dashboard-content">
                {/* Transfer section - shown when both services are connected */}
                {spotifyConnected && youtubeConnected && (
                    <div className="transfer-section">
                        <h3>Ready to Transfer</h3>
                        <p>Both services are connected. You can now transfer your playlists.</p>
                        {/* Add transfer functionality here */}
                    </div>
                )}

                {/* Playlists section - shown when playlists are available */}
                {playlists.length > 0 && (
                    <div className="playlists-section">
                        <h3>Your Playlists</h3>
                        <ul>
                            {playlists.map((playlist) => (
                                <li key={playlist.id}>{playlist.name}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </main>
        </div>
    );
};

export default Dashboard;