import './App.css'
import Login from "./components/Login.jsx";

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
        <div>
            <h1>Spotify to YtMusic</h1>
            <Login />
        </div>
    )
}

export default App
