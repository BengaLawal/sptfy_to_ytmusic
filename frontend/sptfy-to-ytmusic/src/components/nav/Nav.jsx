import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthenticator } from "@aws-amplify/ui-react";
import { signOut } from "aws-amplify/auth";
import "./Nav.css";
import AuthDialog from "../auth/AuthDialog";

const Nav = () => {
    const navigate = useNavigate();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const { user, authStatus } = useAuthenticator((context) => [
        context.user,
        context.authStatus,
    ]);

    const handleLoginSignupClick = () => {
        setIsDialogOpen(true);
    };

    const handleCloseDialog = () => {
        setIsDialogOpen(false);
    };

    const handleSignOut = async () => {
        try {
            await signOut();
            navigate("/");
        } catch (error) {
            console.error("Error signing out:", error);
        }
    };

    const toggleMenu = () => {
        setMenuOpen(!menuOpen);
    };

    return (
        <nav className="navbar">
            <div className="nav-container">
                <Link to="/" className="nav-logo">
                    PlayShift
                </Link>
                <button
                    className="menu-toggle"
                    aria-label="Toggle navigation"
                    onClick={toggleMenu}
                >
                    &#9776;
                </button>
                <div className={`nav-content ${menuOpen ? "open" : ""}`}>
                    <div className="nav-buttons">
                        {authStatus === "authenticated" ? (
                            <>
                                <span className="user-email">
                                    {user?.attributes?.email}
                                </span>
                                <button
                                    className="sign-out-button"
                                    onClick={handleSignOut}
                                >
                                    Sign Out
                                </button>
                            </>
                        ) : (
                            <button
                                className="login-button"
                                onClick={handleLoginSignupClick}
                            >
                                Login/Signup
                            </button>
                        )}
                    </div>
                </div>
            </div>
            <AuthDialog isOpen={isDialogOpen} onClose={handleCloseDialog} />
        </nav>
    );
};

export default Nav;
