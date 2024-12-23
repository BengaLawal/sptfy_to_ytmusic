import React, { useState } from 'react';
import { signIn } from 'aws-amplify/auth';
import { Link, useNavigate } from 'react-router-dom';
import Signup from "./Signup.jsx";

const Login = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });
    const [error, setError] = useState('');

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    const handleLogin = async (event) => {
        event.preventDefault();
        setError('');

        try {
            if (!formData.email || !formData.password) {
                throw new Error('Email and password are required');
            }

            const signInResponse = await signIn({
                username: formData.email.toLowerCase().trim(),
                password: formData.password
            });
            console.log('Login successful:', signInResponse);

            // Check if additional verification is needed
            if (signInResponse.isSignedIn) {
                navigate('/dashboard');
            } else if (signInResponse.nextStep) {
                // Handle additional authentication steps if needed
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
            {error && <p className="error-message">{error}</p>}
            <p className="auth-link">
                Don't have an account? <Link to="/signup">Sign up</Link>
            </p>
        </div>
    );
};

export default Login;
