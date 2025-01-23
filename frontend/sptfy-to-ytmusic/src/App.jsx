import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Nav from "@/components/nav/Nav.jsx";
import Home from "@/components/home/Home.jsx";
import Dashboard from "@/components/dashboard/Dashboard.jsx";
import { Amplify } from 'aws-amplify';
import { Authenticator } from "@aws-amplify/ui-react";
import '@aws-amplify/ui-react/styles.css';
import './App.css';

// Configure Amplify with the AWS configuration
Amplify.configure({
    Auth: {
        Cognito: {
            userPoolId: import.meta.env.VITE_USER_POOL_ID,
            userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
            identityPoolId: import.meta.env.VITE_IDENTITY_POOL_ID,
            region: import.meta.env.VITE_AWS_REGION,
        }
    }
});

function App() {
    return (
        <Authenticator.Provider>
            <Router>
                <Nav />
                <div className="main-content">
                    <Routes>
                        <Route path="/" element={<Home />}/>
                        <Route path="/dashboard" element={<Dashboard />}/>
                    </Routes>
                </div>
            </Router>
        </Authenticator.Provider>
    );
}

export default App
