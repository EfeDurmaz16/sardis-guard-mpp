import { useConnection, useConnect, useConnectors, useDisconnect } from 'wagmi'

export function useWallet() {
  const account = useConnection()
  const { connect } = useConnect()
  const [connector] = useConnectors()
  const { disconnect } = useDisconnect()

  const signUp = () => {
    if (!connector) return
    connect({ connector, capabilities: { type: 'sign-up' as const } })
  }

  const signIn = () => {
    if (!connector) return
    connect({ connector, capabilities: { type: 'sign-in' as const } })
  }

  const signOut = () => {
    disconnect()
  }

  return {
    address: account.address,
    isConnected: account.isConnected,
    status: account.status,
    signUp,
    signIn,
    signOut,
  }
}
