import React, { useState } from 'react';
import { Card, Button } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faExchangeAlt, faTimes} from '@fortawesome/free-solid-svg-icons';
import '../transfer/Transfer.css';

const TransferConfirmation = ({
                                  sourcePlatform,
                                  destPlatform,
                                  selectedPlaylists,
                                  onStartTransfer,
                                  onBack,
                                  step,
                                  totalSteps
                              }) => {
    const [isTransferring, setIsTransferring] = useState(false);
    const [selectedPlaylistId, setSelectedPlaylistId] = useState(null);


    const startTransfer = async () => {
        setIsTransferring(true);
        try {
            await onStartTransfer();
        } catch (error) {
            console.error('Transfer failed', error);
        } finally {
            setIsTransferring(false);
        }
    };

    const handlePlaylistClick = (playlist) => {
        if (sourcePlatform.name === 'Spotify') {
            setSelectedPlaylistId(playlist.id);
        }
    };

    return (
        <>
            <div className="transfer-container">
                <div className="transfer-header">
                    <span className="back-button" onClick={onBack}>
                        &lt;
                    </span>
                    <h2>Confirm Transfer</h2>
                    <div className="step-indicator">STEP {step}/{totalSteps}</div>
                </div>

                <div className="transfer-details">
                    <Card className="transfer-platforms mb-3">
                        <Card.Body className="transfer-platforms-body">
                            {sourcePlatform.icon}
                            <FontAwesomeIcon icon={faExchangeAlt} className="transfer-icon" />
                            {destPlatform.icon}
                        </Card.Body>
                    </Card>

                    <Card className="transfer-info mb-3">
                        <Card.Body>
                            <h3 className="transfer-details-title">Transfer Details</h3>
                            <p>Source: {sourcePlatform.name}</p>
                            <p>Destination: {destPlatform.name}</p>
                        </Card.Body>
                    </Card>

                    <div className="selected-playlists-section">
                        <h3>Selected Playlists</h3>
                        <div className="playlist-grid">
                            {selectedPlaylists.map(playlist => (
                                <Card
                                    key={playlist.id}
                                    className="playlist-card"
                                    onClick={() => handlePlaylistClick(playlist)}
                                    style={{
                                        cursor: sourcePlatform.name === 'Spotify' ? 'pointer' : 'default',
                                        border: playlist.id === selectedPlaylistId ? '2px solid #28a745' : 'none'
                                    }}
                                >
                                    <Card.Body className="playlist-card-body">
                                        {playlist.images && playlist.images.length > 0 && (
                                            <img
                                                src={playlist.images[0].url}
                                                alt={playlist.name}
                                                className="playlist-image"
                                            />
                                        )}
                                        <div>
                                            <h3 className="playlist-name">{playlist.name}</h3>
                                            <p className="playlist-tracks">{playlist.tracks.total} tracks</p>
                                        </div>
                                    </Card.Body>
                                </Card>
                            ))}
                        </div>
                    </div>

                    <Button
                        variant="primary"
                        className="start-transfer-btn"
                        disabled={isTransferring}
                        onClick={startTransfer}
                    >
                        {isTransferring ? 'Transferring...' : 'Start Transfer'}
                    </Button>
                </div>
            </div>

            {sourcePlatform.name === 'Spotify' && selectedPlaylistId && (
                <div className="selected-playlist-section">
                    <div className="spotify-embed-container">
                        <div className="embed-header">
                            <h3>Selected Playlist Preview</h3>
                            <button
                                onClick={() => setSelectedPlaylistId(null)}
                                className="close-embed-button"
                            >
                                <FontAwesomeIcon icon={faTimes} /> Close
                            </button>
                        </div>
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
                    </div>
                </div>
            )}
        </>
    );
};

export default TransferConfirmation;