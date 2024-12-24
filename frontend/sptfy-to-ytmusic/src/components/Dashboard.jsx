// Dashboard.jsx
import React, {useCallback, useEffect, useState} from 'react';
import {fetchUserAttributes, getCurrentUser, signOut} from 'aws-amplify/auth';
import {useNavigate} from 'react-router-dom';
import {loginSpotify, fetchPlaylists} from '../utils/spotifyApi';

const Dashboard = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [userAttributes, setUserAttributes] = useState(null);
    const [loading, setLoading] = useState(true);
    const [spotifyConnected, setSpotifyConnected] = useState(false);
    const [youtubeConnected, setYoutubeConnected] = useState(false);
    const [playlists, setPlaylists] = useState([]);
    const [error, setError] = useState(null);

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

    const fetchPlaylistsData = useCallback(async () => {
        try {
            setLoading(true);
            const playlistsData = await fetchPlaylists();
            setPlaylists(playlistsData);
        } catch (error) {
            setError('Error fetching playlists');
            console.error('Error fetching playlists:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, []);

    useEffect(() => {
        if (spotifyConnected) {
            fetchPlaylistsData();
        }
    }, [spotifyConnected, fetchPlaylistsData]);


    const handleSignOut = async () => {
        try {
            await signOut();
            navigate('/login');
        } catch (error) {
            setError('Error signing out');
            console.error('Error signing out:', error);
        }
    };

    const handleSpotifyAuth = async () => {
        try {
            console.log('Connecting to Spotify...');
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

    if (loading) {
        return <div className="loading-container">Loading...</div>;
    }

    if (error) {
        return <div className="error-container">{error}</div>;
    }

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

            <main className="dashboard-content">
                {spotifyConnected && youtubeConnected && (
                    <div className="transfer-section">
                        <h3>Ready to Transfer</h3>
                        <p>Both services are connected. You can now transfer your playlists.</p>
                        {/* Add transfer functionality here */}
                    </div>
                )}

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
