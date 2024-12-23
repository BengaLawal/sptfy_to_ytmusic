import React, { useState } from 'react';
import { signUp, signIn } from 'aws-amplify/auth';
import { Link, useNavigate } from 'react-router-dom';

const Signup = ({ onSignupSuccess }) => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
        // Clear error when user starts typing
        setError('');
    };

    const handleSignup = async (event) => {
        event.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            if (!formData.name || !formData.email || !formData.password || !formData.confirmPassword) {
                throw new Error('All fields are required');
            }

            if (formData.password !== formData.confirmPassword) {
                throw new Error('Passwords do not match');
            }

            // AWS Cognito password validation
            const hasUpperCase = /[A-Z]/.test(formData.password);
            const hasLowerCase = /[a-z]/.test(formData.password);
            const hasNumbers = /\d/.test(formData.password);
            const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(formData.password);

            if (!(hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar)) {
                throw new Error(
                    'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character'
                );
            }

            // Sign up the user
            const signUpResponse = await signUp({
                username: formData.email.toLowerCase().trim(),
                password: formData.password,
                options:  {
                    userAttributes: {
                        email: formData.email.toLowerCase().trim(),
                        name: formData.name.trim(),
                    },
                    autoSignIn: {
                        enabled: true
                    }
                },
            });
            console.log('Sign up successful:', signUpResponse);

            if (signUpResponse.nextStep.signInStep === 'CONFIRM_SIGN_UP') {
                navigate('/login');
            } else {
                navigate('/confirm-signup', {
                    state: {
                        email: formData.email.toLowerCase().trim(),
                        password: formData.password // Pass password for auto-login after confirmation
                    }
                });
            }
            return signUpResponse;
        } catch (error) {
            console.error('Signup error:', error);
            setError(error.message);
            throw error;
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <h2>Sign Up</h2>
            <form onSubmit={handleSignup} className="auth-form">
                <div className="form-group">
                    <label htmlFor="name">Name</label>
                    <input
                        id="name"
                        name="name"
                        type="text"
                        value={formData.name}
                        onChange={handleChange}
                        required
                        autoComplete="name"
                        disabled={isLoading}
                    />
                </div>
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
                        disabled={isLoading}
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
                        autoComplete="new-password"
                        disabled={isLoading}
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password</label>
                    <input
                        id="confirmPassword"
                        name="confirmPassword"
                        type="password"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        required
                        autoComplete="new-password"
                        disabled={isLoading}
                    />
                </div>
                <button type="submit" className="submit-button" disabled={isLoading}
                >{isLoading ? 'Signing up...' : 'Sign Up'}</button>
            </form>
            {error && <p className="error-message">{error}</p>}
            <p className="auth-link">
                Already have an account? <Link to="/login">Log in</Link>
            </p>
        </div>
    );
};

export default Signup;
