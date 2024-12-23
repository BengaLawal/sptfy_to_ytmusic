// Dashboard.jsx
import React, { useEffect, useState } from 'react';
import { getCurrentUser, signOut, fetchUserAttributes} from 'aws-amplify/auth';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [userAttributes, setUserAttributes] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        try {
            const currentUser = await getCurrentUser();
            const attributes = await fetchUserAttributes();
            setUser(currentUser);
            setUserAttributes(attributes);
            setLoading(false);
        } catch (error) {
            console.error('Not authenticated', error);
            navigate('/login');
        }
    };

    const handleSignOut = async () => {
        try {
            await signOut();
            navigate('/login');
        } catch (error) {
            console.error('Error signing out:', error);
        }
    };

    if (loading) {
        return <div>Loading...</div>;
    }

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <h1>Welcome to Your Dashboard</h1>
                <button onClick={handleSignOut} className="signout-button">
                    Sign Out
                </button>
            </header>
            <main className="dashboard-content">
                <h2>Hello, {userAttributes?.name}!</h2>
                {/* Add your dashboard content here */}
            </main>
        </div>
    );
};

export default Dashboard;
