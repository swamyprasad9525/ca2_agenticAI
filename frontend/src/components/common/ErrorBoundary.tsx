import React from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error?.message || 'An unexpected UI error occurred.',
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('UI ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-xl mx-auto mt-12 bg-white rounded-xl border border-rose-200 shadow-sm space-y-4">
          <div className="flex items-center gap-3 text-rose-700">
            <AlertTriangle className="w-6 h-6 flex-shrink-0" />
            <h2 className="text-lg font-bold">Application Rendering Error</h2>
          </div>
          <p className="text-sm text-slate-600 font-mono bg-rose-50 p-3 rounded-lg border border-rose-100">
            {this.state.errorMessage}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, errorMessage: '' });
              window.location.reload();
            }}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold rounded-lg inline-flex items-center gap-2"
          >
            <RotateCw className="w-4 h-4" /> Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
