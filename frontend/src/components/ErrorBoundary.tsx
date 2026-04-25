import { Component, ErrorInfo, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean; errorMessage: string };

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || "An unexpected error occurred." };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ErrorBoundary caught:", error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="glass-card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <div style={{ fontSize: "2.4rem", marginBottom: "12px" }}>⚠️</div>
          <h2 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>Something went wrong</h2>
          <p style={{ color: "var(--text-secondary)", margin: "0 0 20px" }}>{this.state.errorMessage}</p>
          <button
            className="btn btn-secondary"
            onClick={() => this.setState({ hasError: false, errorMessage: "" })}
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
