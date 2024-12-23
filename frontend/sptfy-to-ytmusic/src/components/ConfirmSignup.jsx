import React, { useState } from 'react';
import { confirmSignUp, signIn, resendSignUpCode } from 'aws-amplify/auth';
import { useLocation, useNavigate, Link } from 'react-router-dom';

const ConfirmSignup = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isResending, setIsResending] = useState(false);

    const email = location.state?.email;
    const password = location.state?.password;

    const handleConfirm = async (event) => {
        event.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            if (!email) {
                throw new Error('Email is required. Please go back to signup.');
            }

            const confirmResponse = await confirmSignUp({
                username: email,
                confirmationCode: code
            });

            console.log('Confirmation successful:', confirmResponse);

            // After successful confirmation, attempt to sign in
            if (password) {
                try {
                    const signInResponse = await signIn({
                        username: email,
                        password: password
                    });

                    if (signInResponse.isSignedIn) {
                        navigate('/dashboard');
                        return;
                    }
                } catch (signInError) {
                    console.error('Auto sign-in failed:', signInError);
                }
            }

            // If auto-login fails or no password available, redirect to login
            navigate('/login');
        } catch (error) {
            console.error('Confirmation error:', error);
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleResendCode = async () => {
        setIsResending(true);
        setError('');

        try {
            await resendSignUpCode({
                username: email
            });
            alert('New verification code sent successfully!');
        } catch (error) {
            console.error('Resend code error:', error);
            setError(error.message);
        } finally {
            setIsResending(false);
        }
    };

    const handleCodeChange = (event) => {
        setCode(event.target.value);
        setError(''); // Clear error when user types
    };

    return (
        <div className="auth-container">
            <h2>Verify Your Email</h2>
            <p className="verification-message">
                Please enter the verification code sent to:
                <br />
                <strong>{email}</strong>
            </p>

            <form onSubmit={handleConfirm} className="auth-form">
                <div className="form-group">
                    <label htmlFor="code">Verification Code</label>
                    <input
                        id="code"
                        type="text"
                        value={code}
                        onChange={handleCodeChange}
                        placeholder="Enter verification code"
                        required
                        disabled={isLoading}
                        autoComplete="off"
                        className="verification-input"
                    />
                </div>

                <button
                    type="submit"
                    className="submit-button"
                    disabled={isLoading || !code}
                >
                    {isLoading ? 'Verifying...' : 'Verify Email'}
                </button>

                <button
                    type="button"
                    onClick={handleResendCode}
                    className="resend-button"
                    disabled={isResending}
                >
                    {isResending ? 'Sending...' : 'Resend Code'}
                </button>
            </form>

            {error && (
                <p className="error-message">
                    {error}
                </p>
            )}

            <div className="auth-links">
                <Link to="/signup" className="auth-link">
                    Return to Signup
                </Link>
                <span className="separator">|</span>
                <Link to="/login" className="auth-link">
                    Go to Login
                </Link>
            </div>
        </div>
    );
};

export default ConfirmSignup;
