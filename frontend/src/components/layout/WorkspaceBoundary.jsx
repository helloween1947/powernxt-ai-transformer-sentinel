import { Component } from 'react';
export default class WorkspaceBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <main className="workspace-recovery"><h1>Workspace view could not render</h1><p>The interface encountered an unexpected error. Reload the workspace to retry.</p><button className="ui-button button-primary" onClick={() => window.location.reload()}>Reload workspace</button></main> : this.props.children; }
}
