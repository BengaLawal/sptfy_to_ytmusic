import './App.css'
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Signup from './components/Signup';
import Login from "./components/Login.jsx";
import ConfirmSignup from './components/ConfirmSignup';
import Dashboard from './components/Dashboard.jsx';
import ProtectedRoute from './components/ProtectedRoute';
import SpotifyCallback from './components/SpotifyCallback';

import { Amplify } from 'aws-amplify';

// Configure Amplify with the AWS configuration
Amplify.configure({
    Auth: {
        Cognito: {
            userPoolId: import.meta.env.VITE_USER_POOL_ID,
            userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
            region: import.meta.env.VITE_AWS_REGION,
        }
    }
});

function App() {
    return (
        <Router>
            <div className="app-container">
                <Routes>
                    <Route path="/"
                           element={
                               <ProtectedRoute>
                                   <Dashboard />
                               </ProtectedRoute>
                           }
                    />
                    <Route path="/signup" element={<Signup />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/confirm-signup" element={<ConfirmSignup />} />
                    <Route
                        path="/dashboard"
                        element={
                            <ProtectedRoute>
                                <Dashboard />
                            </ProtectedRoute>
                        }
                    />
                    {/* Redirect root to dashboard if authenticated, otherwise to login */}
                    <Route
                        path="/"
                        element={
                            <ProtectedRoute>
                                <Dashboard />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="/spotify-callback" element={<SpotifyCallback />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App
