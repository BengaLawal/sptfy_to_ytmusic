/**
 * ConfirmSignup Component
 *
 * This component handles the email verification step after user signup.
 * It allows users to:
 * - Enter and submit a verification code
 * - Resend the verification code if needed
 * - Navigate back to signup or login pages
 */
import React, { useState } from 'react';
import { confirmSignUp, signIn, resendSignUpCode } from 'aws-amplify/auth';
import { useLocation, useNavigate, Link } from 'react-router-dom';

const ConfirmSignup = () => {
    // Navigation and routing hooks
    const navigate = useNavigate();
    const location = useLocation();

    // Component state
    const [code, setCode] = useState(''); // Verification code input
    const [error, setError] = useState(''); // Error message
    const [isLoading, setIsLoading] = useState(false); // Loading state for verification
    const [isResending, setIsResending] = useState(false); // Loading state for resend

    // Get email and password from navigation state
    const email = location.state?.email;
    const password = location.state?.password;

    /**
     * Handles the verification code submission
     * Confirms signup and attempts auto-login if password is available
     */
    const handleConfirm = async (event) => {
        event.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // Validate email presence
            if (!email) {
                throw new Error('Email is required. Please go back to signup.');
            }

            // Confirm signup with code
            const confirmResponse = await confirmSignUp({
                username: email,
                confirmationCode: code
            });

            console.log('Confirmation successful:', confirmResponse);

            // Attempt auto-login if password is available
            if (password) {
                try {
                    const signInResponse = await signIn({
                        username: email,
                        password: password
                    });

                    if (signInResponse.isSignedIn) {
                        navigate('/transfer');
                        return;
                    }
                } catch (signInError) {
                    console.error('Auto sign-in failed:', signInError);
                }
            }

            // Fallback to login page
            navigate('/login');
        } catch (error) {
            console.error('Confirmation error:', error);
            setError(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    /**
     * Handles resending of verification code
     */
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

    /**
     * Handles verification code input changes
     * Clears any existing error messages
     */
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

            {/* Verification form */}
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

                {/* Submit button */}
                <button
                    type="submit"
                    className="submit-button"
                    disabled={isLoading || !code}
                >
                    {isLoading ? 'Verifying...' : 'Verify Email'}
                </button>

                {/* Resend code button */}
                <button
                    type="button"
                    onClick={handleResendCode}
                    className="resend-button"
                    disabled={isResending}
                >
                    {isResending ? 'Sending...' : 'Resend Code'}
                </button>
            </form>

            {/* Error message display */}
            {error && (
                <p className="error-message">
                    {error}
                </p>
            )}

            {/* Navigation links */}
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