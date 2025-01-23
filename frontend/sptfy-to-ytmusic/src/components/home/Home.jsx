import React, {useState} from "react";
import { Container, Row, Col, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExchangeAlt, faLock, faRocket } from "@fortawesome/free-solid-svg-icons";
import { faSpotify, faYoutube } from "@fortawesome/free-brands-svg-icons";
import { useAuthenticator } from '@aws-amplify/ui-react';
import {useNavigate} from "react-router-dom";
import Lottie from 'lottie-react';
import AuthDialog from "@/components/auth/AuthDialog.jsx";
import animationData from '@/lotties/player.json';
import "./Home.css";


function Home() {
    const [showAuthDialog, setShowAuthDialog] = useState(false);
    const navigate = useNavigate();
    const { user, authStatus } = useAuthenticator((context) => [
        context.user,
        context.authStatus
    ]);

    const handleGetStartedClick = () => {
        if (authStatus === 'authenticated') {
            navigate('/transfer');
        } else {
            setShowAuthDialog(true);
        }
    };

    const closeAuthDialog = () => {
        setShowAuthDialog(false);
    };

    return (
        <div className="home">
            {/* Hero Section */}
            <section className="hero">
                <Container className="hero-container">
                    <Row className="align-items-center h-100">
                        <Col md={6} className="d-flex flex-column align-items-center justify-content-center text-center">
                            <h1 className="hero-title">Welcome to PlayShift</h1>
                            <p className="hero-description">
                                Seamlessly transfer your music playlists between Spotify, YouTube Music, and more.
                            </p>
                            <Button className="hero-button mt-4" variant="primary" onClick={handleGetStartedClick}>
                                Get Started
                            </Button>
                        </Col>
                        <Col md={6} className="d-flex justify-content-center align-items-end" onClick={handleGetStartedClick}>
                            <Lottie
                                animationData={animationData}
                                loop={true}
                                style={{ maxWidth: "80%", height: "auto", padding: "2rem"}}
                            />
                        </Col>
                    </Row>
                </Container>
            </section>

            {/* Features Section */}
            <section id="features" className="features">
                <Container>
                    <h2 className="section-title">Why Choose PlayShift?</h2>
                    <Row>
                        <Col md={4} className="text-center">
                            <FontAwesomeIcon icon={faExchangeAlt} size="3x" className="feature-icon" />
                            <h3 className="feature-title">Easy Transfers</h3>
                            <p>Move your playlists across platforms with just a few clicks.</p>
                        </Col>
                        <Col md={4} className="text-center">
                            <FontAwesomeIcon icon={faLock} size="3x" className="feature-icon" />
                            <h3 className="feature-title">Secure & Private</h3>
                            <p>Your data is encrypted and never shared.</p>
                        </Col>
                        <Col md={4} className="text-center">
                            <FontAwesomeIcon icon={faRocket} size="3x" className="feature-icon" />
                            <h3 className="feature-title">Fast & Reliable</h3>
                            <p>Enjoy quick transfers and a smooth experience.</p>
                        </Col>
                    </Row>
                </Container>
            </section>

            {/* Supported Platforms Section */}
            <section className="platforms">
                <Container>
                    <h2 className="section-title">Supported Platforms</h2>
                    <Row className="justify-content-center">
                        <Col xs={6} sm={4} md={3} lg={2} className="text-center">
                            <FontAwesomeIcon icon={faSpotify} size="4x" className="platform-icon" />
                            <p>Spotify</p>
                        </Col>
                        <Col xs={6} sm={4} md={3} lg={2} className="text-center">
                            <FontAwesomeIcon icon={faYoutube} size="4x" className="platform-icon" />
                            <p>YouTube Music</p>
                        </Col>
                    </Row>
                </Container>
            </section>



            {/* Footer */}
            <footer className="footer">
                <Container>
                    <p>&copy; {new Date().getFullYear()} PlayShift. All rights reserved.</p>
                </Container>
            </footer>

            {showAuthDialog && <AuthDialog isOpen={showAuthDialog} onClose={closeAuthDialog} />}

        </div>
    );
}

export default Home;
