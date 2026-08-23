import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
    }
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error, errorInfo) {
    // Project-consistent error logging without leaking raw technical stack to UI
    console.error(
      '[ChatbotAI ErrorBoundary] Render error caught:',
      error,
      errorInfo?.componentStack
    )
  }

  handleReset = () => {
    if (this.props.onReset) {
      try {
        this.props.onReset()
      } catch (err) {
        console.error('[ChatbotAI ErrorBoundary] onReset callback error:', err)
      }
    }
    this.setState({
      hasError: false,
      error: null,
    })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          role="alert"
          className="flex h-full min-h-[320px] w-full flex-col items-center justify-center bg-[#141313] p-6 text-center font-mono text-[#ededed]"
        >
          <div className="flex max-w-md flex-col items-center space-y-5 rounded-xl border border-[#27272a] bg-[#16161a] p-6 shadow-xl">
            {/* Warning Emblem */}
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-400 shadow-sm">
              <span className="material-symbols-outlined text-[26px]">warning</span>
            </div>

            {/* Error Headline & Calm Description */}
            <div className="space-y-1.5">
              <h2 className="text-sm font-semibold tracking-tight text-white">
                Something went wrong displaying this component
              </h2>
              <p className="text-xs text-[#a1a1aa] leading-relaxed">
                An unexpected rendering error occurred in the workspace interface. Your conversations and data remain safe.
              </p>
            </div>

            {/* Scoped Non-Destructive Reset Action */}
            <button
              type="button"
              onClick={this.handleReset}
              className="flex items-center gap-2 rounded border border-[#27272a] bg-[#201f1f] px-4 py-2 text-xs font-semibold text-white transition-all hover:border-[#3f3f46] hover:bg-[#2a2a2a] focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              <span>Reset Interface</span>
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
