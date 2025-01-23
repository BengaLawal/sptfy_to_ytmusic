import React, { useState } from 'react';
import { Card, Button } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck } from '@fortawesome/free-solid-svg-icons';
import '../transfer/Transfer.css';

const PlaylistSelection = ({
                               playlists,
                               onPlaylistsSelected,
                               onBack,
                               step,
                               totalSteps
                           }) => {
    const [selectedPlaylists, setSelectedPlaylists] = useState([]);

    const togglePlaylist = (playlist) => {
        setSelectedPlaylists(current =>
            current.includes(playlist)
                ? current.filter(p => p.id !== playlist.id)
                : [...current, playlist]
        );
    };

    return (
        <div className="transfer-container">
            <div className="transfer-header">
        <span className="back-button" onClick={onBack}>
          &lt;
        </span>
                <h2>Select Playlists to Move</h2>
                <div className="step-indicator">STEP {step}/{totalSteps}</div>
            </div>

            <div className="playlist-grid">
                {playlists.map(playlist => (
                    <Card
                        key={playlist.id}
                        className={`playlist-card ${
                            selectedPlaylists.includes(playlist) ? 'playlist-selected' : ''
                        }`}
                        onClick={() => togglePlaylist(playlist)}
                    >
                        <Card.Body className="playlist-card-body">
                            {selectedPlaylists.includes(playlist) && (
                                <FontAwesomeIcon icon={faCheck} className="playlist-check" />
                            )}
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
            <div className="playlist-footer">
                <Button
                    variant="primary"
                    disabled={selectedPlaylists.length === 0}
                    onClick={() => onPlaylistsSelected(selectedPlaylists)}
                    className="choose-destination-btn"
                >
                    Choose Destination ({selectedPlaylists.length} selected)
                </Button>
            </div>
        </div>
    );
};

export default PlaylistSelection;