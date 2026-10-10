import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import WorkspaceBoundary from './components/layout/WorkspaceBoundary.jsx';
import './index.css';
import './styles/dashboard.css';
import './styles/workbench.css';
import './styles/motion.css';

ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><WorkspaceBoundary><App /></WorkspaceBoundary></React.StrictMode>);
