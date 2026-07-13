import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-red-400 bg-gray-900 min-h-screen">
          <h1 className="text-xl font-bold mb-4">Error en la página</h1>
          <pre className="text-sm whitespace-pre-wrap bg-gray-800 p-4 rounded-lg">
            {this.state.error?.toString()}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}
