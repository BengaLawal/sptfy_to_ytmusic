import React, { useState } from 'react';
import PlatformSelection from '../transferFlow/PlatformSelection';
import PlaylistSelection from '../transferFlow/PlaylistSelection';
import TransferConfirmation from '../transferFlow/TransferConfirmation';
import TransferStatus from '../transferFlow/TransferStatus';
import {initiateSpotifyTransferToYtmusic} from "@/api/spotifyApi.jsx";
import './Transfer.css';

const TransferFlow = () => {
    const [currentStep, setCurrentStep] = useState('source-platform');
    const [sourcePlatform, setSourcePlatform] = useState(null);
    const [destPlatform, setDestPlatform] = useState(null);
    const [selectedPlaylists, setSelectedPlaylists] = useState([]);
    const [selectionContext, setSelectionContext] = useState('source');
    const [transferId, setTransferId] = useState(null);
    const [showTransferStatus, setShowTransferStatus] = useState(false);

    const resetTransfer = () => {
        setCurrentStep('source-platform');
        setSourcePlatform(null);
        setDestPlatform(null);
        setSelectedPlaylists([]);
        setSelectionContext('source');
        setTransferId(null);
        setShowTransferStatus(false);
    };

    const handleSourcePlatformSelect = (platform) => {
        setSourcePlatform(platform);
        setSelectionContext('source');
        setCurrentStep('source-playlists');
    };

    const handlePlaylistsSelect = (playlists) => {
        setSelectedPlaylists(playlists);
        setSelectionContext('destination');
        setCurrentStep('dest-platform');
    };

    const handleDestPlatformSelect = (platform) => {
        setDestPlatform(platform);
        setCurrentStep('transfer-confirm');
    };

    const handleStartTransfer = async () => {
        if (sourcePlatform.name === 'Spotify') {
            const selectedPlaylistIds = selectedPlaylists.map(playlist => playlist.id);
            const response = await initiateSpotifyTransferToYtmusic(selectedPlaylistIds)
            if (response.transfer_id) {
                setTransferId(response.transfer_id);
                setShowTransferStatus(true);
            }
        }
    };

    const goBack = () => {
        switch(currentStep) {
            case 'source-playlists':
                setCurrentStep('source-platform');
                break;
            case 'dest-platform':
                setCurrentStep('source-playlists');
                break;
            case 'transfer-confirm':
                setCurrentStep('dest-platform');
                break;
            default:
                break;
        }
    };

    return (
        <div>
            <div className="transfer-container">
                {currentStep === 'source-platform' && (
                    <PlatformSelection
                        title="Select Source Platform"
                        onPlatformSelect={handleSourcePlatformSelect}
                        selectionContext="source"
                        onPlaylistsFetched={setSelectedPlaylists}
                        step={1}
                        totalSteps={4}
                    />
                )}

                {currentStep === 'source-playlists' && (
                    <PlaylistSelection
                        playlists={selectedPlaylists}
                        onPlaylistsSelected={handlePlaylistsSelect}
                        onBack={goBack}
                        step={2}
                        totalSteps={4}
                    />
                )}

                {currentStep === 'dest-platform' && (
                    <PlatformSelection
                        title="Select Destination Platform"
                        onPlatformSelect={handleDestPlatformSelect}
                        selectionContext="destination"
                        onBack={goBack}
                        disabledPlatform={sourcePlatform.id}
                        step={3}
                        totalSteps={4}
                    />
                )}

                {currentStep === 'transfer-confirm' && (
                    <TransferConfirmation
                        sourcePlatform={sourcePlatform}
                        destPlatform={destPlatform}
                        selectedPlaylists={selectedPlaylists}
                        onStartTransfer={handleStartTransfer}
                        onBack={goBack}
                        onResetTransfer={resetTransfer}
                        step={4}
                        totalSteps={4}
                    />
                )}
            </div>
            {showTransferStatus && transferId && (
                <div className="transfer-status-wrapper">
                    <TransferStatus transferId={transferId} />
                </div>
            )}
        </div>
    );
};

export default TransferFlow;