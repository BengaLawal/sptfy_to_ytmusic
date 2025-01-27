import React, {useEffect, useState} from 'react';
import {Card, Button, Spinner, Alert} from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpotify, faYoutube } from "@fortawesome/free-brands-svg-icons";
import { handleSpotifyAuthentication, fetchSpotifyPlaylists } from '../../handlers/spotifyAuthHandler.jsx';
import { handleYouTubeMusicAuth } from '../../handlers/youtubeAuthHandler.jsx';
import '../transfer/Transfer.css';

// Define available platforms with their properties
const PLATFORMS = [
    {
        id: 'spotify',
        name: 'Spotify',
        icon: <FontAwesomeIcon icon={faSpotify} className="platform-icon" />,
        availableAs: {
            source: true,
            destination: true
        }
    },
    {
        id: 'ytmusic',
        name: 'YouTube Music',
        icon: <FontAwesomeIcon icon={faYoutube} className="platform-icon" />,
        availableAs: {
            source: false,
            destination: true
        }
    }
];

// PlatformSelection component for selecting music platforms
const PlatformSelection = ({
                               title = 'Select Platform',
                               onPlatformSelect,
                               selectionContext,
                               onPlaylistsFetched,
                               onBack,
                               step,
                               totalSteps,
                               disabledPlatform = null
                           }) => {
    // State for managing loading states and Spotify connection status
    const [loading, setLoading] = useState({});
    const [spotifyConnected, setSpotifyConnected] = useState(false);
    const [youtubeConnected, setYoutubeConnected] = useState(false);
    const [error, setError] = useState({});


    // Handle platform selection and authentication
    const handlePlatformSelect = async (platform) => {
        setError(prev => ({ ...prev, [platform.id]: null }));


        if (platform.id === 'spotify') {
            setLoading(prev => ({ ...prev, spotify: true }));
            try {
                await handleSpotifyAuthentication(setSpotifyConnected);
                if (selectionContext === "source"){
                    try {
                        const playlists = await fetchSpotifyPlaylists();
                        console.log('Fetched playlists:', playlists);
                        onPlaylistsFetched(playlists);
                    } catch (playlistError) {
                        if (playlistError.message.includes('403')) {
                            setError(prev => ({
                                ...prev,
                                spotify: 'You are not registered on the creators Spotify Developer Dashboard. You can contact him to add you at gbengalawal99@gmail.com. Apologies for the inconvenience'
                            }));
                            return; // Prevent proceeding with platform selection
                        }
                        throw playlistError;
                    }
                }
                onPlatformSelect(platform);
            } catch (error) {
                console.error('Spotify platform selection error', error);
                setError(prev => ({
                    ...prev,
                    spotify: 'Failed to connect to Spotify. Please try again.'
                }));
            } finally {
                setLoading(prev => ({ ...prev, spotify: false }));
            }
        } else if (platform.id === 'ytmusic') {
            // Handle YouTube Music platform selection
            setLoading(prev => ({ ...prev, ytmusic: true }));
            try {
                await handleYouTubeMusicAuth(setLoading, setYoutubeConnected);
                if (selectionContext === "source"){
                //     TODO: Add get ytmusic playlist function
                }
                onPlatformSelect(platform);
            } catch (error) {
                console.error('YouTube Music platform selection error', error);
            } finally {
                setLoading(prev => ({ ...prev, ytmusic: false }));
            }
            onPlatformSelect(platform);
        } else {
            // For other platforms, proceed directly
            onPlatformSelect(platform);
        }
    };

    return (
        // Main container for the platform selection interface
        <div className="transfer-container">
            {/* Header section with back button, title and step indicator */}
            <div className="transfer-header">
                {onBack && (
                    <span className="back-button" onClick={onBack}>
            &lt;
          </span>
                )}
                <h2>{title}</h2>
                <div className="step-indicator">STEP {step}/{totalSteps}</div>
            </div>

            {/* Grid of platform cards */}
            <div className="platform-grid">
                {PLATFORMS.filter(platform =>
                    selectionContext === 'source'
                        ? platform.availableAs.source
                        : platform.availableAs.destination
                ).map(platform => (
                    <Card
                        key={platform.id}
                        className={`platform-card ${platform.color} 
              ${disabledPlatform === platform.id ? 'platform-disabled' : ''}`}
                    >
                        <Card.Body
                            className="platform-card-body"
                            onClick={() => {
                                if (disabledPlatform !== platform.id) {
                                    handlePlatformSelect(platform);
                                }
                            }}
                        >
                            {/* Show loading spinner or platform details */}
                            {loading[platform.id] ? (
                                <Spinner animation="border" variant="light" />
                            ) : (
                                <>
                                    {platform.icon}
                                    <h3 className="platform-name">{platform.name}</h3>
                                    {/* Show connection status for Spotify */}
                                    {platform.id === 'spotify' && spotifyConnected && (
                                        <div className="login-status">Connected</div>
                                    )}
                                    {/* Show connection status for YouTube Music */}
                                    {platform.id === 'ytmusic' && youtubeConnected && (
                                        <div className="login-status">Connected</div>
                                    )}

                                    {error[platform.id] && (
                                        <div className="error-message">
                                            {error[platform.id]}
                                        </div>
                                    )}
                                </>
                            )}
                        </Card.Body>
                    </Card>
                ))}
            </div>
        </div>
    );
};

export default PlatformSelection;