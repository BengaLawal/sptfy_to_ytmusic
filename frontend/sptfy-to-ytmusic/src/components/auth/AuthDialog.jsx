import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { signIn, signUp, confirmSignUp, resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { useAuthenticator } from '@aws-amplify/ui-react';
import './AuthDialog.css';

const AuthDialog = ({ isOpen, onClose }) => {
    const navigate = useNavigate();
    const { signIn: authenticatorSignIn } = useAuthenticator();

    // Move all state to the top
    const [formState, setFormState] = useState({
        isSignIn: true,
        showPassword: false,
        email: '',
        password: '',
        verificationCode: '',
        showVerification: false,
        resetPassword: false,
        newPassword: '',
        error: ''
    });

    // Define all callbacks at the top level
    const clearError = useCallback(() => {
        setFormState(prev => ({ ...prev, error: '' }));
    }, []);

    const handleBackdropClick = useCallback((e) => {
        if (e.target.className === 'auth-dialog-overlay') {
            onClose();
        }
    }, [onClose]);

    const handleInputChange = useCallback((field) => (e) => {
        setFormState(prev => ({ ...prev, [field]: e.target.value }));
    }, []);

    const handleSignIn = useCallback(async (e) => {
        e.preventDefault();
        clearError();
        try {
            const { isSignedIn } = await signIn({
                username: formState.email,
                password: formState.password,
            });

            if (isSignedIn) {
                onClose();
                navigate('/dashboard');
            }
        } catch (error) {
            setFormState(prev => ({ ...prev, error: error.message }));
        }
    }, [formState.email, formState.password, navigate, onClose, clearError]);

    const handleSignUp = useCallback(async (e) => {
        e.preventDefault();
        clearError();
        try {
            const { isSignUpComplete } = await signUp({
                username: formState.email,
                password: formState.password,
                options: {
                    userAttributes: {
                        email: formState.email,
                    },
                    autoSignIn: true
                }
            });

            if (!isSignUpComplete) {
                setFormState(prev => ({ ...prev, showVerification: true }));
            }
        } catch (error) {
            setFormState(prev => ({ ...prev, error: error.message }));
        }
    }, [formState.email, formState.password, clearError]);

    const handleVerification = useCallback(async (e) => {
        e.preventDefault();
        clearError();
        try {
            await confirmSignUp({
                username: formState.email,
                confirmationCode: formState.verificationCode
            });

            const { isSignedIn } = await signIn({
                username: formState.email,
                password: formState.password,
            });

            if (isSignedIn) {
                setFormState(prev => ({ ...prev, showVerification: false }));
                onClose();
                navigate('/dashboard');
            }
        } catch (error) {
            setFormState(prev => ({ ...prev, error: error.message }));
        }
    }, [formState.email, formState.password, formState.verificationCode, navigate, onClose, clearError]);

    const handleForgotPassword = useCallback(async (e) => {
        e.preventDefault();
        clearError();
        try {
            await resetPassword({ username: formState.email });
            setFormState(prev => ({ ...prev, resetPassword: true }));
        } catch (error) {
            setFormState(prev => ({ ...prev, error: error.message }));
        }
    }, [formState.email, clearError]);

    const handleResetPassword = useCallback(async (e) => {
        e.preventDefault();
        clearError();
        try {
            await confirmResetPassword({
                username: formState.email,
                confirmationCode: formState.verificationCode,
                newPassword: formState.newPassword
            });
            setFormState(prev => ({
                ...prev,
                resetPassword: false,
                isSignIn: true
            }));
        } catch (error) {
            setFormState(prev => ({ ...prev, error: error.message }));
        }
    }, [formState.email, formState.verificationCode, formState.newPassword, clearError]);

    // Memoize all form renders
    const verificationForm = useMemo(() => (
        <form className="auth-form" onSubmit={handleVerification}>
            <div className="form-group">
                <label>Verification Code</label>
                <input
                    type="text"
                    className="auth-input"
                    value={formState.verificationCode}
                    onChange={handleInputChange('verificationCode')}
                    required
                />
            </div>
            <button type="submit" className="submit-button">
                Verify Account
            </button>
        </form>
    ), [formState.verificationCode, handleVerification, handleInputChange]);

    const resetPasswordForm = useMemo(() => (
        <form className="auth-form" onSubmit={handleResetPassword}>
            <div className="form-group">
                <label>Verification Code</label>
                <input
                    type="text"
                    className="auth-input"
                    value={formState.verificationCode}
                    onChange={handleInputChange('verificationCode')}
                    required
                />
            </div>
            <div className="form-group">
                <label>New Password</label>
                <div className="password-input-wrapper">
                    <input
                        type={formState.showPassword ? "text" : "password"}
                        className="auth-input"
                        value={formState.newPassword}
                        onChange={handleInputChange('newPassword')}
                        required
                    />
                    <button
                        className="toggle-password"
                        onClick={() => setFormState(prev => ({ ...prev, showPassword: !prev.showPassword }))}
                        type="button"
                    >
                        {formState.showPassword ? "🐵" : "🙈️"}
                    </button>
                </div>
            </div>
            <button type="submit" className="submit-button">
                Reset Password
            </button>
        </form>
    ), [formState.showPassword, formState.verificationCode, formState.newPassword, handleResetPassword, handleInputChange]);

    const mainForm = useMemo(() => (
        <>
            <div className="auth-tabs">
                <button
                    className={`tab-button ${formState.isSignIn ? 'active' : ''}`}
                    onClick={() => setFormState(prev => ({ ...prev, isSignIn: true }))}
                >
                    Sign In
                </button>
                <button
                    className={`tab-button ${!formState.isSignIn ? 'active' : ''}`}
                    onClick={() => setFormState(prev => ({ ...prev, isSignIn: false }))}
                >
                    Create Account
                </button>
            </div>
            <form className="auth-form" onSubmit={formState.isSignIn ? handleSignIn : handleSignUp}>
                <div className="form-group">
                    <label>Email</label>
                    <input
                        type="email"
                        className="auth-input"
                        value={formState.email}
                        onChange={handleInputChange('email')}
                        required
                    />
                </div>
                <div className="form-group">
                    <label>Password</label>
                    <div className="password-input-wrapper">
                        <input
                            type={formState.showPassword ? "text" : "password"}
                            className="auth-input"
                            value={formState.password}
                            onChange={handleInputChange('password')}
                            required
                        />
                        <button
                            className="toggle-password"
                            onClick={() => setFormState(prev => ({ ...prev, showPassword: !prev.showPassword }))}
                            type="button"
                        >
                            {formState.showPassword ? "🐵" : "🙈️"}
                        </button>
                    </div>
                </div>
                <button type="submit" className="submit-button">
                    {formState.isSignIn ? 'Sign in' : 'Create Account'}
                </button>
                {formState.isSignIn && (
                    <button
                        className="forgot-password"
                        onClick={handleForgotPassword}
                        type="button"
                    >
                        Forgot your password?
                    </button>
                )}
            </form>
        </>
    ), [
        formState.isSignIn,
        formState.showPassword,
        formState.email,
        formState.password,
        handleSignIn,
        handleSignUp,
        handleForgotPassword,
        handleInputChange
    ]);

    if (!isOpen) return null;

    return (
        <div className="auth-dialog-overlay" onClick={handleBackdropClick}>
            <div className="auth-dialog-content">
                <button
                    className="close-button"
                    onClick={onClose}
                    aria-label="Close"
                >
                    ×
                </button>
                <h1>Welcome to Self Storage</h1>
                {formState.error && (
                    <div
                        role="alert"
                        className="error-message"
                        style={{ color: 'red', marginBottom: '1rem', textAlign: 'center' }}
                    >
                        {formState.error}
                    </div>
                )}
                {formState.showVerification ? verificationForm :
                    formState.resetPassword ? resetPasswordForm :
                        mainForm}
            </div>
        </div>
    );
};

export default React.memo(AuthDialog);