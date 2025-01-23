/**
 * Dashboard Component
 * Main dashboard interface for the playlist transfer application.
 * Handles user authentication, service connections, and playlist management.
 *
 * Features:
 * - User authentication and profile management
 * - Spotify and YouTube Music service connections
 * - Playlist browsing and selection
 * - Playlist transfer functionality
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { checkUserAuth, handleUserSignOut } from '../../handlers/authHandlers.jsx';
import { handleYouTubeMusicAuth } from '../../handlers/youtubeAuthHandler.jsx';
import { handleSpotifyAuthentication, fetchSpotifyPlaylists } from '../../handlers/spotifyAuthHandler.jsx';
import {initiateSpotifyTransferToYtmusic, isLoggedIntoSpotify} from '../../api/spotifyApi.jsx';
import {isLoggedIntoYtMusic} from "../../api/ytmusicApi.jsx";
import './Dashboard.css';

/**
 * Dashboard functional component
 * Manages the main application interface and state
 * @returns {JSX.Element} The rendered Dashboard component
 */
const Dashboard = () => {
    // State management
    const navigate = useNavigate();
    const [user, setUser] = useState(null);                                   // Current authenticated user
    const [userAttributes, setUserAttributes] = useState(null);               // User profile attributes
    const [loading, setLoading] = useState(true);                            // Loading state flag
    const [spotifyConnected, setSpotifyConnected] = useState(false);         // Spotify connection status
    const [youtubeConnected, setYoutubeConnected] = useState(false);        // YouTube Music connection status
    const [playlists, setPlaylists] = useState([]);                         // User's Spotify playlists
    const [selectedPlaylists, setSelectedPlaylists] = useState([]);          // Selected playlists for transfer
    const [selectedPlaylistId, setSelectedPlaylistId] = useState(null);      // Currently viewed playlist
    const [error, setError] = useState(null);                               // Error state

    useEffect(() => {
        const initializeDash = async () => {
            try {
                setLoading(true);
                // First check authentication
                await checkAuth();

                // Only after auth is confirmed, check service connections
                const spotifyStatus = await isLoggedIntoSpotify();
                setSpotifyConnected(spotifyStatus.isLoggedIn);

                const youtubeStatus = await isLoggedIntoYtMusic();
                setYoutubeConnected(youtubeStatus.isLoggedIn);

            } catch (error) {
                setError('Initialization failed');
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        }, []);

    /**
     * Checks user authentication status
     * Updates user state and attributes if authenticated
     */
    const checkAuth = useCallback(async () => {
        try {
            const { user, attributes } = await checkUserAuth(navigate);
            setUser(user);
            setUserAttributes(attributes);
            setLoading(false);
        } catch (error) {
            setError('Authentication failed');
        }
    }, [navigate]);

    /**
     * Fetches user's Spotify playlists
     * Updates playlists state with fetched data
     */
    const fetchSpotifyPlaylistsData = useCallback(async () => {
        try {
            setLoading(true);
            const playlistsData = await fetchSpotifyPlaylists();
            console.log('Fetched playlists:', playlistsData);
            setPlaylists(playlistsData);
        } catch (error) {
            setError('Error fetching playlists');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        if (spotifyConnected) {
            fetchSpotifyPlaylistsData();
        }
    }, [spotifyConnected, fetchSpotifyPlaylistsData]);

    /**
     * Handles user sign out
     * Clears authentication and navigates to login
     */
    const handleSignOut = async () => {
        try {
            await handleUserSignOut(navigate);
        } catch (error) {
            setError('Error signing out');
        }
    };

    /**
     * Initiates Spotify authentication
     * Updates connection status on success
     */
    const handleSpotifyAuth = async () => {
        try {
            await handleSpotifyAuthentication(setSpotifyConnected, fetchSpotifyPlaylistsData);
        } catch (error) {
            setError('Spotify authentication failed');
        }
    };

    /**
     * Initiates YouTube Music authentication
     * Updates connection status on success
     */
    const handleYouTubeAuth = async () => {
        try {
            await handleYouTubeMusicAuth(setLoading, setYoutubeConnected);
        } catch (error) {
            setError('YouTube Music authentication failed');
        }
    };

    const handlePlaylistView = (playlistId) => {
        setSelectedPlaylistId(playlistId);
    };


    const handlePlaylistSelect = (playlistId, event) => {
        setSelectedPlaylists(prevSelected => {
            const newSelection = prevSelected.includes(playlistId)
                ? prevSelected.filter(id => id !== playlistId)
                : [...prevSelected, playlistId];

            console.log('Selected playlists:', newSelection);
            return newSelection;
        });
    };

    const handleTransferPlaylists = async () => {
        try {
            setLoading(true);
            const response = await initiateSpotifyTransferToYtmusic(selectedPlaylists)
            console.log(response);

            // const data = await response.json();
            // Optionally, you can show a success message or update the UI
        } catch (error) {
            setError('Error transferring playlists');
            console.error(error);
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
            <div className="service-buttons">
                <button onClick={handleSpotifyAuth}
                        className="dashboard-button"
                        disabled={spotifyConnected}>
                    {spotifyConnected ? 'Connected to Spotify' : 'Connect Spotify'}
                </button>

                <button onClick={handleYouTubeAuth}
                        className="dashboard-button"
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
                                        onClick={() => handlePlaylistView(playlist.id)}
                                    >
                                        <div className="playlist-select"
                                             onClick={(e) => {
                                                 e.stopPropagation() // prevent tile click
                                             }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedPlaylists.includes(playlist.id)}
                                                onChange={(e) => handlePlaylistSelect(playlist.id, e)}
                                            />
                                        </div>
                                        {playlist.images && playlist.images.length > 0 ? (
                                            <img src={playlist.images[0].url} alt={playlist.name}
                                                 className="playlist-image"/>
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
                        <button onClick={handleTransferPlaylists} className="transfer-button">
                            Transfer Playlist
                        </button>
                    </div>
                )}
            </main>
        </div>
    );
};

export default Dashboard;