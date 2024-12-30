/**
 * Login Component
 *
 * A React component that handles user authentication using AWS Amplify.
 * Provides a login form with email and password fields and handles various
 * authentication scenarios including signup confirmation and password reset.
 */
import React, { useState } from 'react';
import { signIn } from 'aws-amplify/auth';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/login.css';

const Login = () => {
    const navigate = useNavigate();
    // State for form data and error handling
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });
    const [error, setError] = useState('');

    /**
     * Handles input field changes and updates form state
     * @param {Event} event - The input change event
     */
    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    /**
     * Handles the login form submission
     * Attempts to sign in the user using AWS Amplify auth
     * Handles various authentication scenarios and redirects accordingly
     * @param {Event} event - The form submission event
     * @returns {Promise} SignIn response from AWS Amplify
     */
    const handleLogin = async (event) => {
        event.preventDefault();
        setError('');

        try {
            // Validate required fields
            if (!formData.email || !formData.password) {
                throw new Error('Email and password are required');
            }

            // Attempt sign in
            const signInResponse = await signIn({
                username: formData.email.toLowerCase().trim(),
                password: formData.password
            });
            console.log('Login successful:', signInResponse);

            // Handle different authentication scenarios
            if (signInResponse.isSignedIn) {
                navigate('/dashboard');
            } else if (signInResponse.nextStep) {
                // Handle additional authentication steps
                switch (signInResponse.nextStep.signInStep) {
                    case 'CONFIRM_SIGN_UP':
                        navigate('/confirm-signup', {
                            state: { email: formData.email }
                        });
                        break;
                    case 'RESET_PASSWORD':
                        navigate('/reset-password', {
                            state: { email: formData.email }
                        });
                        break;
                    default:
                        console.log('Additional step required:', signInResponse.nextStep);
                }
            }

            return signInResponse;
        } catch (error) {
            setError(error.message);
        }
    };

    // Render login form with email and password inputs
    return (
        <div className="auth-container">
            <h2>Log In</h2>
            <form onSubmit={handleLogin} className="auth-form">
                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        autoComplete="email"
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        name="password"
                        type="password"
                        value={formData.password}
                        onChange={handleChange}
                        required
                        autoComplete="current-password"
                    />
                </div>
                <button type="submit" className="submit-button">Log In</button>
            </form>
            {/* Display error message if authentication fails */}
            {error && <p className="error-message">{error}</p>}
            <p className="auth-link">
                Don't have an account? <Link to="/signup">Sign up</Link>
            </p>
        </div>
    );
};

export default Login;