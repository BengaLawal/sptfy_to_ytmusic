// src/components/Home.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthenticator } from '@aws-amplify/ui-react';
import './Home.css';
import homeImage from '../../assets/home_img.png';
import AuthDialog from '../auth/AuthDialog';

const Home = () => {
    const navigate = useNavigate();
    const { authStatus } = useAuthenticator((context) => [context.authStatus]);
    const [isDialogOpen, setIsDialogOpen] = useState(false); // State to manage the modal

    const handleDashboardClick = () => {
        if (authStatus === 'authenticated') {
            navigate('/dashboard'); // Navigate to dashboard if authenticated
        } else {
            setIsDialogOpen(true);
        }
    };

    const handleCloseDialog = () => {
        setIsDialogOpen(false); // Close the authentication modal
    };

    return (
        <div className="home">
            <h1>Welcome to PlayShift</h1>
            <p>I am now working on showing proper feedback after transferring and a new UI.</p>
            <p>This is how the website looks as of now.</p>
            <img src={homeImage} alt="Current UI" className="home-image" />
            <p>
                Note: You won't be able to see your Spotify playlists if you log in to the website just yet because my Spotify developer account is in dev mode. I can, however, add you manually to my list of users while Spotify processes my extension request.
            </p>
            <p>
                Feel free to contact me at <a href="mailto:gbengalawal99@gmail.com">gbengalawal99@gmail.com</a> for me to add you to the list.
            </p>
            <button className="dashboard-button" onClick={handleDashboardClick}>
                Go to Dashboard
            </button>
            <AuthDialog isOpen={isDialogOpen} onClose={handleCloseDialog} />
        </div>
    );
};

export default Home;