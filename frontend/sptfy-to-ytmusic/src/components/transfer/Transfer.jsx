import React, { useState } from 'react';
import PlatformSelection from '../transferFlow/PlatformSelection';
import PlaylistSelection from '../transferFlow/PlaylistSelection';
import TransferConfirmation from '../transferFlow/TransferConfirmation';
import {initiateSpotifyTransferToYtmusic} from "@/api/spotifyApi.jsx";
import './Transfer.css';

const TransferFlow = () => {
    const [currentStep, setCurrentStep] = useState('source-platform');
    const [sourcePlatform, setSourcePlatform] = useState(null);
    const [destPlatform, setDestPlatform] = useState(null);
    const [selectedPlaylists, setSelectedPlaylists] = useState([]);
    const [selectionContext, setSelectionContext] = useState('source');

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
        console.log('Starting transfer', {
            source: sourcePlatform,
            destination: destPlatform,
            playlists: selectedPlaylists
        });
        if (sourcePlatform.name === 'Spotify') {
            const selectedPlaylistIds = selectedPlaylists.map(playlist => playlist.id);
            const response = await initiateSpotifyTransferToYtmusic(selectedPlaylistIds)
            console.log(response);
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
                    step={4}
                    totalSteps={4}
                />
            )}
        </div>
    );
};

export default TransferFlow;