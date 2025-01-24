import React, { useEffect, useState } from 'react';
import {Alert, Card, ProgressBar} from 'react-bootstrap';
import { CheckCircle, XCircle, Timer } from 'lucide-react';
import { checkTransferStatus } from '../../api/spotifyApi.jsx';

const TransferStatus = ({ transferId }) => {
    const [status, setStatus] = useState('pending');
    const [progress, setProgress] = useState(0);
    const [stats, setStats] = useState({
        successful: 0,
        failed: 0,
        total: 0
    });

    useEffect(() => {
        const pollStatus = async () => {
            try {
                const data = await checkTransferStatus(transferId);
                console.log('Transfer status:', data)

                if (!data) {
                    console.error('No data received from checkTransferStatus');
                    setStatus('failed');
                    return;
                }

                setStatus(data.status);

                const totalTracks = data.total_tracks || 0;
                const completedTracks = data.completed_tracks || 0;
                const progressPercentage = totalTracks > 0
                    ? Math.round((completedTracks / totalTracks) * 100)
                    : 0;

                setProgress(progressPercentage);

                setStats({
                    successful: completedTracks,
                    failed: data.failed_tracks || 0,
                    total: totalTracks
                });

                if (!['completed', 'failed'].includes(data.status)) {
                    setTimeout(pollStatus, 3000);
                }
            } catch (error) {
                console.error('Error polling transfer status:', error);
                setStatus('failed');
            }
        };

        pollStatus();
    }, [transferId]);

    const renderStatusIcon = () => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="text-success" />;
            case 'failed':
                return <XCircle className="text-danger" />;
            default:
                return <Timer className="text-primary animate-spin" />;
        }
    };

    return (
        <div className="transfer-status-container">
            <Card className="transfer-status-card">
                <Card.Header className={`transfer-status-header ${status}`}>
                    <div className="status-header-content">
                        {renderStatusIcon()}
                        <span>Transfer Status: {status.charAt(0).toUpperCase() + status.slice(1)}</span>
                    </div>
                </Card.Header>
                <Card.Body>
                    <div className="progress-container">
                        <div className="progress-bar" style={{ width: `${progress}%` }}></div>
                    </div>
                    <div className="transfer-stats">
                        <p>Successfully transferred: {stats.successful}/{stats.total} tracks</p>
                        {stats.failed > 0 && (
                            <p className="failed-tracks">({stats.failed} failed)</p>
                        )}
                    </div>
                </Card.Body>
            </Card>
        </div>
    );
};

export default TransferStatus;