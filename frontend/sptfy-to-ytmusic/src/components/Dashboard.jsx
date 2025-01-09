/**
 * Dashboard Component
 * Main dashboard interface for the playlist transfer application.
 * Handles user authentication, service connections, and playlist management.
 */
import React, {useCallback, useEffect, useState} from 'react';
import {fetchUserAttributes, getCurrentUser, signOut} from 'aws-amplify/auth';
import {useNavigate} from 'react-router-dom';
import {loginSpotify, fetchPlaylists, isLoggedIntoSpotify} from '../utils/spotifyApi';
import {loginYtmusic, pollInterval} from '../utils/ytmusicApi.jsx';
import '../styles/dashboard.css';

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
    const [selectedPlaylists, setSelectedPlaylists] = useState([]); // Hold selected playlists
    const [selectedPlaylistId, setSelectedPlaylistId] = useState(null); // Hold the selected playlist ID
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

    const handlePlaylistSelect = (playlistId) => {
        setSelectedPlaylists((prevSelected) => {
            if (prevSelected.includes(playlistId)) {
                setSelectedPlaylistId(null); // Deselect if already selected
                return prevSelected.filter(id => id !== playlistId); // Deselect if already selected
            } else {
                setSelectedPlaylistId(playlistId); // Select the playlist and show embed
                return [...prevSelected, playlistId]; // Select the playlist
            }
        });
        console.log(selectedPlaylists)
    };

    /**
     * Initiates YouTube Music OAuth flow
     * TODO: Implement actual YouTube Music authentication
     */
    const handleYouTubeAuth = async () => {
        const MAX_RETRIES = 60;
        setLoading(true)
        try {
            // Implement YouTube Music OAuth flow
            console.log('Connecting to YouTube Music...');
            const response = await loginYtmusic();

            console.log('YouTube Music connection response:', response);
            const { verification_url, device_code, interval } = response;

            const newWindow = window.open(verification_url, '_blank');
            if (!newWindow) {
                throw new Error('Popup blocked. Please enable popups and try again.');
            }

            let tokenStatus = await pollInterval(device_code, interval);
            let attempts = 0;

            while (tokenStatus.status !== 'completed' && attempts < MAX_RETRIES) {
                console.log('Polling for token status...');
                await new Promise(resolve => setTimeout(resolve, interval * 1000));
                tokenStatus = await pollInterval(device_code, interval);
                attempts++
            }


            if (tokenStatus.status === 'completed') {
                console.log('Token exchange completed successfully');
                setYoutubeConnected(true);
                window.location.href = '/dashboard';
                // After successful connection:
            }else if (tokenStatus.status === 'error') {
                throw new Error(tokenStatus.message || 'Token exchange failed');
            } else {
                throw new Error('Polling timeout: Token exchange took too long');
            }

        } catch (error) {
            console.error('YouTube Music authentication error:', error);
            setYoutubeConnected(false);
        } finally {
            setLoading(false);
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

            <div className="service-buttons">
                <button onClick={handleSpotifyAuth}
                        className={`service-button spotify-button ${spotifyConnected ? 'connected' : ''}`}
                        disabled={spotifyConnected}>
                    {spotifyConnected ? 'Connected to Spotify' : 'Connect Spotify'}
                </button>

                <button onClick={handleYouTubeAuth}
                        className={`service-button youtube-button ${youtubeConnected ? 'connected' : ''}`}
                        disabled={youtubeConnected}>
                    {youtubeConnected ? 'Connected to YouTube Music' : 'Connect YouTube Music'}
                </button>
            </div>

            <main className="dashboard-content">
                <div className="dashboard-layout">
                    <div className="playlists-section">
                        <h3>Your Spotify Playlists</h3>
                        <div className="playlists-scrollable">
                            <div className="playlists-grid">
                                {playlists.map((playlist) => (
                                    <div
                                        key={playlist.id}
                                        className={`playlist-tile ${selectedPlaylists.includes(playlist.id) ? 'selected' : ''}`}
                                        onClick={() => handlePlaylistSelect(playlist.id)}
                                    >
                                        {playlist.images && playlist.images.length > 0 ? (
                                            <img src={playlist.images[0].url} alt={playlist.name} className="playlist-image" />
                                        ) : (
                                            <div className="placeholder-image">No Image Available</div>
                                        )}
                                        <h4 className="playlist-name">{playlist.name}</h4>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="selected-playlist-section">
                        <h3>Selected Playlist</h3>
                        {selectedPlaylistId && (
                            <div className="spotify-embed-container">
                                <iframe
                                    src={`https://open.spotify.com/embed/playlist/${selectedPlaylistId}?utm_source=generator`}
                                    width="100%"
                                    height="352"
                                    frameBorder="0"
                                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                                    loading="lazy"
                                    style={{ borderRadius: "12px" }}
                                    title="Spotify Playlist"
                                ></iframe>
                                <button onClick={() => setSelectedPlaylistId(null)} className="close-embed-button">
                                    Close
                                </button>
                            </div>
                        )}
                        {!selectedPlaylistId && <div className="no-playlist-selected">No playlist selected</div>}
                    </div>
                </div>


                {/* Transfer Button Section */}
                {spotifyConnected && youtubeConnected && selectedPlaylists.length > 0 && (
                    <div className="transfer-section">
                        <button className="transfer-button">
                            Transfer Playlist
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
};

export default Dashboard;