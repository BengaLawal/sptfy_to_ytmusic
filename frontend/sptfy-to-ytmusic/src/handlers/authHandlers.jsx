import { signOut } from 'aws-amplify/auth';
import { fetchUserAttributes, getCurrentUser } from 'aws-amplify/auth';

/**
 * Checks if user is authenticated and retrieves user data
 * @param {function} navigate - Navigation function from router
 * @returns {Object} Object containing user and attributes
 * @throws {Error} If authentication fails
 */
export const checkUserAuth = async (navigate) => {
    try {
        const [currentUser, attributes] = await Promise.all([
            getCurrentUser(),
            fetchUserAttributes()
        ]);
        return { user: currentUser, attributes };
    } catch (error) {
        console.error('Not authenticated', error);
        navigate('/login');
        throw error;
    }
};

/**
 * Signs out the current user
 * @param {function} navigate - Navigation function from router
 * @throws {Error} If sign out fails
 */
export const handleUserSignOut = async (navigate) => {
    try {
        await signOut();
        navigate('/login');
    } catch (error) {
        console.error('Error signing out:', error);
        throw new Error('Error signing out');
    }
};