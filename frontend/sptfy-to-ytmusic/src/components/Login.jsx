import React, { useState } from 'react';
import { signIn } from 'aws-amplify/auth';

const Login = () => {
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

            // New signIn syntax with named parameters
            const { isSignedIn, nextStep } = await signIn({
                username: formData.email,
                password: formData.password
            });

            if (isSignedIn) {
                console.log('Login successful');
                // Handle successful login here
            } else if (nextStep) {
                // Handle additional authentication steps if needed
                console.log('Additional steps required:', nextStep);
            }
        } catch (error) {
            setError(error.message);
        }
    };

    return (
        <div>
            <h2>Login</h2>
            <form onSubmit={handleLogin}>
                <label htmlFor="email">Email</label>
                <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    autoComplete="email"
                />
                <label htmlFor="password">Password</label>
                <input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    autoComplete="current-password"
                />
                <button type="submit">Login</button>
            </form>
            {error && <p>{error}</p>}
        </div>
    );
};

export default Login;
