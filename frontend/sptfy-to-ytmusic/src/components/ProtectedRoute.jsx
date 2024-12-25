/**
 * ProtectedRoute Component
 *
 * A wrapper component that protects routes by checking authentication status.
 * Redirects unauthenticated users to the login page while preserving the
 * intended destination path.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components to render when authenticated
 * @returns {React.ReactNode} Protected route content or redirect
 */
import { useEffect, useState } from 'react';
import { getCurrentUser } from 'aws-amplify/auth';
import { Navigate, useLocation } from 'react-router-dom';

const ProtectedRoute = ({ children }) => {
    // Track authentication and loading states
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const location = useLocation();

    // Check auth state on component mount
    useEffect(() => {
        checkAuthState();
    }, []);

    /**
     * Verifies if user is currently authenticated using Amplify Auth
     * Updates authentication and loading states accordingly
     */
    const checkAuthState = async () => {
        try {
            await getCurrentUser();
            setIsAuthenticated(true);
        } catch (error) {
            setIsAuthenticated(false);
        } finally {
            setIsLoading(false);
        }
    };

    // Show loading state while checking authentication
    if (isLoading) {
        return <div>Loading...</div>;
    }

    // Redirect to login if not authenticated, preserving intended destination
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location.pathname }} replace />;
    }

    // Render protected content if authenticated
    return children;
};

export default ProtectedRoute;